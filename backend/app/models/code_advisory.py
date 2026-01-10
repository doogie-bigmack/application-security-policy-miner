"""Code advisory models for refactoring suggestions."""

from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.repository import Base


class AdvisoryStatus(str, PyEnum):
    """Status of a code advisory."""

    PENDING = "pending"
    REVIEWED = "reviewed"
    APPLIED = "applied"
    REJECTED = "rejected"


class CodeAdvisory(Base):
    """Code advisory for refactoring inline authorization to PBAC."""

    __tablename__ = "code_advisories"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False)

    # Original code
    file_path = Column(String, nullable=False)
    original_code = Column(Text, nullable=False)
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)

    # Refactored code
    refactored_code = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)

    # Test cases
    test_cases = Column(Text, nullable=True)  # JSON string of test cases

    # Metadata
    status = Column(Enum(AdvisoryStatus), default=AdvisoryStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    policy = relationship("Policy", back_populates="advisories")
    tenant = relationship("Tenant", back_populates="advisories")
    opa_verifications = relationship("OPAVerification", back_populates="code_advisory")

    def __repr__(self) -> str:
        """String representation."""
        return f"<CodeAdvisory(id={self.id}, policy_id={self.policy_id}, status={self.status})>"
