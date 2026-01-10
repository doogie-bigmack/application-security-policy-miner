"""Database models for policy fixes."""

import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.repository import Base


class FixStatus(str, enum.Enum):
    """Status of a policy fix."""

    PENDING = "pending"
    REVIEWED = "reviewed"
    APPLIED = "applied"
    REJECTED = "rejected"


class FixSeverity(str, enum.Enum):
    """Severity of the security gap."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyFix(Base):
    """Model for AI-generated policy fixes."""

    __tablename__ = "policy_fixes"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(255), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    # Security gap analysis
    security_gap_type = Column(String(255), nullable=False)  # incomplete_logic, privilege_escalation, always_true, etc.
    severity = Column(Enum(FixSeverity), nullable=False, default=FixSeverity.MEDIUM)
    gap_description = Column(Text, nullable=False)  # AI description of what's missing or wrong
    missing_checks = Column(Text, nullable=True)  # JSON array of missing security checks

    # Original and fixed policy
    original_policy = Column(Text, nullable=False)  # JSON of original policy
    fixed_policy = Column(Text, nullable=False)  # JSON of fixed policy with complete logic
    fix_explanation = Column(Text, nullable=False)  # AI explanation of what was fixed

    # Test cases to prove fix prevents security gaps
    test_cases = Column(Text, nullable=True)  # JSON array of test cases

    # Attack scenario for privilege escalation risks
    attack_scenario = Column(Text, nullable=True)  # Detailed attack scenario description

    # Review tracking
    status = Column(Enum(FixStatus), nullable=False, default=FixStatus.PENDING)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    policy = relationship("Policy", back_populates="fixes")
    tenant = relationship("Tenant")


# Add relationship to Policy model
# This will be added to policy.py via import
