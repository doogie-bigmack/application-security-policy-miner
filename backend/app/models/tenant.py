"""Tenant model for multi-tenancy support."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .repository import Base


class Tenant(Base):
    """Tenant model for multi-tenancy."""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Tenant {self.tenant_id}: {self.name}>"
