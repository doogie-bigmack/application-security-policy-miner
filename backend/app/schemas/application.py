"""Pydantic schemas for application management."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.application import CriticalityLevel


# Base schemas
class ApplicationBase(BaseModel):
    """Base schema for application."""

    name: str = Field(..., description="Application name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Application description")
    criticality: CriticalityLevel = Field(
        default=CriticalityLevel.MEDIUM,
        description="Application criticality level"
    )
    tech_stack: str | None = Field(
        None,
        description="Technology stack (e.g., 'Java, Spring Boot, PostgreSQL')",
        max_length=255
    )
    owner: str | None = Field(
        None,
        description="Application owner name or email",
        max_length=255
    )


# Create schemas (for POST requests)
class ApplicationCreate(ApplicationBase):
    """Schema for creating an application."""

    business_unit_id: int = Field(..., description="Business unit ID")


class ApplicationUpdate(BaseModel):
    """Schema for updating an application."""

    name: str | None = Field(None, description="Application name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Application description")
    criticality: CriticalityLevel | None = Field(None, description="Application criticality level")
    tech_stack: str | None = Field(None, description="Technology stack", max_length=255)
    owner: str | None = Field(None, description="Application owner", max_length=255)
    business_unit_id: int | None = Field(None, description="Business unit ID")


# Response schemas (for API responses)
class ApplicationResponse(ApplicationBase):
    """Schema for application response."""

    id: int
    business_unit_id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# CSV Import schema
class ApplicationCSVRow(BaseModel):
    """Schema for CSV row when importing applications."""

    name: str = Field(..., description="Application name")
    business_unit_id: int = Field(..., description="Business unit ID")
    description: str | None = Field(None, description="Application description")
    criticality: str = Field(default="medium", description="Criticality (low, medium, high, critical)")
    tech_stack: str | None = Field(None, description="Technology stack")
    owner: str | None = Field(None, description="Application owner")


class ApplicationImportResult(BaseModel):
    """Schema for CSV import result."""

    total: int = Field(..., description="Total applications in CSV")
    success: int = Field(..., description="Successfully imported applications")
    failed: int = Field(..., description="Failed imports")
    errors: list[str] = Field(default_factory=list, description="Error messages")


class ApplicationWithPolicies(ApplicationResponse):
    """Schema for application with policy statistics."""

    policy_count: int = Field(default=0, description="Total number of policies")
    policy_count_by_source: dict[str, int] = Field(
        default_factory=dict,
        description="Policy count grouped by source type (frontend/backend/database)"
    )
    policy_count_by_risk: dict[str, int] = Field(
        default_factory=dict,
        description="Policy count grouped by risk level (low/medium/high)"
    )
