"""Bulk scan model for parallel application scanning."""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from .repository import Base


class BulkScanStatus(str, enum.Enum):
    """Bulk scan status enum."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkScan(Base):
    """Model for bulk scan batch operations."""

    __tablename__ = "bulk_scans"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), index=True, nullable=True)

    # Scan configuration
    total_applications = Column(Integer, nullable=False)
    completed_applications = Column(Integer, default=0)
    failed_applications = Column(Integer, default=0)

    # Status tracking
    status = Column(String(50), default=BulkScanStatus.QUEUED, nullable=False)
    error_message = Column(Text, nullable=True)

    # Application/repository IDs being scanned
    target_ids = Column(JSONB, nullable=False)  # list of repository IDs

    # Results aggregation
    total_policies_extracted = Column(Integer, default=0)
    total_files_scanned = Column(Integer, default=0)

    # Performance metrics
    max_parallel_workers = Column(Integer, default=10)  # Configurable concurrency
    average_scan_duration_seconds = Column(Integer, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_bulk_scans_tenant_status", "tenant_id", "status"),
        Index("idx_bulk_scans_created_at", "created_at"),
    )
