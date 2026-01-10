"""
OPA Verification Model for tracking lasagna architecture migration.

Tracks runtime verification of applications calling centralized OPA
instead of inline authorization checks (spaghetti code).
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .repository import Base


class OPAVerification(Base):
    """
    Tracks verification of applications using centralized PBAC (OPA) instead of inline authorization.

    Represents the "lasagna architecture" where authorization is centralized,
    as opposed to "spaghetti architecture" with inline authorization scattered throughout code.
    """
    __tablename__ = "opa_verifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False, index=True)

    # Baseline metrics (before migration)
    baseline_inline_checks = Column(Integer, nullable=True, comment="Number of inline authorization checks before migration")
    baseline_scan_date = Column(DateTime, nullable=True, comment="When baseline metrics were captured")

    # Migration tracking
    code_advisory_id = Column(Integer, ForeignKey("code_advisories.id"), nullable=True, comment="Code advisory used for refactoring")
    refactoring_applied = Column(Boolean, default=False, comment="Whether refactoring was applied to codebase")
    refactoring_applied_at = Column(DateTime, nullable=True)

    # Verification metrics (after migration)
    verification_status = Column(String, default="pending", comment="pending/in_progress/verified/failed")
    verification_date = Column(DateTime, nullable=True, comment="When verification was performed")

    # Runtime call verification
    opa_calls_detected = Column(Boolean, default=False, comment="Whether OPA calls were detected at runtime")
    inline_checks_remaining = Column(Integer, nullable=True, comment="Number of inline checks still present after migration")
    spaghetti_reduction_percentage = Column(Float, nullable=True, comment="Percentage of inline checks eliminated (0-100)")

    # OPA integration verification
    opa_endpoint_url = Column(String, nullable=True, comment="OPA endpoint being called")
    opa_connection_verified = Column(Boolean, default=False, comment="Whether OPA connection was verified")
    opa_decision_enforced = Column(Boolean, default=False, comment="Whether application enforces OPA decisions")

    # Latency comparison
    inline_latency_ms = Column(Float, nullable=True, comment="Average latency of inline checks (milliseconds)")
    opa_latency_ms = Column(Float, nullable=True, comment="Average latency of OPA calls (milliseconds)")
    latency_overhead_ms = Column(Float, nullable=True, comment="Additional latency from centralized OPA (milliseconds)")
    latency_overhead_percentage = Column(Float, nullable=True, comment="Percentage overhead (positive = slower, negative = faster)")

    # Verification evidence
    verification_logs = Column(JSON, nullable=True, comment="Logs/traces from verification process")
    verification_notes = Column(Text, nullable=True, comment="Human-readable verification notes")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="opa_verifications")
    policy = relationship("Policy", back_populates="opa_verifications")
    code_advisory = relationship("CodeAdvisory", back_populates="opa_verifications")

    def __repr__(self) -> str:
        return (
            f"<OPAVerification(id={self.id}, app={self.application_id}, "
            f"status={self.verification_status}, reduction={self.spaghetti_reduction_percentage}%)>"
        )

    @property
    def is_fully_migrated(self) -> bool:
        """Check if application is fully migrated to lasagna architecture."""
        return (
            self.refactoring_applied
            and self.opa_calls_detected
            and self.opa_connection_verified
            and self.opa_decision_enforced
            and (self.inline_checks_remaining == 0 or self.inline_checks_remaining is None)
        )

    @property
    def migration_completeness(self) -> float:
        """Calculate migration completeness percentage (0-100)."""
        total_checks = 5  # Number of verification checks
        completed = 0

        if self.refactoring_applied:
            completed += 1
        if self.opa_calls_detected:
            completed += 1
        if self.opa_connection_verified:
            completed += 1
        if self.opa_decision_enforced:
            completed += 1
        if self.inline_checks_remaining == 0:
            completed += 1

        return (completed / total_checks) * 100
