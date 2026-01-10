"""Pydantic schemas for policy fixes."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.policy_fix import FixSeverity, FixStatus


class PolicyFixBase(BaseModel):
    """Base schema for policy fix."""

    security_gap_type: str = Field(..., description="Type of security gap")
    severity: FixSeverity = Field(..., description="Severity of the gap")
    gap_description: str = Field(..., description="Description of security gaps")


class PolicyFixCreate(PolicyFixBase):
    """Schema for creating a policy fix."""

    policy_id: int = Field(..., description="ID of the policy being fixed")


class PolicyFixResponse(PolicyFixBase):
    """Schema for policy fix response."""

    id: int
    policy_id: int
    tenant_id: str
    missing_checks: str | None = Field(None, description="JSON array of missing checks")
    original_policy: str = Field(..., description="JSON of original policy")
    fixed_policy: str = Field(..., description="JSON of fixed policy")
    fix_explanation: str = Field(..., description="Explanation of the fix")
    test_cases: str | None = Field(None, description="JSON array of test cases")
    status: FixStatus
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class AnalyzePolicyRequest(BaseModel):
    """Request to analyze a policy."""

    policy_id: int = Field(..., description="ID of policy to analyze")


class UpdateFixStatusRequest(BaseModel):
    """Request to update fix status."""

    status: FixStatus = Field(..., description="New status")
    reviewed_by: str | None = Field(None, description="Email of reviewer")
    review_comment: str | None = Field(None, description="Review comment")


class GenerateTestCasesRequest(BaseModel):
    """Request to generate test cases."""

    fix_id: int = Field(..., description="ID of fix to generate test cases for")
