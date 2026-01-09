"""Application models for managing enterprise applications."""
import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .repository import Base


class CriticalityLevel(str, enum.Enum):
    """Criticality levels for applications."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Application(Base):
    """Application model for managing enterprise applications."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)

    # Required fields
    name = Column(String(255), nullable=False, index=True)
    business_unit_id = Column(
        Integer, ForeignKey("business_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(String(255), nullable=False, index=True)

    # Optional fields
    description = Column(Text, nullable=True)
    criticality = Column(
        Enum(CriticalityLevel),
        default=CriticalityLevel.MEDIUM,
        nullable=False,
        index=True
    )
    tech_stack = Column(String(255), nullable=True)  # e.g., "Java, Spring Boot, PostgreSQL"
    owner = Column(String(255), nullable=True)  # Application owner name or email

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    business_unit = relationship("BusinessUnit")
    policies = relationship("Policy", back_populates="application", foreign_keys="[Policy.application_id]")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Application {self.id}: {self.name}>"
