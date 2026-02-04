"""Bulk scan schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class BulkScanRequest(BaseModel):
    """Request schema for bulk scanning."""

    repository_ids: list[int] = Field(
        ..., description="List of repository IDs to scan", min_length=1, max_length=1000
    )
    incremental: bool = Field(
        default=False, description="Whether to perform incremental scans"
    )
    max_parallel_workers: int = Field(
        default=10, description="Maximum number of parallel workers", ge=1, le=100
    )


class BulkScanJobInfo(BaseModel):
    """Information about a single scan job in the bulk operation."""

    repository_id: int
    repository_name: str
    job_id: str  # RQ job ID
    status: str  # queued, started, finished, failed


class BulkScanResponse(BaseModel):
    """Response schema for bulk scan initiation."""

    bulk_scan_id: int
    total_applications: int
    initiated_scans: int
    failed_initiations: int
    max_parallel_workers: int
    jobs: list[BulkScanJobInfo]


class BulkScanProgress(BaseModel):
    """Progress schema for bulk scan."""

    bulk_scan_id: int
    status: str
    total_applications: int
    completed_applications: int
    failed_applications: int
    total_policies_extracted: int
    total_files_scanned: int
    average_scan_duration_seconds: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
