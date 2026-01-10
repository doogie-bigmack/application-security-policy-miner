"""Inconsistent Enforcement model for tracking cross-application policy inconsistencies."""
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB

from .repository import Base


class InconsistentEnforcementStatus(str, Enum):
    """Status for inconsistent enforcement issues."""

    PENDING = "pending"  # Detected but not reviewed
    ACKNOWLEDGED = "acknowledged"  # Reviewed but not fixed
    RESOLVED = "resolved"  # Fixed with standardized policy
    DISMISSED = "dismissed"  # Determined to be acceptable variation


class InconsistentEnforcementSeverity(str, Enum):
    """Severity levels for inconsistent enforcement."""

    LOW = "low"  # Minor variations, low security impact
    MEDIUM = "medium"  # Moderate variations, some security concerns
    HIGH = "high"  # Significant variations, major security gap
    CRITICAL = "critical"  # Complete lack of protection in some apps


class InconsistentEnforcement(Base):
    """Model for tracking inconsistent policy enforcement across applications."""

    __tablename__ = "inconsistent_enforcements"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # Resource type being protected inconsistently
    resource_type = Column(String(500), nullable=False, index=True)
    resource_description = Column(Text, nullable=True)

    # Affected applications (stored as JSON array of application IDs)
    affected_application_ids = Column(JSONB, nullable=False)

    # Policies involved (stored as JSON array of policy IDs)
    policy_ids = Column(JSONB, nullable=False)

    # Inconsistency details
    inconsistency_description = Column(Text, nullable=False)
    severity = Column(SAEnum(InconsistentEnforcementSeverity), nullable=False, index=True)

    # AI-generated standardized policy recommendation
    recommended_policy = Column(JSONB, nullable=False)
    recommendation_explanation = Column(Text, nullable=False)

    # Status tracking
    status = Column(SAEnum(InconsistentEnforcementStatus), default=InconsistentEnforcementStatus.PENDING)
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<InconsistentEnforcement {self.resource_type}: {self.severity.value}>"
