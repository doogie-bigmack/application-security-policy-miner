"""Scan progress tracking model."""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .repository import Base


class ScanStatus(str, enum.Enum):
    """Scan status enum."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanProgress(Base):
    """Scan progress tracking."""

    __tablename__ = "scan_progress"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    tenant_id = Column(String, index=True, nullable=True)

    # Progress tracking
    status = Column(Enum(ScanStatus), default=ScanStatus.QUEUED, nullable=False)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    current_batch = Column(Integer, default=0)
    total_batches = Column(Integer, default=0)

    # Results
    policies_extracted = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="scan_progresses")
