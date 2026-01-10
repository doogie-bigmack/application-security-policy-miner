"""Auto-approval schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class AutoApprovalSettingsBase(BaseModel):
    """Base schema for auto-approval settings."""

    enabled: bool = Field(default=False, description="Enable auto-approval")
    risk_threshold: float = Field(default=30.0, ge=0, le=100, description="Maximum risk score for auto-approval")
    min_historical_approvals: int = Field(default=3, ge=1, description="Minimum similar approvals needed")


class AutoApprovalSettingsCreate(AutoApprovalSettingsBase):
    """Schema for creating auto-approval settings."""

    pass


class AutoApprovalSettingsUpdate(BaseModel):
    """Schema for updating auto-approval settings."""

    enabled: bool | None = None
    risk_threshold: float | None = Field(default=None, ge=0, le=100)
    min_historical_approvals: int | None = Field(default=None, ge=1)


class AutoApprovalSettings(AutoApprovalSettingsBase):
    """Schema for auto-approval settings response."""

    id: int
    tenant_id: str
    total_auto_approvals: int
    total_policies_scanned: int
    auto_approval_rate: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutoApprovalDecisionBase(BaseModel):
    """Base schema for auto-approval decision."""

    auto_approved: bool
    reasoning: str
    risk_score: float
    similar_policies_count: int
    matched_patterns: str | None = None


class AutoApprovalDecision(AutoApprovalDecisionBase):
    """Schema for auto-approval decision response."""

    id: int
    tenant_id: str
    policy_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AutoApprovalMetrics(BaseModel):
    """Schema for auto-approval metrics."""

    total_auto_approvals: int
    total_policies_scanned: int
    auto_approval_rate: float
    enabled: bool
    risk_threshold: float
    min_historical_approvals: int
