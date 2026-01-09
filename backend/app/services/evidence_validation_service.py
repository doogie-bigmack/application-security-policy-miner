"""Evidence validation service - prevents AI hallucination by verifying evidence matches source files."""
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.policy import Evidence, ValidationStatus

logger = logging.getLogger(__name__)


class EvidenceValidationService:
    """Service for validating evidence against source files."""

    def __init__(self, db: Session):
        """Initialize the evidence validation service.

        Args:
            db: Database session
        """
        self.db = db

    def validate_evidence(self, evidence_id: int, repository_path: str) -> dict[str, str]:
        """Validate a single evidence item against its source file.

        Args:
            evidence_id: ID of the evidence to validate
            repository_path: Path to the repository containing the source files

        Returns:
            Dictionary with validation result
        """
        evidence = self.db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            return {"status": "error", "message": f"Evidence {evidence_id} not found"}

        logger.info(f"Validating evidence {evidence_id}: {evidence.file_path}:{evidence.line_start}-{evidence.line_end}")

        # Build absolute file path
        file_path = Path(repository_path) / evidence.file_path
        logger.debug(f"Checking file path: {file_path}")

        # Check if file exists
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            evidence.validation_status = ValidationStatus.FILE_NOT_FOUND
            evidence.validation_error = f"Source file not found: {evidence.file_path}"
            evidence.validated_at = datetime.now(UTC)
            self.db.commit()
            return {
                "status": "invalid",
                "validation_status": ValidationStatus.FILE_NOT_FOUND.value,
                "message": evidence.validation_error,
            }

        # Read file and extract lines
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Check if line numbers are valid
            if evidence.line_start < 1 or evidence.line_end > len(lines):
                logger.warning(
                    f"Line numbers out of range: {evidence.line_start}-{evidence.line_end} (file has {len(lines)} lines)"
                )
                evidence.validation_status = ValidationStatus.LINE_MISMATCH
                evidence.validation_error = (
                    f"Line numbers {evidence.line_start}-{evidence.line_end} out of range (file has {len(lines)} lines)"
                )
                evidence.validated_at = datetime.now(UTC)
                self.db.commit()
                return {
                    "status": "invalid",
                    "validation_status": ValidationStatus.LINE_MISMATCH.value,
                    "message": evidence.validation_error,
                }

            # Extract actual code from file (convert to 0-based indexing)
            actual_code_lines = lines[evidence.line_start - 1 : evidence.line_end]
            actual_code = "".join(actual_code_lines).rstrip()

            # Normalize whitespace for comparison
            stored_snippet = evidence.code_snippet.rstrip()
            actual_snippet = actual_code.rstrip()

            # Compare code snippets
            if stored_snippet == actual_snippet:
                logger.info(f"Evidence {evidence_id} validated successfully")
                evidence.validation_status = ValidationStatus.VALID
                evidence.validation_error = None
                evidence.validated_at = datetime.now(UTC)
                self.db.commit()
                return {
                    "status": "valid",
                    "validation_status": ValidationStatus.VALID.value,
                    "message": "Evidence matches source file",
                }
            else:
                # Code doesn't match - possible hallucination or file changed
                logger.warning(f"Evidence {evidence_id} code mismatch")
                logger.debug(f"Expected:\n{stored_snippet[:200]}")
                logger.debug(f"Actual:\n{actual_snippet[:200]}")

                evidence.validation_status = ValidationStatus.INVALID
                evidence.validation_error = "Code snippet does not match source file (possible hallucination or file changed)"
                evidence.validated_at = datetime.now(UTC)
                self.db.commit()
                return {
                    "status": "invalid",
                    "validation_status": ValidationStatus.INVALID.value,
                    "message": evidence.validation_error,
                }

        except Exception as e:
            logger.error(f"Error validating evidence {evidence_id}: {e}", exc_info=True)
            evidence.validation_status = ValidationStatus.INVALID
            evidence.validation_error = f"Validation error: {str(e)}"
            evidence.validated_at = datetime.now(UTC)
            self.db.commit()
            return {
                "status": "error",
                "validation_status": ValidationStatus.INVALID.value,
                "message": evidence.validation_error,
            }

    def validate_policy_evidence(self, policy_id: int, repository_path: str) -> dict[str, int | list]:
        """Validate all evidence items for a policy.

        Args:
            policy_id: ID of the policy
            repository_path: Path to the repository

        Returns:
            Dictionary with validation summary
        """
        from app.models.policy import Policy

        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            return {"error": f"Policy {policy_id} not found"}

        results = []
        valid_count = 0
        invalid_count = 0

        for evidence in policy.evidence:
            result = self.validate_evidence(evidence.id, repository_path)
            results.append(
                {
                    "evidence_id": evidence.id,
                    "file_path": evidence.file_path,
                    "validation_status": result.get("validation_status"),
                    "message": result.get("message"),
                }
            )

            if result.get("status") == "valid":
                valid_count += 1
            else:
                invalid_count += 1

        logger.info(
            f"Policy {policy_id} validation complete: {valid_count} valid, {invalid_count} invalid out of {len(policy.evidence)} evidence items"
        )

        return {
            "policy_id": policy_id,
            "total": len(policy.evidence),
            "valid": valid_count,
            "invalid": invalid_count,
            "results": results,
        }

    def validate_repository_evidence(self, repository_id: int, repository_path: str) -> dict[str, int | list]:
        """Validate all evidence items for all policies in a repository.

        Args:
            repository_id: ID of the repository
            repository_path: Path to the repository

        Returns:
            Dictionary with validation summary
        """
        from app.models.policy import Policy

        policies = self.db.query(Policy).filter(Policy.repository_id == repository_id).all()

        total_evidence = 0
        valid_count = 0
        invalid_count = 0
        policy_results = []

        for policy in policies:
            policy_result = self.validate_policy_evidence(policy.id, repository_path)
            policy_results.append(policy_result)
            total_evidence += policy_result.get("total", 0)
            valid_count += policy_result.get("valid", 0)
            invalid_count += policy_result.get("invalid", 0)

        logger.info(
            f"Repository {repository_id} validation complete: {valid_count} valid, {invalid_count} invalid out of {total_evidence} evidence items across {len(policies)} policies"
        )

        return {
            "repository_id": repository_id,
            "total_policies": len(policies),
            "total_evidence": total_evidence,
            "valid": valid_count,
            "invalid": invalid_count,
            "policy_results": policy_results,
        }
