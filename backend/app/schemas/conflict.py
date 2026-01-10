"""Policy conflict schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.conflict import ConflictStatus, ConflictType
from app.schemas.policy import Policy


class ConflictBase(BaseModel):
    """Base conflict schema."""

    conflict_type: ConflictType = Field(..., description="Type of conflict")
    description: str = Field(..., description="Description of the conflict")
    severity: str = Field(..., description="Severity: low, medium, high")


class ConflictCreate(ConflictBase):
    """Schema for creating a conflict."""

    policy_a_id: int
    policy_b_id: int
    ai_recommendation: str | None = None


class Conflict(ConflictBase):
    """Conflict schema with full details."""

    id: int
    policy_a_id: int
    policy_b_id: int
    policy_a: Policy
    policy_b: Policy
    ai_recommendation: str | None = None
    status: ConflictStatus
    resolution_strategy: str | None = None
    resolution_notes: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    tenant_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConflictResolve(BaseModel):
    """Schema for resolving a conflict."""

    resolution_strategy: str = Field(..., description="Resolution strategy: keep_a, keep_b, merge, custom")
    resolution_notes: str | None = Field(None, description="Notes about the resolution")


class ConflictList(BaseModel):
    """Schema for listing conflicts."""

    conflicts: list[Conflict]
    total: int
