"""PolicyConflict model for tracking policy conflicts."""
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from .repository import Base


class ConflictStatus(str, Enum):
    """Conflict resolution status."""

    PENDING = "pending"
    RESOLVED = "resolved"


class ConflictType(str, Enum):
    """Type of policy conflict."""

    CONTRADICTORY = "contradictory"  # Policies contradict each other
    OVERLAPPING = "overlapping"  # Policies overlap in scope
    INCONSISTENT = "inconsistent"  # Inconsistent enforcement


class PolicyConflict(Base):
    """Model for storing detected policy conflicts."""

    __tablename__ = "policy_conflicts"

    id = Column(Integer, primary_key=True, index=True)

    # The two conflicting policies
    policy_a_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    policy_b_id = Column(Integer, ForeignKey("policies.id"), nullable=False)

    # Conflict details
    conflict_type = Column(SAEnum(ConflictType), nullable=False)
    description = Column(Text, nullable=False)  # AI-generated description of the conflict
    severity = Column(String(20), nullable=False)  # low, medium, high

    # AI recommendation
    ai_recommendation = Column(Text, nullable=True)  # AI-generated resolution recommendation

    # Resolution
    status = Column(SAEnum(ConflictStatus), default=ConflictStatus.PENDING, nullable=False)
    resolution_strategy = Column(String(100), nullable=True)  # keep_a, keep_b, merge, custom
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    policy_a = relationship("Policy", foreign_keys=[policy_a_id])
    policy_b = relationship("Policy", foreign_keys=[policy_b_id])

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    tenant_id = Column(String(100), nullable=True, index=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<PolicyConflict {self.id}: {self.conflict_type} ({self.status})>"
