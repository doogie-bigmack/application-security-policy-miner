"""Repository schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.repository import GitProvider, RepositoryStatus, RepositoryType


class RepositoryBase(BaseModel):
    """Base repository schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    repository_type: RepositoryType
    git_provider: GitProvider | None = None
    source_url: str | None = Field(None, max_length=500)
    connection_config: dict | None = None
    tenant_id: str | None = None


class RepositoryCreate(RepositoryBase):
    """Schema for creating a repository."""

    pass


class RepositoryUpdate(BaseModel):
    """Schema for updating a repository."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    source_url: str | None = Field(None, max_length=500)
    connection_config: dict | None = None
    status: RepositoryStatus | None = None
    webhook_enabled: bool | None = None


class RepositoryResponse(RepositoryBase):
    """Schema for repository responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: RepositoryStatus
    git_provider: GitProvider | None = None
    last_scan_at: datetime | None = None
    webhook_secret: str | None = None
    webhook_enabled: bool = False
    created_at: datetime
    updated_at: datetime


class RepositoryListResponse(BaseModel):
    """Schema for repository list responses."""

    repositories: list[RepositoryResponse]
    total: int
