"""Schemas for code advisories."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.code_advisory import AdvisoryStatus


class CodeAdvisoryBase(BaseModel):
    """Base schema for code advisory."""

    policy_id: int
    file_path: str
    original_code: str
    line_start: int
    line_end: int
    refactored_code: str
    explanation: str


class CodeAdvisoryCreate(CodeAdvisoryBase):
    """Schema for creating a code advisory."""

    pass


class CodeAdvisory(CodeAdvisoryBase):
    """Schema for code advisory response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    test_cases: str | None = None  # JSON string of test cases
    status: AdvisoryStatus
    created_at: datetime
    reviewed_at: datetime | None


class CodeAdvisoryUpdate(BaseModel):
    """Schema for updating a code advisory."""

    status: AdvisoryStatus | None = None


class GenerateAdvisoryRequest(BaseModel):
    """Request to generate code advisory for a policy."""

    policy_id: int
    target_platform: str = "OPA"  # OPA, AWS, Axiomatics, PlainID
