"""Policy schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.policy import PolicyStatus, RiskLevel, SourceType, ValidationStatus


# Simple application schema to avoid circular imports
class SimpleApplication(BaseModel):
    """Simplified application schema for policy responses."""

    id: int
    name: str
    criticality: str
    business_unit_id: int

    model_config = ConfigDict(from_attributes=True)


class EvidenceBase(BaseModel):
    """Base evidence schema."""

    file_path: str = Field(..., description="Path to the source file")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    code_snippet: str = Field(..., description="Code snippet supporting the policy")


class EvidenceCreate(EvidenceBase):
    """Schema for creating evidence."""

    pass


class Evidence(EvidenceBase):
    """Evidence schema with ID and timestamps."""

    id: int
    policy_id: int
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_error: str | None = None
    validated_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyBase(BaseModel):
    """Base policy schema."""

    subject: str = Field(..., description="Who - the principal (e.g., Manager, Admin)")
    resource: str = Field(..., description="What - the resource being accessed")
    action: str = Field(..., description="How - the action being performed")
    conditions: str | None = Field(None, description="When - conditions for the policy")
    description: str | None = Field(None, description="Policy description")
    source_type: SourceType = Field(SourceType.UNKNOWN, description="Source type (frontend/backend/database)")


class PolicyCreate(PolicyBase):
    """Schema for creating a policy."""

    repository_id: int
    application_id: int | None = None
    risk_score: float | None = None
    risk_level: RiskLevel | None = None
    complexity_score: float | None = None
    impact_score: float | None = None
    confidence_score: float | None = None
    historical_score: float | None = None
    evidence: list[EvidenceCreate] = Field(default_factory=list)


class Policy(PolicyBase):
    """Policy schema with full details."""

    id: int
    repository_id: int
    application_id: int | None = None
    status: PolicyStatus
    risk_score: float | None = None
    risk_level: RiskLevel | None = None
    complexity_score: float | None = None
    impact_score: float | None = None
    confidence_score: float | None = None
    historical_score: float | None = None
    approval_comment: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    tenant_id: str | None = None
    application: SimpleApplication | None = None

    model_config = ConfigDict(from_attributes=True)


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""

    subject: str | None = None
    resource: str | None = None
    action: str | None = None
    conditions: str | None = None
    description: str | None = None
    source_type: SourceType | None = None
    application_id: int | None = None
    risk_score: float | None = None
    risk_level: RiskLevel | None = None
    complexity_score: float | None = None
    impact_score: float | None = None
    confidence_score: float | None = None
    historical_score: float | None = None


class PolicyList(BaseModel):
    """Schema for listing policies."""

    policies: list[Policy]
    total: int
