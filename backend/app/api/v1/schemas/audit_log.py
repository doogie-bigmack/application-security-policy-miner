"""Schemas for audit log API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.audit_log import AuditEventType


class AuditLogBase(BaseModel):
    """Base audit log schema."""

    event_type: AuditEventType
    event_description: str
    user_email: str | None = None
    repository_id: int | None = None
    policy_id: int | None = None
    conflict_id: int | None = None
    ai_model: str | None = None
    ai_provider: str | None = None


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit log entries (internal use)."""

    tenant_id: int
    ai_prompt: str | None = None
    ai_response: str | None = None
    request_metadata: dict[str, Any] | None = None
    response_metadata: dict[str, Any] | None = None
    additional_data: dict[str, Any] | None = None


class AuditLog(AuditLogBase):
    """Schema for audit log response."""

    id: int
    tenant_id: int
    ai_prompt: str | None = None
    ai_response: str | None = None
    request_metadata: dict[str, Any] | None = None
    response_metadata: dict[str, Any] | None = None
    additional_data: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogList(BaseModel):
    """Schema for list of audit logs."""

    total: int
    items: list[AuditLog]


class AuditLogFilters(BaseModel):
    """Schema for audit log filters."""

    event_type: AuditEventType | None = None
    user_email: str | None = None
    repository_id: int | None = None
    policy_id: int | None = None
    conflict_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    skip: int = 0
    limit: int = 100
