"""Migration wave models for managing phased rollout of application migrations."""
import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from .repository import Base


class MigrationWaveStatus(str, enum.Enum):
    """Status of a migration wave."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


# Association table for many-to-many relationship between waves and applications
wave_applications = Table(
    "wave_applications",
    Base.metadata,
    Column("wave_id", Integer, ForeignKey("migration_waves.id", ondelete="CASCADE"), primary_key=True),
    Column("application_id", Integer, ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True),
)


class MigrationWave(Base):
    """Migration wave model for managing phased rollout."""

    __tablename__ = "migration_waves"

    id = Column(Integer, primary_key=True, index=True)

    # Required fields
    name = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Optional fields
    description = Column(Text, nullable=True)
    status = Column(
        Enum(MigrationWaveStatus),
        default=MigrationWaveStatus.PLANNED,
        nullable=False,
        index=True
    )

    # Progress tracking
    total_applications = Column(Integer, default=0, nullable=False)
    scanned_applications = Column(Integer, default=0, nullable=False)
    provisioned_applications = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    applications = relationship(
        "Application",
        secondary=wave_applications,
        backref="migration_waves",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<MigrationWave {self.id}: {self.name} ({self.status})>"

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_applications == 0:
            return 0.0
        return (self.scanned_applications / self.total_applications) * 100

    @property
    def provisioned_percentage(self) -> float:
        """Calculate provisioned percentage."""
        if self.total_applications == 0:
            return 0.0
        return (self.provisioned_applications / self.total_applications) * 100
