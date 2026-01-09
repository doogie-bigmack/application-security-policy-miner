"""Schemas for PolicyChange and WorkItem."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.policy_change import ChangeType, WorkItemPriority, WorkItemStatus


class PolicyChangeBase(BaseModel):
    """Base schema for PolicyChange."""

    repository_id: int
    change_type: ChangeType
    before_subject: str | None = None
    before_resource: str | None = None
    before_action: str | None = None
    before_conditions: str | None = None
    after_subject: str | None = None
    after_resource: str | None = None
    after_action: str | None = None
    after_conditions: str | None = None
    description: str | None = None
    diff_summary: str | None = None


class PolicyChangeCreate(PolicyChangeBase):
    """Schema for creating a PolicyChange."""

    policy_id: int | None = None
    previous_policy_id: int | None = None
    tenant_id: str | None = None


class PolicyChange(PolicyChangeBase):
    """Schema for PolicyChange response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int | None
    previous_policy_id: int | None
    detected_at: datetime
    tenant_id: str | None


class WorkItemBase(BaseModel):
    """Base schema for WorkItem."""

    title: str
    description: str | None = None
    status: WorkItemStatus = WorkItemStatus.OPEN
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    assigned_to: str | None = None


class WorkItemCreate(WorkItemBase):
    """Schema for creating a WorkItem."""

    policy_change_id: int
    repository_id: int
    tenant_id: str | None = None


class WorkItemUpdate(BaseModel):
    """Schema for updating a WorkItem."""

    status: WorkItemStatus | None = None
    priority: WorkItemPriority | None = None
    assigned_to: str | None = None
    description: str | None = None


class WorkItem(WorkItemBase):
    """Schema for WorkItem response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_change_id: int
    repository_id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    tenant_id: str | None
