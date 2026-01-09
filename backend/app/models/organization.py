"""Organization models for hierarchical structure support."""
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .repository import Base


class Organization(Base):
    """Organization model for top-level organizational entity."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    divisions = relationship(
        "Division", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Organization {self.id}: {self.name}>"


class Division(Base):
    """Division model for mid-level organizational grouping."""

    __tablename__ = "divisions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    organization = relationship("Organization", back_populates="divisions")
    business_units = relationship(
        "BusinessUnit", back_populates="division", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Division {self.id}: {self.name}>"


class BusinessUnit(Base):
    """Business unit model for lowest-level organizational grouping."""

    __tablename__ = "business_units"

    id = Column(Integer, primary_key=True, index=True)
    division_id = Column(
        Integer, ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    division = relationship("Division", back_populates="business_units")

    def __repr__(self) -> str:
        """String representation."""
        return f"<BusinessUnit {self.id}: {self.name}>"
