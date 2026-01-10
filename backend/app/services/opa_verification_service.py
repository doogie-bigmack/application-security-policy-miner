"""
OPA Verification Service for tracking lasagna architecture migration.

This service verifies that applications have successfully migrated from inline
authorization checks (spaghetti) to calling centralized PBAC (OPA).
"""
import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models.opa_verification import OPAVerification

logger = logging.getLogger(__name__)


class OPAVerificationService:
    """Service for managing OPA verification lifecycle."""

    def __init__(self, db: Session):
        """Initialize the service."""
        self.db = db

    async def create_baseline(
        self,
        tenant_id: str,
        application_id: str,
        policy_id: str,
        inline_checks_count: int,
    ) -> OPAVerification:
        """
        Create a baseline measurement before migration.

        Args:
            tenant_id: Tenant identifier
            application_id: Application being migrated
            policy_id: Policy being centralized
            inline_checks_count: Number of inline authorization checks detected

        Returns:
            OPAVerification: Created verification record
        """
        logger.info(
            "Creating OPA verification baseline",
            extra={
                "tenant_id": tenant_id,
                "application_id": application_id,
                "policy_id": policy_id,
                "inline_checks": inline_checks_count,
            },
        )

        verification = OPAVerification(
            tenant_id=tenant_id,
            application_id=application_id,
            policy_id=policy_id,
            baseline_inline_checks=inline_checks_count,
            baseline_scan_date=datetime.utcnow(),
            verification_status="pending",
        )

        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)

        logger.info(f"Created OPA verification baseline: {verification.id}")
        return verification

    async def mark_refactoring_applied(
        self,
        verification_id: str,
        code_advisory_id: str | None = None,
    ) -> OPAVerification:
        """
        Mark that refactoring has been applied to the application.

        Args:
            verification_id: Verification record ID
            code_advisory_id: Optional code advisory that was applied

        Returns:
            OPAVerification: Updated verification record
        """
        logger.info(
            "Marking refactoring as applied",
            extra={
                "verification_id": verification_id,
                "code_advisory_id": code_advisory_id,
            },
        )

        verification = self.db.query(OPAVerification).filter(
            OPAVerification.id == verification_id
        ).first()

        if not verification:
            raise ValueError(f"Verification {verification_id} not found")

        verification.refactoring_applied = True
        verification.refactoring_applied_at = datetime.utcnow()
        verification.code_advisory_id = code_advisory_id
        verification.verification_status = "in_progress"

        self.db.commit()
        self.db.refresh(verification)

        logger.info(f"Marked refactoring applied for verification {verification_id}")
        return verification

    async def verify_opa_integration(
        self,
        verification_id: str,
        opa_endpoint_url: str,
        timeout_seconds: int = 5,
    ) -> dict:
        """
        Verify that the application can successfully connect to OPA.

        Args:
            verification_id: Verification record ID
            opa_endpoint_url: OPA endpoint URL to test
            timeout_seconds: Timeout for connection test

        Returns:
            dict: Verification results with connection status and latency
        """
        logger.info(
            "Verifying OPA integration",
            extra={
                "verification_id": verification_id,
                "opa_endpoint": opa_endpoint_url,
            },
        )

        verification = self.db.query(OPAVerification).filter(
            OPAVerification.id == verification_id
        ).first()

        if not verification:
            raise ValueError(f"Verification {verification_id} not found")

        # Test OPA connection
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                start_time = datetime.utcnow()

                # Try to reach OPA health endpoint
                response = await client.get(f"{opa_endpoint_url}/health")

                end_time = datetime.utcnow()
                latency_ms = (end_time - start_time).total_seconds() * 1000

                if response.status_code == 200:
                    verification.opa_connection_verified = True
                    verification.opa_endpoint_url = opa_endpoint_url
                    verification.opa_latency_ms = latency_ms

                    logger.info(
                        f"OPA connection verified successfully (latency: {latency_ms:.2f}ms)",
                        extra={"verification_id": verification_id},
                    )

                    result = {
                        "success": True,
                        "latency_ms": latency_ms,
                        "message": "OPA connection verified successfully",
                    }
                else:
                    logger.warning(
                        f"OPA health check returned non-200: {response.status_code}",
                        extra={"verification_id": verification_id},
                    )
                    result = {
                        "success": False,
                        "error": f"OPA health check returned {response.status_code}",
                    }
        except Exception as e:
            logger.error(
                f"Failed to connect to OPA: {str(e)}",
                extra={"verification_id": verification_id},
            )
            result = {
                "success": False,
                "error": str(e),
            }

        verification.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(verification)

        return result

    async def verify_opa_calls_detected(
        self,
        verification_id: str,
        calls_detected: bool,
        inline_checks_remaining: int,
    ) -> OPAVerification:
        """
        Update verification with runtime detection results.

        Args:
            verification_id: Verification record ID
            calls_detected: Whether OPA calls were detected at runtime
            inline_checks_remaining: Number of inline checks still present

        Returns:
            OPAVerification: Updated verification record
        """
        logger.info(
            "Updating OPA call detection results",
            extra={
                "verification_id": verification_id,
                "calls_detected": calls_detected,
                "inline_remaining": inline_checks_remaining,
            },
        )

        verification = self.db.query(OPAVerification).filter(
            OPAVerification.id == verification_id
        ).first()

        if not verification:
            raise ValueError(f"Verification {verification_id} not found")

        verification.opa_calls_detected = calls_detected
        verification.inline_checks_remaining = inline_checks_remaining

        # Calculate spaghetti reduction percentage
        if verification.baseline_inline_checks and verification.baseline_inline_checks > 0:
            checks_eliminated = verification.baseline_inline_checks - inline_checks_remaining
            verification.spaghetti_reduction_percentage = (
                checks_eliminated / verification.baseline_inline_checks
            ) * 100
        else:
            verification.spaghetti_reduction_percentage = 100.0 if inline_checks_remaining == 0 else 0.0

        verification.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(verification)

        logger.info(
            f"Updated OPA call detection: reduction={verification.spaghetti_reduction_percentage:.1f}%",
            extra={"verification_id": verification_id},
        )

        return verification

    async def verify_decision_enforcement(
        self,
        verification_id: str,
        decision_enforced: bool,
        verification_notes: str | None = None,
    ) -> OPAVerification:
        """
        Verify that the application enforces OPA decisions.

        Args:
            verification_id: Verification record ID
            decision_enforced: Whether OPA decisions are being enforced
            verification_notes: Human-readable verification notes

        Returns:
            OPAVerification: Updated verification record
        """
        logger.info(
            "Verifying OPA decision enforcement",
            extra={
                "verification_id": verification_id,
                "enforced": decision_enforced,
            },
        )

        verification = self.db.query(OPAVerification).filter(
            OPAVerification.id == verification_id
        ).first()

        if not verification:
            raise ValueError(f"Verification {verification_id} not found")

        verification.opa_decision_enforced = decision_enforced
        verification.verification_notes = verification_notes
        verification.verification_date = datetime.utcnow()

        # Update status based on completeness
        if verification.is_fully_migrated:
            verification.verification_status = "verified"
            logger.info(
                "Application fully migrated to lasagna architecture!",
                extra={"verification_id": verification_id},
            )
        else:
            verification.verification_status = "in_progress"

        verification.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(verification)

        return verification

    async def measure_latency_comparison(
        self,
        verification_id: str,
        inline_latency_ms: float,
        opa_latency_ms: float,
    ) -> OPAVerification:
        """
        Record latency comparison between inline and centralized authorization.

        Args:
            verification_id: Verification record ID
            inline_latency_ms: Average latency of inline checks
            opa_latency_ms: Average latency of OPA calls

        Returns:
            OPAVerification: Updated verification record
        """
        logger.info(
            "Recording latency comparison",
            extra={
                "verification_id": verification_id,
                "inline_ms": inline_latency_ms,
                "opa_ms": opa_latency_ms,
            },
        )

        verification = self.db.query(OPAVerification).filter(
            OPAVerification.id == verification_id
        ).first()

        if not verification:
            raise ValueError(f"Verification {verification_id} not found")

        verification.inline_latency_ms = inline_latency_ms
        verification.opa_latency_ms = opa_latency_ms

        # Calculate overhead
        verification.latency_overhead_ms = opa_latency_ms - inline_latency_ms
        if inline_latency_ms > 0:
            verification.latency_overhead_percentage = (
                (opa_latency_ms - inline_latency_ms) / inline_latency_ms
            ) * 100
        else:
            verification.latency_overhead_percentage = 0.0

        verification.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(verification)

        logger.info(
            f"Latency overhead: {verification.latency_overhead_ms:.2f}ms ({verification.latency_overhead_percentage:.1f}%)",
            extra={"verification_id": verification_id},
        )

        return verification

    async def get_verification(
        self,
        verification_id: str,
        tenant_id: str,
    ) -> OPAVerification | None:
        """Get a specific verification record."""
        return self.db.query(OPAVerification).filter(
            OPAVerification.id == verification_id,
            OPAVerification.tenant_id == tenant_id,
        ).first()

    async def list_verifications(
        self,
        tenant_id: str,
        application_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[OPAVerification]:
        """
        List verification records with optional filtering.

        Args:
            tenant_id: Tenant identifier
            application_id: Optional application filter
            status: Optional status filter
            limit: Maximum number of records to return

        Returns:
            list[OPAVerification]: List of verification records
        """
        query = self.db.query(OPAVerification).filter(
            OPAVerification.tenant_id == tenant_id
        )

        if application_id:
            query = query.filter(OPAVerification.application_id == application_id)

        if status:
            query = query.filter(OPAVerification.verification_status == status)

        return query.order_by(OPAVerification.created_at.desc()).limit(limit).all()

    async def get_verification_statistics(
        self,
        tenant_id: str,
    ) -> dict:
        """
        Get aggregate statistics for tenant's verifications.

        Args:
            tenant_id: Tenant identifier

        Returns:
            dict: Statistics including total verifications, fully migrated count, etc.
        """
        verifications = self.db.query(OPAVerification).filter(
            OPAVerification.tenant_id == tenant_id
        ).all()

        total = len(verifications)
        fully_migrated = sum(1 for v in verifications if v.is_fully_migrated)
        in_progress = sum(1 for v in verifications if v.verification_status == "in_progress")
        pending = sum(1 for v in verifications if v.verification_status == "pending")

        # Average spaghetti reduction
        reductions = [v.spaghetti_reduction_percentage for v in verifications if v.spaghetti_reduction_percentage is not None]
        avg_reduction = sum(reductions) / len(reductions) if reductions else 0.0

        # Average latency overhead
        overheads = [v.latency_overhead_ms for v in verifications if v.latency_overhead_ms is not None]
        avg_overhead = sum(overheads) / len(overheads) if overheads else 0.0

        return {
            "total_verifications": total,
            "fully_migrated": fully_migrated,
            "in_progress": in_progress,
            "pending": pending,
            "average_spaghetti_reduction_percentage": avg_reduction,
            "average_latency_overhead_ms": avg_overhead,
        }
