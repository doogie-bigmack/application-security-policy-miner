"""Duplicate policy group model for tracking policy duplicates across applications."""

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from .repository import Base


class DuplicateGroupStatus(str, Enum):
    """Status of duplicate policy group."""

    DETECTED = "detected"  # Duplicates detected, awaiting review
    CONSOLIDATED = "consolidated"  # Duplicates have been consolidated
    DISMISSED = "dismissed"  # Duplicates reviewed and dismissed as false positives


class DuplicatePolicyGroup(Base):
    """Model for tracking groups of duplicate policies across applications."""

    __tablename__ = "duplicate_policy_groups"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), ForeignKey("tenants.tenant_id"), nullable=False, index=True)

    # Group metadata
    status = Column(SAEnum(DuplicateGroupStatus), nullable=False, default=DuplicateGroupStatus.DETECTED)
    group_name = Column(String(500), nullable=True)  # Optional user-friendly name for the group
    description = Column(Text, nullable=True)  # Description of what these policies do

    # Similarity metrics
    avg_similarity_score = Column(Float, nullable=False)  # Average similarity score across all pairs
    min_similarity_score = Column(Float, nullable=False)  # Minimum similarity score in the group
    policy_count = Column(Integer, nullable=False)  # Number of policies in this duplicate group

    # Consolidation info
    consolidated_policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)  # The centralized policy (if consolidated)
    consolidation_notes = Column(Text, nullable=True)  # Notes about consolidation decision

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    consolidated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="duplicate_policy_groups")
    policies = relationship(
        "Policy",
        secondary="duplicate_policy_group_members",
        back_populates="duplicate_groups",
    )
    consolidated_policy = relationship(
        "Policy",
        foreign_keys=[consolidated_policy_id],
        uselist=False,
    )


class DuplicatePolicyGroupMember(Base):
    """Association table for policies in duplicate groups."""

    __tablename__ = "duplicate_policy_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("duplicate_policy_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_to_group = Column(Float, nullable=False)  # Similarity score to the group centroid/representative

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
