"""Mainframe-specific scanning service for COBOL code."""
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import Policy, SourceType
from app.models.repository import Repository
from app.services.cobol_scanner_service import CobolScannerService
from app.services.llm_service import LLMService
from app.services.risk_scoring_service import RiskScoringService

logger = logging.getLogger(__name__)


class MainframeScannerService:
    """Service for scanning mainframe repositories (COBOL code)."""

    def __init__(self):
        """Initialize mainframe scanner."""
        self.cobol_scanner = CobolScannerService()
        self.llm_service = LLMService()
        self.risk_service = RiskScoringService()

    async def scan_mainframe_repository(
        self,
        session: AsyncSession,
        repository: Repository,
        tenant_id: str,
        application_id: str | None = None,
    ) -> dict[str, Any]:
        """Scan a mainframe repository for COBOL authorization patterns.

        Args:
            session: Database session
            repository: Repository to scan
            tenant_id: Tenant ID
            application_id: Optional application ID

        Returns:
            Scan results summary
        """
        logger.info(
            f"Starting mainframe scan for repository {repository.id}",
            extra={"tenant_id": tenant_id, "repository_id": repository.id}
        )

        try:
            # Extract connection config
            config = repository.connection_config or {}
            connection_type = config.get("connection_type", "file_upload")

            # Get COBOL source files
            cobol_files = await self._retrieve_cobol_files(repository, config)

            logger.info(
                f"Retrieved {len(cobol_files)} COBOL files from mainframe",
                extra={"tenant_id": tenant_id, "repository_id": repository.id, "file_count": len(cobol_files)}
            )

            # Scan each file for authorization patterns
            policies_created = 0
            files_with_auth = 0

            for file_info in cobol_files:
                file_path = file_info["path"]
                content = file_info["content"]

                # Check if file contains authorization code
                if not self.cobol_scanner.has_authorization_code(content):
                    continue

                files_with_auth += 1
                logger.debug(
                    f"Found authorization patterns in {file_path}",
                    extra={"tenant_id": tenant_id, "file_path": file_path}
                )

                # Extract detailed authorization information
                details = self.cobol_scanner.extract_authorization_details(content, file_path)

                # Extract policies using LLM
                policies = await self._extract_policies_from_cobol(
                    session=session,
                    repository=repository,
                    file_path=file_path,
                    content=content,
                    details=details,
                    tenant_id=tenant_id,
                    application_id=application_id,
                )

                policies_created += len(policies)

            logger.info(
                f"Mainframe scan complete for repository {repository.id}",
                extra={
                    "tenant_id": tenant_id,
                    "repository_id": repository.id,
                    "files_scanned": len(cobol_files),
                    "files_with_auth": files_with_auth,
                    "policies_created": policies_created,
                }
            )

            return {
                "files_scanned": len(cobol_files),
                "files_with_authorization": files_with_auth,
                "policies_extracted": policies_created,
                "connection_type": connection_type,
            }

        except Exception as e:
            logger.error(
                f"Error scanning mainframe repository {repository.id}: {e}",
                extra={"tenant_id": tenant_id, "repository_id": repository.id},
                exc_info=True
            )
            raise

    async def _retrieve_cobol_files(
        self,
        repository: Repository,
        config: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Retrieve COBOL source files from mainframe.

        Args:
            repository: Repository configuration
            config: Connection configuration

        Returns:
            List of file dictionaries with path and content
        """
        connection_type = config.get("connection_type", "file_upload")

        if connection_type == "file_upload":
            # For MVP, support manual file upload via MinIO/S3
            return await self._retrieve_from_storage(repository)
        elif connection_type == "ftp":
            # Future: FTP file transfer
            logger.warning("FTP connection not yet implemented, using file upload")
            return await self._retrieve_from_storage(repository)
        elif connection_type == "sftp":
            # Future: SFTP file transfer
            logger.warning("SFTP connection not yet implemented, using file upload")
            return await self._retrieve_from_storage(repository)
        elif connection_type == "tn3270":
            # Future: TN3270 terminal emulation
            logger.warning("TN3270 connection not yet implemented, using file upload")
            return await self._retrieve_from_storage(repository)
        else:
            logger.warning(f"Unknown connection type: {connection_type}, using file upload")
            return await self._retrieve_from_storage(repository)

    async def _retrieve_from_storage(self, repository: Repository) -> list[dict[str, str]]:
        """Retrieve uploaded COBOL files from object storage.

        Args:
            repository: Repository configuration

        Returns:
            List of file dictionaries
        """
        # For MVP, we'll support COBOL files uploaded to the repository's storage location
        # This simulates mainframe file retrieval without requiring actual mainframe access

        # In a real implementation, this would:
        # 1. Connect to MinIO/S3
        # 2. List files in repository's storage bucket
        # 3. Filter for COBOL extensions (.cbl, .cobol, .cob, .txt)
        # 4. Download and return file contents

        # For now, return empty list (will be populated when files are uploaded)
        logger.info(
            f"Retrieving COBOL files from storage for repository {repository.id}",
            extra={"repository_id": repository.id}
        )

        # TODO: Implement MinIO/S3 file retrieval
        # This would integrate with the existing object_storage_service
        return []

    async def _extract_policies_from_cobol(
        self,
        session: AsyncSession,
        repository: Repository,
        file_path: str,
        content: str,
        details: list[dict[str, Any]],
        tenant_id: str,
        application_id: str | None,
    ) -> list[Policy]:
        """Extract policies from COBOL code using LLM.

        Args:
            session: Database session
            repository: Repository
            file_path: Path to COBOL file
            content: COBOL source code
            details: Authorization details from COBOL scanner
            tenant_id: Tenant ID
            application_id: Optional application ID

        Returns:
            List of created Policy objects
        """
        # Build extraction prompt
        base_prompt = self._build_extraction_prompt(file_path, content)

        # Enhance with COBOL-specific context
        enhanced_prompt = self.cobol_scanner.enhance_prompt_with_cobol_context(base_prompt, details)

        # Call LLM to extract policies
        try:
            response = await self.llm_service.extract_policies(enhanced_prompt)

            if not response or not isinstance(response, list):
                logger.warning(
                    f"Invalid LLM response for {file_path}",
                    extra={"tenant_id": tenant_id, "file_path": file_path}
                )
                return []

            # Create Policy objects
            policies = []
            for policy_data in response:
                # Calculate risk scores
                risk_scores = self.risk_service.calculate_risk_scores(
                    policy_data.get("subject", ""),
                    policy_data.get("resource", ""),
                    policy_data.get("action", ""),
                    policy_data.get("conditions", ""),
                )

                # Create evidence list
                evidence_list = []
                for detail in details[:5]:  # Limit to first 5 details
                    evidence_list.append({
                        "file_path": file_path,
                        "line_start": detail["line_start"],
                        "line_end": detail["line_end"],
                        "code_snippet": detail["text"],
                        "context": detail.get("context", ""),
                    })

                # Create Policy
                policy = Policy(
                    tenant_id=tenant_id,
                    repository_id=repository.id,
                    application_id=application_id,
                    source_type=SourceType.BACKEND,  # COBOL is backend/mainframe code
                    subject=policy_data.get("subject", ""),
                    resource=policy_data.get("resource", ""),
                    action=policy_data.get("action", ""),
                    conditions=policy_data.get("conditions", ""),
                    evidence=evidence_list,
                    file_path=file_path,
                    line_start=details[0]["line_start"] if details else 1,
                    line_end=details[-1]["line_end"] if details else 1,
                    complexity_score=risk_scores["complexity_score"],
                    impact_score=risk_scores["impact_score"],
                    confidence_score=risk_scores["confidence_score"],
                    risk_score=risk_scores["risk_score"],
                    risk_level=risk_scores["risk_level"],
                )

                session.add(policy)
                policies.append(policy)

            await session.commit()

            logger.info(
                f"Extracted {len(policies)} policies from {file_path}",
                extra={"tenant_id": tenant_id, "file_path": file_path, "policy_count": len(policies)}
            )

            return policies

        except Exception as e:
            logger.error(
                f"Error extracting policies from {file_path}: {e}",
                extra={"tenant_id": tenant_id, "file_path": file_path},
                exc_info=True
            )
            return []

    def _build_extraction_prompt(self, file_path: str, content: str) -> str:
        """Build LLM extraction prompt for COBOL code.

        Args:
            file_path: Path to file
            content: COBOL source code

        Returns:
            Extraction prompt
        """
        # Truncate content if too long (COBOL files can be large)
        max_length = 8000  # Leave room for context
        if len(content) > max_length:
            content = content[:max_length] + "\n... (truncated)"

        prompt = f"""Analyze this COBOL mainframe code and extract authorization policies.

COBOL File: {file_path}

COBOL Code:
```cobol
{content}
```

Extract authorization policies in the format:
- WHO can perform the action (subject: user roles, departments, security levels)
- WHAT resource is being protected (resource: data, programs, transactions)
- HOW they can interact (action: read, write, execute, approve, etc.)
- WHEN/under what conditions (conditions: time, location, approval status, etc.)

Focus on:
- RACF authorization calls (RACFAUTH, RACFTEST, RACROUTE, etc.)
- Top Secret security checks (TSS commands, TSO-LOGON/LOGOFF)
- ACF2 authorization (ACFTEST, GETUID, ACF2 commands)
- CICS security (EXEC CICS LINK with security checks)
- User ID, role, department, and security level checks
- EVALUATE and IF statements controlling access
- CALL statements to security modules

Translate mainframe security concepts to modern PBAC:
- RACF USER-ID → subject
- RACF RESOURCE → resource
- RACF ACCESS (READ/UPDATE/ALTER/CONTROL) → action
- Security levels, departments, roles → conditions

Return your response as a JSON array of policies. Each policy should have:
- subject: Who can perform the action
- resource: What is being accessed
- action: How they can interact
- conditions: When/under what conditions

Example:
[
  {{
    "subject": "Users with RACF role MANAGER",
    "resource": "Employee payroll records",
    "action": "UPDATE",
    "conditions": "User department matches employee department AND security level >= 5"
  }}
]

Return only the JSON array, no other text.
"""

        return prompt
