"""Migration wave schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.migration_wave import MigrationWaveStatus


class MigrationWaveBase(BaseModel):
    """Base migration wave schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class MigrationWaveCreate(MigrationWaveBase):
    """Schema for creating a migration wave."""

    application_ids: list[int] = Field(default_factory=list, description="List of application IDs to include in wave")


class MigrationWaveUpdate(BaseModel):
    """Schema for updating a migration wave."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: MigrationWaveStatus | None = None


class MigrationWaveApplicationAdd(BaseModel):
    """Schema for adding applications to a wave."""

    application_ids: list[int] = Field(..., min_items=1, description="List of application IDs to add to wave")


class MigrationWaveApplicationRemove(BaseModel):
    """Schema for removing applications from a wave."""

    application_ids: list[int] = Field(..., min_items=1, description="List of application IDs to remove from wave")


class MigrationWaveProgressUpdate(BaseModel):
    """Schema for updating wave progress."""

    scanned_applications: int | None = Field(None, ge=0)
    provisioned_applications: int | None = Field(None, ge=0)


class MigrationWaveResponse(MigrationWaveBase):
    """Schema for migration wave response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    status: MigrationWaveStatus
    total_applications: int
    scanned_applications: int
    provisioned_applications: int
    progress_percentage: float
    provisioned_percentage: float
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class MigrationWaveWithApplications(MigrationWaveResponse):
    """Schema for migration wave with applications."""

    application_ids: list[int] = Field(default_factory=list, description="List of application IDs in this wave")


class MigrationWaveReport(BaseModel):
    """Schema for migration wave completion report."""

    wave_id: int
    wave_name: str
    status: MigrationWaveStatus
    total_applications: int
    scanned_applications: int
    provisioned_applications: int
    progress_percentage: float
    provisioned_percentage: float
    started_at: datetime | None
    completed_at: datetime | None
    duration_minutes: float | None
    policies_extracted: int
    policies_provisioned: int
    high_risk_policies: int
    conflicts_detected: int
