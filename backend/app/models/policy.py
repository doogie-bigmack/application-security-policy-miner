"""Policy models for storing extracted authorization policies."""

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from app.models.repository import Base


class PolicyStatus(str, Enum):
    """Policy status."""

    EXTRACTED = "EXTRACTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_REVIEW = "PENDING_REVIEW"


class RiskLevel(str, Enum):
    """Risk level for policies."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceType(str, Enum):
    """Source type for policies."""

    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DATABASE = "DATABASE"
    UNKNOWN = "UNKNOWN"


class Policy(Base):
    """Policy model for storing extracted authorization policies."""

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)

    # Policy Components (Who/What/How/When)
    subject = Column(String(500), nullable=False)  # Who: user role, group, etc.
    resource = Column(String(500), nullable=False)  # What: resource being accessed
    action = Column(String(500), nullable=False)  # How: action being performed
    conditions = Column(Text, nullable=True)  # When: conditions, constraints

    # Metadata
    description = Column(Text, nullable=True)
    status = Column(SAEnum(PolicyStatus), default=PolicyStatus.EXTRACTED)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.MEDIUM)
    risk_score = Column(Integer, default=50)  # 0-100
    complexity_score = Column(Integer, nullable=True)
    impact_score = Column(Integer, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    historical_score = Column(Integer, nullable=True)
    source_type = Column(SAEnum(SourceType), nullable=False, default=SourceType.UNKNOWN)

    # Review fields
    approval_comment = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Application reference
    application_id = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Multi-tenancy
    tenant_id = Column(String(100), nullable=True, index=True)

    # Relationships
    evidence = relationship("PolicyEvidence", back_populates="policy", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Policy {self.subject} -> {self.action} on {self.resource}>"


class PolicyEvidence(Base):
    """Evidence linking policies to source code."""

    __tablename__ = "policy_evidence"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False, index=True)

    # Source location
    file_path = Column(String(1000), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    # Code snippet
    code_snippet = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    policy = relationship("Policy", back_populates="evidence")

    def __repr__(self) -> str:
        """String representation."""
        return f"<PolicyEvidence {self.file_path}:{self.start_line}-{self.end_line}>"
