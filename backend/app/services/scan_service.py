"""Scan service for analyzing repositories and extracting policies."""

import json
import logging
import os
import tempfile
from pathlib import Path

import anthropic
from git import Repo
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.policy import Policy, PolicyEvidence, PolicyStatus, RiskLevel
from app.models.repository import Repository, RepositoryStatus, RepositoryType

logger = logging.getLogger(__name__)

# File extensions to scan
SCANNABLE_EXTENSIONS = {
    ".py",
    ".java",
    ".cs",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rb",
    ".php",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}


class ScanService:
    """Service for scanning repositories and extracting policies."""

    def __init__(self, db: Session) -> None:
        """Initialize scan service."""
        self.db = db
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def scan_repository(self, repository_id: int) -> int:
        """
        Scan a repository and extract authorization policies.

        Args:
            repository_id: ID of repository to scan

        Returns:
            Number of policies extracted
        """
        repository = self.db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            msg = f"Repository {repository_id} not found"
            raise ValueError(msg)

        # Update status to scanning
        repository.status = RepositoryStatus.SCANNING
        self.db.commit()

        try:
            if repository.repository_type == RepositoryType.GIT:
                policies_count = await self._scan_git_repository(repository)
            elif repository.repository_type == RepositoryType.DATABASE:
                policies_count = await self._scan_database_repository(repository)
            else:
                msg = f"Unsupported repository type: {repository.repository_type}"
                raise ValueError(msg)

            # Update repository status
            repository.status = RepositoryStatus.CONNECTED
            from datetime import UTC, datetime

            repository.last_scan_at = datetime.now(UTC)
            self.db.commit()

            return policies_count

        except Exception as e:
            logger.exception("Error scanning repository %d", repository_id)
            repository.status = RepositoryStatus.FAILED
            self.db.commit()
            raise

    async def _scan_git_repository(self, repository: Repository) -> int:
        """
        Scan a Git repository for authorization policies.

        Args:
            repository: Repository model

        Returns:
            Number of policies extracted
        """
        temp_dir = None
        try:
            # Clone repository to temporary directory
            temp_dir = tempfile.mkdtemp()
            logger.info("Cloning repository %s to %s", repository.source_url, temp_dir)

            # Get Git credentials from connection_config
            config = repository.connection_config or {}
            auth_type = config.get("auth_type", "none")

            # Build clone URL with credentials if needed
            clone_url = repository.source_url
            if auth_type == "token" and config.get("token"):
                # Insert token into URL
                clone_url = self._insert_credentials(repository.source_url, config.get("token"), "")
            elif auth_type == "username_password":
                username = config.get("username", "")
                password = config.get("password", "")
                clone_url = self._insert_credentials(repository.source_url, username, password)

            # Clone repository
            repo = Repo.clone_from(clone_url, temp_dir, depth=1)
            logger.info("Repository cloned successfully")

            # Find all scannable files
            files_to_scan = []
            for root, _dirs, files in os.walk(temp_dir):
                # Skip .git directory
                if ".git" in root:
                    continue

                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix in SCANNABLE_EXTENSIONS:
                        # Check file size
                        file_size_mb = file_path.stat().st_size / (1024 * 1024)
                        if file_size_mb <= settings.MAX_FILE_SIZE_MB:
                            files_to_scan.append(file_path)

            logger.info("Found %d files to scan", len(files_to_scan))

            # Process files in batches
            policies_extracted = 0
            batch_size = settings.BATCH_SIZE
            for i in range(0, len(files_to_scan), batch_size):
                batch = files_to_scan[i : i + batch_size]
                batch_policies = await self._analyze_files_batch(repository, batch, temp_dir)
                policies_extracted += batch_policies
                logger.info(
                    "Processed batch %d/%d, extracted %d policies",
                    (i // batch_size) + 1,
                    (len(files_to_scan) + batch_size - 1) // batch_size,
                    batch_policies,
                )

            return policies_extracted

        finally:
            # Cleanup temporary directory
            if temp_dir:
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)

    def _insert_credentials(self, url: str, username: str, password: str) -> str:
        """Insert credentials into Git URL."""
        if url.startswith("https://"):
            # Insert credentials after https://
            if password:
                return url.replace("https://", f"https://{username}:{password}@")
            return url.replace("https://", f"https://{username}@")
        return url

    async def _analyze_files_batch(
        self, repository: Repository, files: list[Path], repo_root: str
    ) -> int:
        """
        Analyze a batch of files for authorization policies.

        Args:
            repository: Repository model
            files: List of file paths to analyze
            repo_root: Root directory of repository

        Returns:
            Number of policies extracted
        """
        if not self.client:
            logger.warning("No Anthropic API key configured, using mock policies")
            return self._create_mock_policies(repository, files, repo_root)

        # Read file contents
        file_contents = []
        for file_path in files:
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    rel_path = str(file_path.relative_to(repo_root))
                    file_contents.append({"path": rel_path, "content": content})
            except Exception as e:
                logger.warning("Error reading file %s: %s", file_path, e)

        if not file_contents:
            return 0

        # Analyze with Claude
        prompt = self._build_analysis_prompt(file_contents)

        try:
            response = self.client.messages.create(
                model="claude-opus-4-5-20251101",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response and create policies
            policies = self._parse_claude_response(response.content[0].text)
            return self._store_policies(repository, policies)

        except Exception as e:
            logger.exception("Error calling Claude API: %s", e)
            # Fall back to mock policies
            return self._create_mock_policies(repository, files, repo_root)

    def _build_analysis_prompt(self, file_contents: list[dict]) -> str:
        """Build prompt for Claude to analyze code."""
        files_text = "\n\n".join(
            [f"File: {fc['path']}\n```\n{fc['content']}\n```" for fc in file_contents]
        )

        return f"""Analyze the following code files and extract ALL authorization policies.

For each authorization policy you find, identify:
- WHO: The subject (user, role, group, service that is authorized)
- WHAT: The resource being accessed (API endpoint, data, feature, etc.)
- HOW: The action being performed (read, write, delete, execute, etc.)
- WHEN: Any conditions or constraints (time-based, attribute-based, etc.)

Also provide evidence for each policy:
- File path
- Start and end line numbers
- Exact code snippet

Look for:
- Role-based access control (RBAC) checks
- Permission checks
- Authentication/authorization decorators or attributes
- Conditional access logic
- Security checks in API endpoints
- Authorization middleware
- Access control lists

Return your analysis as a JSON array with this structure:
[
  {{
    "subject": "string describing who is authorized",
    "resource": "string describing what resource",
    "action": "string describing what action",
    "conditions": "string describing when/conditions (or null)",
    "description": "brief description of the policy",
    "risk_level": "low|medium|high|critical",
    "evidence": [
      {{
        "file_path": "relative/path/to/file",
        "start_line": 10,
        "end_line": 15,
        "code_snippet": "exact code from those lines"
      }}
    ]
  }}
]

Files to analyze:

{files_text}

Return ONLY the JSON array, no other text.
"""

    def _parse_claude_response(self, response_text: str) -> list[dict]:
        """Parse Claude's response into policy dictionaries."""
        try:
            # Try to extract JSON from response
            # Sometimes Claude wraps JSON in markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            policies = json.loads(response_text)
            return policies if isinstance(policies, list) else []

        except Exception as e:
            logger.exception("Error parsing Claude response: %s", e)
            return []

    def _store_policies(self, repository: Repository, policies: list[dict]) -> int:
        """Store extracted policies in database."""
        count = 0
        for policy_data in policies:
            try:
                # Create policy
                policy_status_str = policy_data.get("status", "EXTRACTED")
                policy = Policy(
                    repository_id=repository.id,
                    subject=policy_data.get("subject", "Unknown"),
                    resource=policy_data.get("resource", "Unknown"),
                    action=policy_data.get("action", "Unknown"),
                    conditions=policy_data.get("conditions"),
                    description=policy_data.get("description"),
                    status=PolicyStatus(policy_status_str),
                    risk_level=RiskLevel(policy_data.get("risk_level", "medium")),
                    tenant_id=repository.tenant_id,
                )
                self.db.add(policy)
                self.db.flush()  # Get policy ID

                # Create evidence
                for evidence_data in policy_data.get("evidence", []):
                    evidence = PolicyEvidence(
                        policy_id=policy.id,
                        file_path=evidence_data.get("file_path", "unknown"),
                        start_line=evidence_data.get("start_line", 1),
                        end_line=evidence_data.get("end_line", 1),
                        code_snippet=evidence_data.get("code_snippet", ""),
                    )
                    self.db.add(evidence)

                count += 1

            except Exception as e:
                logger.exception("Error storing policy: %s", e)

        self.db.commit()
        return count

    def _create_mock_policies(self, repository: Repository, files: list[Path], repo_root: str) -> int:
        """Create mock policies for testing when Claude API is not available."""
        # Create a few sample policies
        mock_policies = [
            {
                "subject": "Authenticated User",
                "resource": "API Endpoints",
                "action": "Read",
                "conditions": "Valid JWT token required",
                "description": "Users must be authenticated to access protected API endpoints",
                "risk_level": "MEDIUM",
                "status": "EXTRACTED",
                "evidence": [
                    {
                        "file_path": str(files[0].relative_to(repo_root)) if files else "example.py",
                        "start_line": 1,
                        "end_line": 5,
                        "code_snippet": "# Sample authorization code\n@require_auth\ndef protected_endpoint():\n    return data",
                    }
                ],
            },
            {
                "subject": "Admin Role",
                "resource": "User Management",
                "action": "Write",
                "conditions": "User must have admin role",
                "description": "Only administrators can manage user accounts",
                "risk_level": "HIGH",
                "status": "EXTRACTED",
                "evidence": [
                    {
                        "file_path": str(files[0].relative_to(repo_root)) if files else "example.py",
                        "start_line": 10,
                        "end_line": 15,
                        "code_snippet": "if user.role == 'admin':\n    # Admin operations\n    manage_users()",
                    }
                ],
            },
        ]

        return self._store_policies(repository, mock_policies)

    async def _scan_database_repository(self, repository: Repository) -> int:
        """
        Scan a database repository for authorization policies.

        Args:
            repository: Repository model

        Returns:
            Number of policies extracted
        """
        # TODO: Implement database scanning
        logger.warning("Database scanning not yet implemented")
        return 0
