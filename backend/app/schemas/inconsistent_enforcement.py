"""Schemas for inconsistent enforcement."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.inconsistent_enforcement import (
    InconsistentEnforcementSeverity,
    InconsistentEnforcementStatus,
)


class RecommendedPolicy(BaseModel):
    """Recommended standardized policy."""

    subject: str = Field(..., description="Recommended subject (role/permission)")
    resource: str = Field(..., description="Resource type being protected")
    action: str = Field(..., description="Recommended action")
    conditions: str | None = Field(None, description="Recommended conditions")


class InconsistentEnforcementBase(BaseModel):
    """Base schema for inconsistent enforcement."""

    resource_type: str = Field(..., description="Resource type with inconsistent protection")
    resource_description: str | None = Field(None, description="Description of the resource")
    affected_application_ids: list[int] = Field(..., description="Application IDs affected")
    policy_ids: list[int] = Field(..., description="Policy IDs involved")
    inconsistency_description: str = Field(..., description="Description of the inconsistency")
    severity: InconsistentEnforcementSeverity = Field(..., description="Severity level")
    recommended_policy: dict = Field(..., description="AI-recommended standardized policy")
    recommendation_explanation: str = Field(..., description="Explanation of recommendation")


class InconsistentEnforcementCreate(InconsistentEnforcementBase):
    """Schema for creating inconsistent enforcement record."""

    pass


class InconsistentEnforcementResponse(InconsistentEnforcementBase):
    """Schema for inconsistent enforcement response."""

    id: int
    tenant_id: str
    status: InconsistentEnforcementStatus
    resolution_notes: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InconsistentEnforcementStatusUpdate(BaseModel):
    """Schema for updating inconsistency status."""

    status: InconsistentEnforcementStatus = Field(..., description="New status")
    resolution_notes: str | None = Field(None, description="Resolution notes")
    resolved_by: str | None = Field(None, description="Email of user resolving")


class DetectInconsistenciesResponse(BaseModel):
    """Response from inconsistency detection."""

    inconsistencies_found: int = Field(..., description="Number of inconsistencies detected")
    inconsistencies: list[InconsistentEnforcementResponse] = Field(..., description="List of inconsistencies")
