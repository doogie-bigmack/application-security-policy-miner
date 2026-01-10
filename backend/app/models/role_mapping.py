"""Role mapping models for cross-application normalization."""
import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from .repository import Base


class MappingStatus(str, enum.Enum):
    """Status of role mapping."""

    SUGGESTED = "suggested"  # AI suggested, awaiting approval
    APPROVED = "approved"  # Approved by user
    REJECTED = "rejected"  # Rejected by user
    APPLIED = "applied"  # Applied to policies


class RoleMapping(Base):
    """Role mapping model for storing role normalization mappings."""

    __tablename__ = "role_mappings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # Normalization details
    standard_role = Column(String(255), nullable=False, index=True)  # e.g., "ADMIN"
    variant_roles = Column(JSONB, nullable=False)  # e.g., ["admin", "administrator", "sysadmin"]
    affected_applications = Column(JSONB, nullable=False)  # List of application IDs
    affected_policy_count = Column(Integer, nullable=False, default=0)

    # AI analysis
    confidence_score = Column(Integer, nullable=False)  # 0-100
    reasoning = Column(Text, nullable=True)  # AI explanation of why these are equivalent

    # Status and metadata
    status = Column(Enum(MappingStatus), default=MappingStatus.SUGGESTED, nullable=False)
    approved_by = Column(String(255), nullable=True)  # Email of user who approved
    approved_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<RoleMapping {self.standard_role} <- {self.variant_roles}>"
