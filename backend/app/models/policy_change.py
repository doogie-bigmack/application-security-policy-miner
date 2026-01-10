"""PolicyChange and WorkItem models for change detection."""
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from .repository import Base


class ChangeType(str, Enum):
    """Type of policy change."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


class WorkItemStatus(str, Enum):
    """Work item status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class WorkItemPriority(str, Enum):
    """Work item priority."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyChange(Base):
    """Policy change model for tracking policy modifications over time."""

    __tablename__ = "policy_changes"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)  # Current policy (null if deleted)
    previous_policy_id = Column(Integer, nullable=True)  # Previous version (null if added)

    # Change details
    change_type = Column(SAEnum(ChangeType), nullable=False)

    # Before state (for modified/deleted policies)
    before_subject = Column(String(500), nullable=True)
    before_resource = Column(String(500), nullable=True)
    before_action = Column(String(500), nullable=True)
    before_conditions = Column(Text, nullable=True)

    # After state (for added/modified policies)
    after_subject = Column(String(500), nullable=True)
    after_resource = Column(String(500), nullable=True)
    after_action = Column(String(500), nullable=True)
    after_conditions = Column(Text, nullable=True)

    # Metadata
    description = Column(Text, nullable=True)  # AI-generated description of the change
    diff_summary = Column(Text, nullable=True)  # Human-readable diff summary

    # Relationships
    work_items = relationship("WorkItem", back_populates="policy_change", cascade="all, delete-orphan")

    # Timestamps
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    tenant_id = Column(String(100), nullable=True, index=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<PolicyChange {self.change_type} - {self.after_subject or self.before_subject}>"


class WorkItem(Base):
    """Work item model for tracking tasks related to policy changes."""

    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, index=True)
    policy_change_id = Column(Integer, ForeignKey("policy_changes.id"), nullable=False)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)

    # Work item details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(WorkItemStatus), default=WorkItemStatus.OPEN)
    priority = Column(SAEnum(WorkItemPriority), default=WorkItemPriority.MEDIUM)

    # Assignment
    assigned_to = Column(String(255), nullable=True)  # User email or ID

    # Spaghetti detection flags
    is_spaghetti_detection = Column(Integer, default=0)  # 1 if this is a spaghetti code detection
    refactoring_suggestion = Column(Text, nullable=True)  # AI-generated refactoring suggestion

    # Relationships
    policy_change = relationship("PolicyChange", back_populates="work_items")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    tenant_id = Column(String(100), nullable=True, index=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<WorkItem {self.title} - {self.status}>"
