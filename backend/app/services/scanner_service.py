"""AI-powered code scanning service."""
import logging
import re
from pathlib import Path
from typing import Any

import anthropic
from git import Repo
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.policy import Evidence, Policy, RiskLevel, SourceType
from app.models.repository import Repository, RepositoryStatus
from app.services.risk_scoring_service import RiskScoringService

logger = logging.getLogger(__name__)

# Common authorization patterns to search for
AUTH_PATTERNS = [
    r"@\w+\s*\(",  # Decorators (Python, TypeScript)
    r"hasRole\s*\(",  # Role checks
    r"isAuthorized\s*\(",  # Authorization checks
    r"authorize\s*\(",  # Authorization functions
    r"checkPermission\s*\(",  # Permission checks
    r"if\s+.*\.(role|permission|isAdmin|isManager)",  # Conditional role checks
    r"canAccess\s*\(",  # Access checks
    r"@Authorize",  # C#/Java annotations
    r"@PreAuthorize",  # Spring Security
    r"@RolesAllowed",  # Java EE
    r"@RequireRole",  # Custom role annotations
]

# File extensions to scan
SUPPORTED_EXTENSIONS = {
    ".py",
    ".java",
    ".cs",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rb",
    ".php",
    ".scala",
    ".kt",
}

# Frontend indicators
FRONTEND_INDICATORS = {
    "path_patterns": ["frontend", "client", "ui", "src/components", "src/pages", "src/views", "public", "web"],
    "file_patterns": [".tsx", ".jsx", ".vue"],
    "content_patterns": ["React", "Vue", "Angular", "useState", "useEffect", "@Component", "component:", "render()", "return ("],
}

# Backend indicators
BACKEND_INDICATORS = {
    "path_patterns": ["backend", "server", "api", "services", "controllers", "routes", "handlers"],
    "file_patterns": [".py", ".java", ".cs", ".go", ".rb", ".php", ".scala", ".kt"],
    "content_patterns": ["@RestController", "@Controller", "@app.route", "@api_view", "router.", "app.get", "app.post", "FastAPI", "Express", "Flask", "Spring"],
}


class ScannerService:
    """Service for scanning repositories and extracting policies."""

    def __init__(self, db: Session):
        """Initialize scanner service."""
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def _classify_source_type(self, file_path: str, content: str) -> SourceType:
        """Classify whether code is frontend, backend, or database.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            SourceType classification
        """
        file_path_lower = file_path.lower()
        frontend_score = 0
        backend_score = 0

        # Check path patterns
        for pattern in FRONTEND_INDICATORS["path_patterns"]:
            if pattern in file_path_lower:
                frontend_score += 3

        for pattern in BACKEND_INDICATORS["path_patterns"]:
            if pattern in file_path_lower:
                backend_score += 3

        # Check file extensions
        for ext in FRONTEND_INDICATORS["file_patterns"]:
            if file_path.endswith(ext):
                frontend_score += 5

        for ext in BACKEND_INDICATORS["file_patterns"]:
            if file_path.endswith(ext):
                backend_score += 2

        # Check content patterns
        for pattern in FRONTEND_INDICATORS["content_patterns"]:
            if pattern in content:
                frontend_score += 1

        for pattern in BACKEND_INDICATORS["content_patterns"]:
            if pattern in content:
                backend_score += 1

        # Determine source type
        if frontend_score > backend_score:
            return SourceType.FRONTEND
        elif backend_score > frontend_score:
            return SourceType.BACKEND
        else:
            return SourceType.UNKNOWN

    async def scan_repository(self, repository_id: int) -> dict[str, Any]:
        """Scan a repository and extract policies.

        Args:
            repository_id: ID of the repository to scan

        Returns:
            Dictionary with scan results
        """
        logger.info(f"Starting scan for repository {repository_id}")

        # Get repository from database
        repo = self.db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise ValueError(f"Repository {repository_id} not found")

        # Update status to scanning
        repo.status = RepositoryStatus.SCANNING
        self.db.commit()

        try:
            # Clone repository to temp directory
            repo_path = await self._clone_repository(repo)

            # Find files with potential authorization code
            auth_files = await self._find_authorization_files(repo_path)

            logger.info(f"Found {len(auth_files)} files with potential authorization code")

            # Extract policies from each file
            policies_created = 0
            for file_info in auth_files[:settings.BATCH_SIZE]:  # Process in batches
                try:
                    policies = await self._extract_policies_from_file(
                        repo, file_info["path"], file_info["content"], file_info["matches"]
                    )
                    policies_created += len(policies)
                except Exception as e:
                    logger.error(f"Error processing file {file_info['path']}: {e}")
                    continue

            # Update repository status
            repo.status = RepositoryStatus.CONNECTED
            self.db.commit()

            logger.info(f"Scan complete: extracted {policies_created} policies")

            return {
                "status": "completed",
                "files_scanned": len(auth_files),
                "policies_extracted": policies_created,
            }

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            repo.status = RepositoryStatus.FAILED
            self.db.commit()
            raise

    async def _clone_repository(self, repo: Repository) -> Path:
        """Clone repository to temporary directory.

        Args:
            repo: Repository model instance

        Returns:
            Path to cloned repository
        """
        clone_dir = Path("/tmp/policy_miner_repos") / str(repo.id)
        clone_dir.mkdir(parents=True, exist_ok=True)

        if (clone_dir / ".git").exists():
            logger.info(f"Repository already cloned at {clone_dir}")
            return clone_dir

        # Build clone URL with credentials if provided
        clone_url = repo.source_url
        if repo.connection_config:
            auth_type = repo.connection_config.get("auth_type")
            if auth_type == "token":
                token = repo.connection_config.get("token")
                # Insert token into URL (works for GitHub, GitLab, etc.)
                clone_url = clone_url.replace("https://", f"https://{token}@")
            elif auth_type == "username_password":
                username = repo.connection_config.get("username")
                password = repo.connection_config.get("password")
                clone_url = clone_url.replace("https://", f"https://{username}:{password}@")

        logger.info(f"Cloning repository to {clone_dir}")
        Repo.clone_from(clone_url, clone_dir, depth=1)

        return clone_dir

    async def _find_authorization_files(self, repo_path: Path) -> list[dict[str, Any]]:
        """Find files containing authorization code.

        Args:
            repo_path: Path to repository

        Returns:
            List of file information dictionaries
        """
        auth_files = []

        for file_path in repo_path.rglob("*"):
            # Skip non-files and common ignore patterns
            if not file_path.is_file():
                continue
            if any(p in str(file_path) for p in [".git", "node_modules", "venv", "__pycache__", "dist", "build"]):
                continue
            if file_path.suffix not in SUPPORTED_EXTENSIONS:
                continue

            # Check file size
            if file_path.stat().st_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Search for authorization patterns
                matches = []
                for pattern in AUTH_PATTERNS:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        line_num = content[:match.start()].count("\n") + 1
                        matches.append({
                            "pattern": pattern,
                            "line": line_num,
                            "text": match.group(),
                        })

                if matches:
                    # Get relative path from repo root
                    relative_path = file_path.relative_to(repo_path)
                    auth_files.append({
                        "path": str(relative_path),
                        "content": content,
                        "matches": matches,
                    })

            except Exception as e:
                logger.debug(f"Skipping file {file_path}: {e}")
                continue

        return auth_files

    async def _extract_policies_from_file(
        self, repo: Repository, file_path: str, content: str, matches: list[dict]
    ) -> list[Policy]:
        """Extract policies from a file using Claude AI.

        Args:
            repo: Repository model
            file_path: Path to the file
            content: File content
            matches: Authorization pattern matches

        Returns:
            List of created Policy objects
        """
        # Prepare prompt for Claude
        prompt = self._build_extraction_prompt(file_path, content, matches)

        try:
            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = message.content[0].text
            policies = self._parse_claude_response(response_text, repo, file_path, content)

            # Save policies to database
            for policy in policies:
                self.db.add(policy)

            self.db.commit()

            return policies

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return []

    def _build_extraction_prompt(self, file_path: str, content: str, matches: list[dict]) -> str:
        """Build prompt for Claude to extract policies.

        Args:
            file_path: Path to file
            content: File content
            matches: Pattern matches

        Returns:
            Formatted prompt string
        """
        # Truncate content if too long (keep context around matches)
        max_content_length = 8000
        if len(content) > max_content_length:
            # Extract snippets around each match
            snippets = []
            for match in matches[:10]:  # Limit matches
                line_num = match["line"]
                lines = content.split("\n")
                start = max(0, line_num - 10)
                end = min(len(lines), line_num + 10)
                snippet = "\n".join(lines[start:end])
                snippets.append(f"Lines {start}-{end}:\n{snippet}")
            content = "\n\n---\n\n".join(snippets)

        prompt = f"""You are a security policy extraction expert. Analyze the following code file and extract ALL authorization/access control policies.

File: {file_path}

Code:
```
{content}
```

For EACH authorization policy you find, extract:
1. **Subject (Who)**: Who is allowed/denied (e.g., "Admin", "Manager", "User with role X")
2. **Resource (What)**: What resource is being protected (e.g., "User Account", "Expense Report", "API Endpoint")
3. **Action (How)**: What action is being controlled (e.g., "delete", "approve", "read")
4. **Conditions (When)**: Any conditions that must be met (e.g., "amount < $5000", "user.department == expense.department")
5. **Evidence**: The EXACT line numbers and code snippet that contains this policy

IMPORTANT:
- Extract EVERY distinct policy, even if similar
- Quote EXACT code snippets with line numbers
- If a policy has no conditions, set conditions to null
- Provide a brief description of what the policy does

Return your response as a JSON array of policies:
```json
[
  {{
    "subject": "Manager",
    "resource": "Expense Report",
    "action": "approve",
    "conditions": "amount < 5000",
    "description": "Managers can approve expense reports under $5000",
    "evidence": [
      {{
        "line_start": 42,
        "line_end": 45,
        "code_snippet": "if (user.role === 'MANAGER' && expense.amount < 5000) {{\\n  return approve(expense);\\n}}"
      }}
    ]
  }}
]
```

Return ONLY the JSON array, no other text."""

        return prompt

    def _parse_claude_response(
        self, response: str, repo: Repository, file_path: str, content: str
    ) -> list[Policy]:
        """Parse Claude's response and create Policy objects.

        Args:
            response: Claude's response text
            repo: Repository model
            file_path: Source file path
            content: File content

        Returns:
            List of Policy objects
        """
        import json

        policies = []

        try:
            # Extract JSON from response
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            policy_data = json.loads(json_str)

            # Classify source type for this file
            source_type = self._classify_source_type(file_path, content)

            for item in policy_data:
                subject = item.get("subject", "Unknown")
                resource = item.get("resource", "Unknown")
                action = item.get("action", "Unknown")
                conditions = item.get("conditions")

                # Get first evidence item for risk scoring
                evidence_items = item.get("evidence", [])
                first_evidence = evidence_items[0] if evidence_items else {}
                code_snippet = first_evidence.get("code_snippet", "")

                # Calculate multi-dimensional risk scores
                complexity_score = RiskScoringService.calculate_complexity_score(
                    subject, resource, action, conditions, code_snippet
                )
                impact_score = RiskScoringService.calculate_impact_score(
                    subject, resource, action, conditions
                )
                confidence_score = RiskScoringService.calculate_confidence_score(
                    len(evidence_items), code_snippet, subject, resource, action
                )
                historical_score = RiskScoringService.calculate_historical_score()

                # Calculate overall risk score
                risk_score = RiskScoringService.calculate_overall_risk_score(
                    complexity_score, impact_score, confidence_score, historical_score
                )

                # Determine risk level from overall score
                if risk_score >= 70:
                    risk_level = RiskLevel.HIGH
                elif risk_score >= 40:
                    risk_level = RiskLevel.MEDIUM
                else:
                    risk_level = RiskLevel.LOW

                # Create policy
                policy = Policy(
                    repository_id=repo.id,
                    subject=subject,
                    resource=resource,
                    action=action,
                    conditions=conditions,
                    description=item.get("description"),
                    risk_score=risk_score,
                    risk_level=risk_level,
                    complexity_score=complexity_score,
                    impact_score=impact_score,
                    confidence_score=confidence_score,
                    historical_score=historical_score,
                    tenant_id=repo.tenant_id,
                    source_type=source_type,
                )

                # Add evidence
                for ev in evidence_items:
                    evidence = Evidence(
                        file_path=file_path,
                        line_start=ev.get("line_start", 0),
                        line_end=ev.get("line_end", 0),
                        code_snippet=ev.get("code_snippet", ""),
                    )
                    policy.evidence.append(evidence)

                policies.append(policy)

        except Exception as e:
            logger.error(f"Error parsing Claude response: {e}")
            logger.debug(f"Response was: {response}")

        return policies
