"""Policy schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.policy import PolicyStatus, RiskLevel, SourceType


class PolicyEvidenceBase(BaseModel):
    """Base schema for policy evidence."""

    file_path: str = Field(..., max_length=1000)
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    code_snippet: str


class PolicyEvidenceResponse(PolicyEvidenceBase):
    """Schema for policy evidence responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    created_at: datetime


class PolicyBase(BaseModel):
    """Base schema for policies."""

    subject: str = Field(..., max_length=500, description="Who: user, role, group")
    resource: str = Field(..., max_length=500, description="What: resource being accessed")
    action: str = Field(..., max_length=500, description="How: action being performed")
    conditions: str | None = Field(None, description="When: conditions, constraints")
    description: str | None = None


class PolicyCreate(PolicyBase):
    """Schema for creating a policy."""

    repository_id: int
    tenant_id: str | None = None


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""

    subject: str | None = Field(None, max_length=500)
    resource: str | None = Field(None, max_length=500)
    action: str | None = Field(None, max_length=500)
    conditions: str | None = None
    description: str | None = None
    status: PolicyStatus | None = None
    risk_level: RiskLevel | None = None
    risk_score: int | None = Field(None, ge=0, le=100)


class PolicyResponse(PolicyBase):
    """Schema for policy responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    status: PolicyStatus
    risk_level: RiskLevel
    risk_score: int
    source_type: SourceType
    created_at: datetime
    updated_at: datetime
    tenant_id: str | None = None
    evidence: list[PolicyEvidenceResponse] = []


class PolicyListResponse(BaseModel):
    """Schema for policy list responses."""

    policies: list[PolicyResponse]
    total: int


class ScanRequest(BaseModel):
    """Schema for scan request."""

    repository_id: int


class ScanResponse(BaseModel):
    """Schema for scan response."""

    message: str
    repository_id: int
    policies_extracted: int
