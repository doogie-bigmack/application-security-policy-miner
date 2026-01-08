"""Policy schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.policy import PolicyStatus, RiskLevel


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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyBase(BaseModel):
    """Base policy schema."""

    subject: str = Field(..., description="Who - the principal (e.g., Manager, Admin)")
    resource: str = Field(..., description="What - the resource being accessed")
    action: str = Field(..., description="How - the action being performed")
    conditions: str | None = Field(None, description="When - conditions for the policy")
    description: str | None = Field(None, description="Policy description")


class PolicyCreate(PolicyBase):
    """Schema for creating a policy."""

    repository_id: int
    risk_score: float | None = None
    risk_level: RiskLevel | None = None
    complexity_score: float | None = None
    impact_score: float | None = None
    confidence_score: float | None = None
    evidence: list[EvidenceCreate] = Field(default_factory=list)


class Policy(PolicyBase):
    """Policy schema with full details."""

    id: int
    repository_id: int
    status: PolicyStatus
    risk_score: float | None = None
    risk_level: RiskLevel | None = None
    complexity_score: float | None = None
    impact_score: float | None = None
    confidence_score: float | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    tenant_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PolicyList(BaseModel):
    """Schema for listing policies."""

    policies: list[Policy]
    total: int
