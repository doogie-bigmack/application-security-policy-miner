"""AI-powered code scanning service."""
import logging
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from git import Repo
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.policy import Evidence, Policy, RiskLevel, SourceType
from app.models.repository import Repository, RepositoryStatus
from app.models.scan_progress import ScanProgress, ScanStatus
from app.models.secret_detection import SecretDetectionLog
from app.services.audit_service import AuditService
from app.services.llm_provider import get_llm_provider
from app.services.risk_scoring_service import RiskScoringService
from app.services.secret_detection_service import SecretDetectionService

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
        self.llm_provider = get_llm_provider()

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

    async def scan_repository(self, repository_id: int, tenant_id: str | None = None) -> dict[str, Any]:
        """Scan a repository and extract policies.

        Args:
            repository_id: ID of the repository to scan
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            Dictionary with scan results
        """
        logger.info(f"Starting scan for repository {repository_id}", tenant_id=tenant_id)

        # Get repository from database with tenant filtering
        query = self.db.query(Repository).filter(Repository.id == repository_id)
        if tenant_id:
            query = query.filter(Repository.tenant_id == tenant_id)
        repo = query.first()
        if not repo:
            raise ValueError(f"Repository {repository_id} not found")

        # Create scan progress tracker
        scan_progress = ScanProgress(
            repository_id=repository_id,
            tenant_id=tenant_id,
            status=ScanStatus.QUEUED,
            started_at=datetime.utcnow(),
        )
        self.db.add(scan_progress)
        self.db.commit()
        self.db.refresh(scan_progress)

        # Update repository status to scanning
        repo.status = RepositoryStatus.SCANNING
        self.db.commit()

        try:
            # Clone repository to temp directory
            repo_path = await self._clone_repository(repo)

            # Find files with potential authorization code (with secret detection)
            auth_files = await self._find_authorization_files(repo_path, repo)

            logger.info(f"Found {len(auth_files)} files with potential authorization code")

            # Calculate batches
            total_files = len(auth_files)
            total_batches = math.ceil(total_files / settings.BATCH_SIZE)

            # Update scan progress with totals
            scan_progress.total_files = total_files
            scan_progress.total_batches = total_batches
            scan_progress.status = ScanStatus.PROCESSING
            self.db.commit()

            # Process ALL files in batches
            policies_created = 0
            errors_count = 0

            for batch_num in range(total_batches):
                start_idx = batch_num * settings.BATCH_SIZE
                end_idx = min((batch_num + 1) * settings.BATCH_SIZE, total_files)
                batch_files = auth_files[start_idx:end_idx]

                logger.info(
                    f"Processing batch {batch_num + 1}/{total_batches} "
                    f"({len(batch_files)} files)"
                )

                # Update progress for current batch
                scan_progress.current_batch = batch_num + 1
                self.db.commit()

                # Process each file in the batch
                for file_info in batch_files:
                    try:
                        policies = await self._extract_policies_from_file(
                            repo, file_info["path"], file_info["content"], file_info["matches"]
                        )
                        policies_created += len(policies)

                        # Update progress
                        scan_progress.processed_files += 1
                        scan_progress.policies_extracted = policies_created
                        self.db.commit()

                    except Exception as e:
                        logger.error(f"Error processing file {file_info['path']}: {e}")
                        errors_count += 1
                        scan_progress.errors_count = errors_count
                        self.db.commit()
                        continue

                logger.info(
                    f"Batch {batch_num + 1} complete: "
                    f"{scan_progress.processed_files}/{total_files} files processed, "
                    f"{policies_created} policies extracted"
                )

            # Update scan progress to completed
            scan_progress.status = ScanStatus.COMPLETED
            scan_progress.completed_at = datetime.utcnow()
            scan_progress.policies_extracted = policies_created
            scan_progress.errors_count = errors_count
            self.db.commit()

            # Update repository status
            repo.status = RepositoryStatus.CONNECTED
            repo.last_scan_at = datetime.utcnow()
            self.db.commit()

            logger.info(
                f"Scan complete: processed {total_files} files in {total_batches} batches, "
                f"extracted {policies_created} policies, {errors_count} errors"
            )

            # Detect changes if this is not the first scan
            changes_detected = 0
            if repo.last_scan_at is not None:
                try:
                    from app.services.change_detection_service import ChangeDetectionService

                    change_service = ChangeDetectionService(self.db)
                    changes = change_service.detect_changes(repo.id, repo.tenant_id)
                    changes_detected = len(changes)
                    logger.info(f"Change detection: found {changes_detected} policy changes")
                except Exception as e:
                    logger.error(f"Error detecting changes: {e}")

            return {
                "status": "completed",
                "scan_id": scan_progress.id,
                "files_scanned": total_files,
                "policies_extracted": policies_created,
                "errors_count": errors_count,
                "batches_processed": total_batches,
                "changes_detected": changes_detected,
            }

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            repo.status = RepositoryStatus.FAILED
            scan_progress.status = ScanStatus.FAILED
            scan_progress.error_message = str(e)
            scan_progress.completed_at = datetime.utcnow()
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

    async def _find_authorization_files(self, repo_path: Path, repository: Repository) -> list[dict[str, Any]]:
        """Find files containing authorization code and scan for secrets.

        Args:
            repo_path: Path to repository
            repository: Repository model instance for logging secrets

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
                relative_path = file_path.relative_to(repo_path)

                # PRE-SCAN: Detect secrets BEFORE processing
                secret_result = SecretDetectionService.scan_content(content, str(relative_path))

                # Log detected secrets to audit trail
                if secret_result.has_secrets:
                    for secret in secret_result.secrets_found:
                        secret_log = SecretDetectionLog(
                            repository_id=repository.id,
                            tenant_id=repository.tenant_id,
                            file_path=str(relative_path),
                            secret_type=secret["type"],
                            description=secret["description"],
                            line_number=secret["line"],
                            preview=secret["preview"],
                        )
                        self.db.add(secret_log)

                    # Commit secret logs immediately
                    self.db.commit()

                    logger.warning(
                        f"Found {len(secret_result.secrets_found)} secrets in {relative_path}. "
                        "Secrets will be redacted before sending to LLM."
                    )

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
                    # Redact secrets from content before storing
                    redacted_content, secrets_count = SecretDetectionService.redact_secrets(content)

                    if secrets_count > 0:
                        logger.info(
                            f"Redacted {secrets_count} secrets from {relative_path} before LLM processing"
                        )

                    auth_files.append({
                        "path": str(relative_path),
                        "content": redacted_content,  # Use redacted content
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
            content: File content (should already be redacted)
            matches: Authorization pattern matches

        Returns:
            List of created Policy objects
        """
        # Prepare prompt for Claude
        prompt = self._build_extraction_prompt(file_path, content, matches)

        # CRITICAL SECURITY CHECK: Validate no secrets in prompt before sending to LLM
        SecretDetectionService.validate_no_secrets_in_prompt(prompt, file_path)

        # Log AI prompt to audit trail
        import time
        start_time = time.time()

        AuditService.log_ai_prompt(
            db=self.db,
            tenant_id=repo.tenant_id,
            prompt=prompt,
            model=self.llm_provider.model_id if hasattr(self.llm_provider, 'model_id') else "unknown",
            provider=settings.LLM_PROVIDER,
            repository_id=repo.id,
            additional_context={
                "file_path": file_path,
                "matches_count": len(matches),
            },
        )

        try:
            # Call LLM provider (AWS Bedrock or Azure OpenAI)
            response_text = self.llm_provider.create_message(
                prompt=prompt,
                max_tokens=4096,
                temperature=0,
            )

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Log AI response to audit trail
            AuditService.log_ai_response(
                db=self.db,
                tenant_id=repo.tenant_id,
                response=response_text,
                model=self.llm_provider.model_id if hasattr(self.llm_provider, 'model_id') else "unknown",
                provider=settings.LLM_PROVIDER,
                repository_id=repo.id,
                response_time_ms=response_time_ms,
                additional_context={
                    "file_path": file_path,
                },
            )

            # Parse response
            policies = self._parse_claude_response(response_text, repo, file_path, content)

            # Save policies to database
            for policy in policies:
                self.db.add(policy)

            self.db.commit()

            return policies

        except Exception as e:
            logger.error(f"Error calling LLM provider: {e}")
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
