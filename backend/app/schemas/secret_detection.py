"""Schemas for secret detection logs."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SecretDetectionLogBase(BaseModel):
    """Base schema for secret detection log."""

    repository_id: int
    file_path: str
    secret_type: str
    description: str
    line_number: int
    preview: str


class SecretDetectionLogResponse(SecretDetectionLogBase):
    """Schema for secret detection log response."""

    id: int
    tenant_id: str | None
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)
