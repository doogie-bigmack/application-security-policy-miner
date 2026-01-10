"""Scan progress schemas."""
from datetime import datetime

from pydantic import BaseModel

from app.models.scan_progress import ScanStatus


class ScanProgressBase(BaseModel):
    """Base scan progress schema."""

    repository_id: int
    status: ScanStatus
    total_files: int = 0
    processed_files: int = 0
    current_batch: int = 0
    total_batches: int = 0
    policies_extracted: int = 0
    errors_count: int = 0


class ScanProgress(ScanProgressBase):
    """Scan progress response schema."""

    id: int
    tenant_id: str | None
    error_message: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
