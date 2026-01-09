"""Pydantic schemas for role mapping."""
from datetime import datetime

from pydantic import BaseModel, Field


class RoleMappingBase(BaseModel):
    """Base role mapping schema."""

    standard_role: str = Field(..., description="Standard normalized role name")
    variant_roles: list[str] = Field(..., description="List of role variants")
    affected_applications: list[int] = Field(..., description="Application IDs affected")
    confidence_score: int = Field(..., ge=0, le=100, description="AI confidence score")
    reasoning: str | None = Field(None, description="AI reasoning for equivalence")


class RoleMappingCreate(RoleMappingBase):
    """Schema for creating a role mapping."""

    pass


class RoleMappingResponse(RoleMappingBase):
    """Schema for role mapping response."""

    id: int
    tenant_id: str
    affected_policy_count: int
    status: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class RoleMappingApproval(BaseModel):
    """Schema for approving a role mapping."""

    approved_by: str = Field(..., description="Email of approver")


class RoleDiscoveryRequest(BaseModel):
    """Schema for role discovery request."""

    min_applications: int = Field(2, ge=2, description="Minimum applications with role variants")


class RoleDiscoveryResponse(BaseModel):
    """Schema for role discovery response."""

    roles: list[str] = Field(..., description="Discovered role variants")
    standard_role: str = Field(..., description="Recommended standard role name")
    confidence: int = Field(..., ge=0, le=100, description="AI confidence score")
    reasoning: str = Field(..., description="AI reasoning")
    application_count: int = Field(..., description="Number of applications affected")
    applications: list[str] = Field(..., description="List of application names")
    apps_by_role: dict[str, list[str]] = Field(..., description="Applications grouped by role")


class RoleMappingStats(BaseModel):
    """Statistics for role mappings."""

    total_mappings: int
    suggested: int
    approved: int
    applied: int
    total_policies_normalized: int
