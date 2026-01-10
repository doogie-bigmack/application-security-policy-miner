"""Policy and Evidence models."""
from datetime import UTC, datetime
from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from .repository import Base


class PolicyStatus(str, Enum):
    """Policy status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    """Risk level for policies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceType(str, Enum):
    """Source type for policies."""

    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    """Evidence validation status."""

    PENDING = "pending"  # Not yet validated
    VALID = "valid"  # Evidence matches source file
    INVALID = "invalid"  # Evidence does not match source file
    FILE_NOT_FOUND = "file_not_found"  # Source file no longer exists
    LINE_MISMATCH = "line_mismatch"  # Line numbers out of range


class Policy(Base):
    """Policy model for storing extracted authorization policies."""

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)

    # Who/What/How/When components
    subject = Column(String(500), nullable=False)  # Who (e.g., "Manager", "Admin")
    resource = Column(String(500), nullable=False)  # What (e.g., "Expense Report", "User Account")
    action = Column(String(500), nullable=False)  # How (e.g., "approve", "delete")
    conditions = Column(Text, nullable=True)  # When (e.g., "amount < $5000", "user.department == request.department")

    # Risk scoring
    risk_score = Column(Float, nullable=True)  # Overall risk score (0-100)
    risk_level = Column(SAEnum(RiskLevel), nullable=True)
    complexity_score = Column(Float, nullable=True)
    impact_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    historical_score = Column(Float, nullable=True)  # Historical change frequency score
    embedding = Column(Vector(1536), nullable=True)  # Policy embedding for similarity search (1536 dims for Claude embeddings)

    # Status and metadata
    status = Column(SAEnum(PolicyStatus), default=PolicyStatus.PENDING)
    description = Column(Text, nullable=True)  # AI-generated description
    source_type = Column(SAEnum(SourceType), default=SourceType.UNKNOWN, nullable=False)  # Frontend/Backend/Database
    approval_comment = Column(Text, nullable=True)  # Comment when approving/rejecting
    reviewed_by = Column(String(255), nullable=True)  # Email of user who reviewed
    reviewed_at = Column(DateTime(timezone=True), nullable=True)  # When the review happened

    # Relationships
    evidence = relationship("Evidence", back_populates="policy", cascade="all, delete-orphan")
    advisories = relationship("CodeAdvisory", back_populates="policy", cascade="all, delete-orphan")
    fixes = relationship("PolicyFix", back_populates="policy", cascade="all, delete-orphan")
    application = relationship("Application", foreign_keys=[application_id])

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
        return f"<Policy {self.subject} -> {self.action} -> {self.resource}>"


class Evidence(Base):
    """Evidence model for storing code snippets that support policies."""

    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)

    # Source location
    file_path = Column(String(1000), nullable=False)
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)

    # Code snippet
    code_snippet = Column(Text, nullable=False)

    # Validation status
    validation_status = Column(SAEnum(ValidationStatus), default=ValidationStatus.PENDING, nullable=False)
    validation_error = Column(Text, nullable=True)  # Details if validation fails
    validated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    policy = relationship("Policy", back_populates="evidence")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        """String representation."""
        return f"<Evidence {self.file_path}:{self.line_start}-{self.line_end}>"
