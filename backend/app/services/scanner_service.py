"""AI-powered code scanning service."""
import logging
import math
import os
import re
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
from git import Repo
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import (
    increment_error_count,
    increment_policies_extracted,
    increment_scan_count,
    record_scan_duration,
    set_active_scans,
)
from app.models.policy import Evidence, Policy, PolicyStatus, RiskLevel, SourceType
from app.models.repository import Repository, RepositoryStatus, RepositoryType
from app.models.scan_progress import ScanProgress, ScanStatus
from app.models.secret_detection import SecretDetectionLog
from app.services.audit_service import AuditService
from app.services.csharp_scanner_service import CSharpScannerService
from app.services.database_scanner_service import DatabaseScannerService
from app.services.java_scanner_service import JavaScannerService
from app.services.javascript_scanner import JavaScriptScannerService
from app.services.llm_provider import get_llm_provider
from app.services.mainframe_scanner_service import MainframeScannerService
from app.services.python_scanner_service import PythonScannerService
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
    ".cbl",     # COBOL
    ".cobol",   # COBOL
    ".cob",     # COBOL
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
        self.java_scanner = JavaScannerService()
        self.csharp_scanner = CSharpScannerService()
        self.python_scanner = PythonScannerService()
        self.javascript_scanner = JavaScriptScannerService()
        self.database_scanner = DatabaseScannerService()
        self.mainframe_scanner = MainframeScannerService()
        self.process = psutil.Process(os.getpid())
        self.initial_memory_mb = self.process.memory_info().rss / 1024 / 1024

    def _get_memory_usage_mb(self) -> float:
        """Get current process memory usage in MB.

        Returns:
            Current memory usage in megabytes
        """
        return self.process.memory_info().rss / 1024 / 1024

    def _get_memory_delta_mb(self) -> float:
        """Get memory usage delta since initialization.

        Returns:
            Memory usage increase in megabytes
        """
        return self._get_memory_usage_mb() - self.initial_memory_mb

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

    async def scan_repository(
        self, repository_id: int, tenant_id: str | None = None, incremental: bool = False
    ) -> dict[str, Any]:
        """Scan a repository and extract policies using streaming analysis.

        Args:
            repository_id: ID of the repository to scan
            tenant_id: Optional tenant ID for multi-tenancy
            incremental: If True, only scan changed files since last scan

        Returns:
            Dictionary with scan results including memory metrics
        """
        start_time = datetime.utcnow()
        start_memory_mb = self._get_memory_usage_mb()
        peak_memory_mb = start_memory_mb

        scan_type = "incremental" if incremental else "full"
        logger.info(
            f"Starting {scan_type} streaming scan for repository {repository_id}",
            tenant_id=tenant_id,
            initial_memory_mb=round(start_memory_mb, 2)
        )

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
            started_at=start_time,
        )
        self.db.add(scan_progress)
        self.db.commit()
        self.db.refresh(scan_progress)

        # Update repository status to scanning
        repo.status = RepositoryStatus.SCANNING
        self.db.commit()

        # Track active scans metric
        active_scans_count = self.db.query(ScanProgress).filter(
            ScanProgress.status.in_([ScanStatus.QUEUED, ScanStatus.PROCESSING])
        ).count()
        set_active_scans(active_scans_count)

        try:
            # Handle database repositories differently
            if repo.repository_type == RepositoryType.DATABASE:
                return await self._scan_database_repository(
                    repo, scan_progress, start_time, start_memory_mb, tenant_id
                )

            # Handle mainframe repositories differently
            if repo.repository_type == RepositoryType.MAINFRAME:
                return await self._scan_mainframe_repository(
                    repo, scan_progress, start_time, start_memory_mb, tenant_id
                )

            # Clone repository to temp directory
            repo_path = await self._clone_repository(repo)

            # Get current commit hash
            git_repo = Repo(repo_path)
            current_commit = git_repo.head.commit.hexsha
            scan_progress.git_commit_hash = current_commit
            scan_progress.is_incremental = 1 if incremental else 0

            # Get changed files if incremental scan
            changed_files = set()
            if incremental:
                last_commit = self._get_last_scan_commit(repository_id)
                if last_commit:
                    changed_files = self._get_changed_files_since_commit(repo_path, last_commit)
                    logger.info(f"Incremental scan: {len(changed_files)} files changed")
                else:
                    logger.info("No previous scan found, performing full scan")
                    incremental = False  # Fall back to full scan

            # STREAMING: Count files first without loading into memory
            total_files = await self._count_authorization_files(repo_path, changed_files if incremental else None)
            total_batches = math.ceil(total_files / settings.BATCH_SIZE) if total_files > 0 else 0

            logger.info(
                f"Found {total_files} files to scan, will process in {total_batches} batches"
            )

            # Update scan progress with totals
            scan_progress.total_files = total_files
            scan_progress.total_batches = total_batches
            scan_progress.status = ScanStatus.PROCESSING
            self.db.commit()

            # STREAMING: Process files as we discover them (batching)
            policies_created = 0
            errors_count = 0
            current_batch = []
            batch_num = 0

            async for file_info in self._stream_authorization_files(
                repo_path, repo, changed_files if incremental else None
            ):
                current_batch.append(file_info)

                # Process batch when it reaches BATCH_SIZE
                if len(current_batch) >= settings.BATCH_SIZE:
                    batch_num += 1
                    logger.info(
                        f"Processing batch {batch_num}/{total_batches} "
                        f"({len(current_batch)} files)"
                    )

                    # Update progress for current batch
                    scan_progress.current_batch = batch_num
                    self.db.commit()

                    # Process each file in the batch
                    for file_info in current_batch:
                        try:
                            policies = await self._extract_policies_from_file(
                                repo, file_info["path"], file_info["content"], file_info["matches"], repo_path
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

                    # Track peak memory usage
                    current_memory_mb = self._get_memory_usage_mb()
                    peak_memory_mb = max(peak_memory_mb, current_memory_mb)

                    logger.info(
                        f"Batch {batch_num} complete: "
                        f"{scan_progress.processed_files}/{total_files} files processed, "
                        f"{policies_created} policies extracted, "
                        f"memory: {round(current_memory_mb, 2)}MB (peak: {round(peak_memory_mb, 2)}MB)"
                    )

                    # Clear batch to free memory
                    current_batch = []

            # Process remaining files in final batch
            if current_batch:
                batch_num += 1
                logger.info(f"Processing final batch {batch_num} ({len(current_batch)} files)")

                scan_progress.current_batch = batch_num
                self.db.commit()

                for file_info in current_batch:
                    try:
                        policies = await self._extract_policies_from_file(
                            repo, file_info["path"], file_info["content"], file_info["matches"], repo_path
                        )
                        policies_created += len(policies)

                        scan_progress.processed_files += 1
                        scan_progress.policies_extracted = policies_created
                        self.db.commit()

                    except Exception as e:
                        logger.error(f"Error processing file {file_info['path']}: {e}")
                        errors_count += 1
                        scan_progress.errors_count = errors_count
                        increment_error_count("file_processing", "scanner_service")
                        self.db.commit()
                        continue

                current_memory_mb = self._get_memory_usage_mb()
                peak_memory_mb = max(peak_memory_mb, current_memory_mb)

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

            # Calculate performance metrics
            end_time = datetime.utcnow()
            scan_duration_seconds = (end_time - start_time).total_seconds()
            end_memory_mb = self._get_memory_usage_mb()
            memory_delta_mb = end_memory_mb - start_memory_mb

            # Record Prometheus metrics
            record_scan_duration(str(repository_id), scan_type, scan_duration_seconds)
            increment_policies_extracted(str(repository_id), "extracted", policies_created)
            increment_scan_count(scan_type, "success")

            # Update active scans metric
            active_scans_count = self.db.query(ScanProgress).filter(
                ScanProgress.status.in_([ScanStatus.QUEUED, ScanStatus.PROCESSING])
            ).count()
            set_active_scans(active_scans_count)

            logger.info(
                f"Streaming scan complete: processed {total_files} files in {batch_num} batches, "
                f"extracted {policies_created} policies, {errors_count} errors, "
                f"duration: {round(scan_duration_seconds, 2)}s, "
                f"memory: start={round(start_memory_mb, 2)}MB peak={round(peak_memory_mb, 2)}MB "
                f"end={round(end_memory_mb, 2)}MB delta={round(memory_delta_mb, 2)}MB"
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
                "scan_type": "incremental" if scan_progress.is_incremental else "full",
                "git_commit": current_commit[:7] if 'current_commit' in locals() else None,
                "files_scanned": total_files,
                "policies_extracted": policies_created,
                "errors_count": errors_count,
                "batches_processed": batch_num,
                "changes_detected": changes_detected,
                "performance": {
                    "duration_seconds": round(scan_duration_seconds, 2),
                    "start_memory_mb": round(start_memory_mb, 2),
                    "peak_memory_mb": round(peak_memory_mb, 2),
                    "end_memory_mb": round(end_memory_mb, 2),
                    "memory_delta_mb": round(memory_delta_mb, 2),
                },
            }

        except Exception as e:
            logger.error(f"Scan failed: {e}")

            # Record error metrics
            increment_error_count("scan_failure", "scanner_service")
            increment_scan_count(scan_type, "failure")

            # Update active scans metric
            active_scans_count = self.db.query(ScanProgress).filter(
                ScanProgress.status.in_([ScanStatus.QUEUED, ScanStatus.PROCESSING])
            ).count()
            set_active_scans(active_scans_count)

            repo.status = RepositoryStatus.FAILED
            scan_progress.status = ScanStatus.FAILED
            scan_progress.error_message = str(e)
            scan_progress.completed_at = datetime.utcnow()
            self.db.commit()
            raise

    def _get_last_scan_commit(self, repository_id: int) -> str | None:
        """Get the git commit hash from the last successful scan.

        Args:
            repository_id: Repository ID

        Returns:
            Git commit hash or None if no previous scan
        """
        last_scan = (
            self.db.query(ScanProgress)
            .filter(
                ScanProgress.repository_id == repository_id,
                ScanProgress.status == ScanStatus.COMPLETED,
                ScanProgress.git_commit_hash.isnot(None)
            )
            .order_by(ScanProgress.completed_at.desc())
            .first()
        )
        return last_scan.git_commit_hash if last_scan else None

    def _get_changed_files_since_commit(self, repo_path: Path, base_commit: str) -> set[str]:
        """Get list of changed files since a specific commit using git diff.

        Args:
            repo_path: Path to the git repository
            base_commit: Base commit hash to compare against

        Returns:
            Set of file paths that have changed
        """
        try:
            git_repo = Repo(repo_path)
            current_commit = git_repo.head.commit.hexsha

            if base_commit == current_commit:
                logger.info("No changes since last scan (same commit)")
                return set()

            # Get diff between base commit and current HEAD
            diff_index = git_repo.commit(base_commit).diff(git_repo.head.commit)

            changed_files = set()
            for diff in diff_index:
                # Include both modified and added files (a_path for deletions, b_path for additions)
                if diff.b_path:  # File was added or modified
                    changed_files.add(diff.b_path)
                elif diff.a_path:  # File was deleted (we won't scan deleted files)
                    pass

            logger.info(
                f"Git diff: found {len(changed_files)} changed files between "
                f"{base_commit[:7]} and {current_commit[:7]}"
            )
            return changed_files

        except Exception as e:
            logger.error(f"Error getting git diff: {e}")
            # If we can't get the diff, fall back to full scan
            return set()

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
            logger.info(f"Repository already cloned at {clone_dir}, pulling latest changes")
            # Pull latest changes instead of re-cloning
            git_repo = Repo(clone_dir)
            origin = git_repo.remotes.origin
            origin.pull()
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
        # Don't use depth=1 anymore so we can do git diff
        Repo.clone_from(clone_url, clone_dir)

        return clone_dir

    async def _count_authorization_files(self, repo_path: Path, changed_files: set[str] | None = None) -> int:
        """Count files with potential authorization code without loading them into memory.

        Args:
            repo_path: Path to repository
            changed_files: Optional set of changed files to filter by (for incremental scans)

        Returns:
            Count of files to be scanned
        """
        count = 0
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

            # Filter by changed files if incremental scan
            if changed_files is not None:
                relative_path = str(file_path.relative_to(repo_path))
                if relative_path not in changed_files:
                    continue

            count += 1

        return count

    async def _stream_authorization_files(
        self, repo_path: Path, repository: Repository, changed_files: set[str] | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream files containing authorization code one at a time (generator).

        This is a memory-efficient streaming version that yields files as they are discovered,
        rather than loading all files into memory at once.

        Args:
            repo_path: Path to repository
            repository: Repository model instance for logging secrets
            changed_files: Optional set of changed files to filter by (for incremental scans)

        Yields:
            File information dictionaries one at a time
        """
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

            relative_path = file_path.relative_to(repo_path)

            # Filter by changed files if incremental scan
            if changed_files is not None:
                if str(relative_path) not in changed_files:
                    continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

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
                        "Secrets logged for audit."
                    )

                # Check for authorization patterns
                matches = []
                for pattern in AUTH_PATTERNS:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count("\n") + 1
                        matches.append({
                            "pattern": pattern,
                            "line": line_num,
                            "text": match.group(),
                        })

                # Only yield files that have authorization patterns
                if matches:
                    yield {
                        "path": str(relative_path),
                        "content": content,
                        "matches": matches,
                    }

            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                continue

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

                # Use Java-specific scanner for .java files
                if file_path.endswith(".java"):
                    if self.java_scanner.has_authorization_code(content):
                        # Extract detailed authorization info via tree-sitter
                        java_details = self.java_scanner.extract_authorization_details(
                            content, str(relative_path)
                        )

                        # Convert to matches format
                        matches = [
                            {
                                "pattern": detail.get("pattern", ""),
                                "line": detail.get("line_start", 0),
                                "text": detail.get("text", ""),
                                "java_detail": detail,  # Store full detail for prompt enhancement
                            }
                            for detail in java_details
                        ]
                    else:
                        matches = []
                # Use C#-specific scanner for .cs files
                elif file_path.endswith(".cs"):
                    if self.csharp_scanner.has_authorization_code(content):
                        # Extract detailed authorization info via tree-sitter
                        csharp_details = self.csharp_scanner.extract_authorization_details(
                            content, str(relative_path)
                        )

                        # Convert to matches format
                        matches = [
                            {
                                "pattern": detail.get("pattern", ""),
                                "line": detail.get("line_start", 0),
                                "text": detail.get("text", ""),
                                "csharp_detail": detail,  # Store full detail for prompt enhancement
                            }
                            for detail in csharp_details
                        ]
                    else:
                        matches = []
                # Use Python-specific scanner for .py files
                elif file_path.endswith(".py"):
                    if self.python_scanner.has_authorization_code(content):
                        # Extract detailed authorization info via tree-sitter
                        python_details = self.python_scanner.extract_authorization_details(
                            content, str(relative_path)
                        )

                        # Convert to matches format
                        matches = [
                            {
                                "pattern": detail.get("pattern", ""),
                                "line": detail.get("line_start", 0),
                                "text": detail.get("text", ""),
                                "python_detail": detail,  # Store full detail for prompt enhancement
                            }
                            for detail in python_details
                        ]
                    else:
                        matches = []
                # Use JavaScript-specific scanner for .js/.ts/.jsx/.tsx files
                elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                    patterns = self.javascript_scanner.analyze_file(content, str(relative_path))

                    # Check if any authorization patterns were found
                    if (patterns["decorators"] or patterns["middleware"] or
                        patterns["method_calls"] or patterns["conditionals"]):
                        # Convert to matches format
                        matches = []

                        for decorator in patterns["decorators"]:
                            matches.append({
                                "pattern": f"@{decorator['decorator']}",
                                "line": decorator["line"],
                                "text": decorator["context"],
                                "javascript_detail": decorator,
                            })

                        for middleware in patterns["middleware"]:
                            matches.append({
                                "pattern": middleware["middleware"],
                                "line": middleware["line"],
                                "text": middleware["context"],
                                "javascript_detail": middleware,
                            })

                        for method_call in patterns["method_calls"]:
                            matches.append({
                                "pattern": method_call["method"],
                                "line": method_call["line"],
                                "text": method_call["context"],
                                "javascript_detail": method_call,
                            })

                        for conditional in patterns["conditionals"]:
                            matches.append({
                                "pattern": conditional["condition"],
                                "line": conditional["line"],
                                "text": conditional["context"],
                                "javascript_detail": conditional,
                            })
                    else:
                        matches = []
                else:
                    # Search for authorization patterns (other files)
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
        self, repo: Repository, file_path: str, content: str, matches: list[dict], repo_path: Path
    ) -> list[Policy]:
        """Extract policies from a file using Claude AI.

        Args:
            repo: Repository model
            file_path: Path to the file
            content: File content (should already be redacted)
            matches: Authorization pattern matches
            repo_path: Path to the repository root (for evidence validation)

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

            # Generate embeddings for policies
            from app.services.similarity_service import similarity_service
            for policy in policies:
                try:
                    embedding = similarity_service.generate_embedding(policy)
                    policy.embedding = embedding
                except Exception as e:
                    logger.error(f"Failed to generate embedding for policy {policy.id}: {e}")

            self.db.commit()

            # Validate evidence immediately after extraction
            from app.services.evidence_validation_service import EvidenceValidationService
            validation_service = EvidenceValidationService(self.db)

            for policy in policies:
                for evidence in policy.evidence:
                    try:
                        validation_service.validate_evidence(evidence.id, repo_path)
                    except Exception as e:
                        logger.error(f"Failed to validate evidence {evidence.id}: {e}")

            # Apply auto-approval if enabled
            if repo.tenant_id:
                from app.services.auto_approval_service import AutoApprovalService
                auto_approval_service = AutoApprovalService(self.db)

                for policy in policies:
                    try:
                        should_approve, reasoning = auto_approval_service.evaluate_policy(
                            repo.tenant_id, policy
                        )
                        if should_approve:
                            policy.status = PolicyStatus.APPROVED
                            logger.info(
                                f"Auto-approved policy {policy.id}: {reasoning}",
                                tenant_id=repo.tenant_id
                            )
                    except Exception as e:
                        logger.error(f"Error in auto-approval for policy {policy.id}: {e}")
                        # Continue without auto-approval

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

        # Check if this is a Java file with tree-sitter details
        java_details = []
        if file_path.endswith(".java"):
            java_details = [m.get("java_detail") for m in matches if m.get("java_detail")]

        # Check if this is a C# file with tree-sitter details
        csharp_details = []
        if file_path.endswith(".cs"):
            csharp_details = [m.get("csharp_detail") for m in matches if m.get("csharp_detail")]

        # Check if this is a Python file with tree-sitter details
        python_details = []
        if file_path.endswith(".py"):
            python_details = [m.get("python_detail") for m in matches if m.get("python_detail")]

        # Check if this is a JavaScript/TypeScript file with tree-sitter details
        javascript_details = []
        if file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            javascript_details = [m.get("javascript_detail") for m in matches if m.get("javascript_detail")]

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

        # Enhance prompt with Java-specific context if available
        if java_details:
            prompt = self.java_scanner.enhance_prompt_with_java_context(prompt, java_details)

        # Enhance prompt with C#-specific context if available
        if csharp_details:
            prompt = self.csharp_scanner.enhance_prompt_with_csharp_context(prompt, csharp_details)

        # Enhance prompt with Python-specific context if available
        if python_details:
            prompt = self.python_scanner.enhance_prompt_with_python_context(prompt, python_details)

        # Enhance prompt with JavaScript-specific context if available
        if javascript_details or file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            enhancement = self.javascript_scanner.enhance_prompt(content, file_path)
            if enhancement:
                prompt += enhancement

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

    async def _scan_database_repository(
        self,
        repo: Repository,
        scan_progress: ScanProgress,
        start_time: datetime,
        start_memory_mb: float,
        tenant_id: str | None,
    ) -> dict[str, Any]:
        """Scan a database repository for stored procedures with authorization logic.

        Args:
            repo: Repository object
            scan_progress: Scan progress tracker
            start_time: Scan start time
            start_memory_mb: Initial memory usage
            tenant_id: Tenant ID

        Returns:
            Scan results dictionary
        """
        logger.info(
            "scanning_database_repository",
            repository_id=repo.id,
            repository_name=repo.name,
            tenant_id=tenant_id,
        )

        try:
            # Update scan progress to processing
            scan_progress.status = ScanStatus.PROCESSING
            self.db.commit()

            # Scan database using database scanner service
            scan_result = await self.database_scanner.scan_database(
                repository=repo,
                tenant_id=tenant_id,
            )

            policies = scan_result["policies"]
            procedures_scanned = scan_result["procedures_scanned"]
            total_procedures = scan_result["total_procedures"]

            # Update scan progress
            scan_progress.total_files = total_procedures
            scan_progress.processed_files = procedures_scanned
            scan_progress.policies_extracted = len(policies)
            scan_progress.total_batches = 1
            scan_progress.current_batch = 1
            self.db.commit()

            # Save policies to database
            for policy in policies:
                self.db.add(policy)
            self.db.commit()

            # Update scan progress to completed
            scan_progress.status = ScanStatus.COMPLETED
            scan_progress.completed_at = datetime.utcnow()
            self.db.commit()

            # Update repository status and last scan time
            repo.status = RepositoryStatus.CONNECTED
            repo.last_scan_at = datetime.utcnow()
            self.db.commit()

            # Calculate metrics
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            end_memory_mb = self._get_memory_usage_mb()
            memory_increase_mb = end_memory_mb - start_memory_mb

            # Record metrics
            increment_scan_count()
            increment_policies_extracted(len(policies))
            record_scan_duration(duration)

            logger.info(
                "database_scan_completed",
                repository_id=repo.id,
                procedures_scanned=procedures_scanned,
                total_procedures=total_procedures,
                policies_extracted=len(policies),
                duration_seconds=round(duration, 2),
                memory_increase_mb=round(memory_increase_mb, 2),
            )

            return {
                "repository_id": repo.id,
                "scan_type": "database",
                "procedures_scanned": procedures_scanned,
                "total_procedures": total_procedures,
                "policies_extracted": len(policies),
                "errors": 0,
                "duration_seconds": duration,
                "start_memory_mb": round(start_memory_mb, 2),
                "end_memory_mb": round(end_memory_mb, 2),
                "memory_increase_mb": round(memory_increase_mb, 2),
            }

        except Exception as e:
            logger.error(
                "database_scan_failed",
                repository_id=repo.id,
                error=str(e),
            )

            # Update scan progress to failed
            scan_progress.status = ScanStatus.FAILED
            scan_progress.error_message = str(e)
            scan_progress.completed_at = datetime.utcnow()
            self.db.commit()

            # Update repository status to failed
            repo.status = RepositoryStatus.FAILED
            self.db.commit()

            # Record error metric
            increment_error_count()

            raise

    async def _scan_mainframe_repository(
        self,
        repo: Repository,
        scan_progress: ScanProgress,
        start_time: datetime,
        start_memory_mb: float,
        tenant_id: str | None,
    ) -> dict[str, Any]:
        """Scan a mainframe repository for COBOL authorization logic.

        Args:
            repo: Repository object
            scan_progress: Scan progress tracker
            start_time: Scan start time
            start_memory_mb: Initial memory usage
            tenant_id: Tenant ID

        Returns:
            Scan results dictionary
        """
        logger.info(
            "scanning_mainframe_repository",
            repository_id=repo.id,
            repository_name=repo.name,
            tenant_id=tenant_id,
        )

        try:
            # Update scan progress to processing
            scan_progress.status = ScanStatus.PROCESSING
            self.db.commit()

            # Get application_id from repository if linked
            from sqlalchemy.orm import Session as SyncSession
            async_session = self.db

            # Convert async session to use with mainframe scanner
            # The mainframe scanner needs an async session
            from sqlalchemy.ext.asyncio import AsyncSession

            # For now, use None for application_id
            # TODO: Link mainframe repos to applications
            application_id = None

            # Scan mainframe using mainframe scanner service
            scan_result = await self.mainframe_scanner.scan_mainframe_repository(
                session=async_session,
                repository=repo,
                tenant_id=tenant_id,
                application_id=application_id,
            )

            files_scanned = scan_result["files_scanned"]
            files_with_auth = scan_result["files_with_authorization"]
            policies_extracted = scan_result["policies_extracted"]

            # Update scan progress
            scan_progress.total_files = files_scanned
            scan_progress.processed_files = files_scanned
            scan_progress.policies_extracted = policies_extracted
            scan_progress.total_batches = 1
            scan_progress.current_batch = 1
            self.db.commit()

            # Complete scan progress
            scan_progress.status = ScanStatus.COMPLETED
            scan_progress.completed_at = datetime.utcnow()
            self.db.commit()

            # Update repository status
            repo.status = RepositoryStatus.CONNECTED
            repo.last_scan_at = datetime.utcnow()
            self.db.commit()

            # Calculate duration and memory
            duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            end_memory_mb = self._get_memory_usage_mb()
            memory_delta_mb = end_memory_mb - start_memory_mb

            # Record metrics
            increment_scan_count()
            record_scan_duration(duration_seconds)
            increment_policies_extracted(policies_extracted)

            logger.info(
                "mainframe_scan_completed",
                repository_id=repo.id,
                files_scanned=files_scanned,
                files_with_auth=files_with_auth,
                policies_extracted=policies_extracted,
                duration_seconds=round(duration_seconds, 2),
                memory_delta_mb=round(memory_delta_mb, 2),
            )

            return {
                "repository_id": repo.id,
                "files_scanned": files_scanned,
                "files_with_authorization": files_with_auth,
                "policies_extracted": policies_extracted,
                "duration_seconds": round(duration_seconds, 2),
                "start_memory_mb": round(start_memory_mb, 2),
                "end_memory_mb": round(end_memory_mb, 2),
                "memory_delta_mb": round(memory_delta_mb, 2),
                "connection_type": scan_result.get("connection_type", "file_upload"),
            }

        except Exception as e:
            logger.error(
                "mainframe_scan_failed",
                repository_id=repo.id,
                error=str(e),
            )

            # Update scan progress to failed
            scan_progress.status = ScanStatus.FAILED
            scan_progress.error_message = str(e)
            scan_progress.completed_at = datetime.utcnow()
            self.db.commit()

            # Update repository status to failed
            repo.status = RepositoryStatus.FAILED
            self.db.commit()

            # Record error metric
            increment_error_count()

            raise
