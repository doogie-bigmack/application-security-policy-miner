"""Pydantic schemas for organization management."""
from datetime import datetime

from pydantic import BaseModel, Field


# Base schemas
class OrganizationBase(BaseModel):
    """Base schema for organization."""

    name: str = Field(..., description="Organization name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Organization description")


class DivisionBase(BaseModel):
    """Base schema for division."""

    name: str = Field(..., description="Division name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Division description")


class BusinessUnitBase(BaseModel):
    """Base schema for business unit."""

    name: str = Field(..., description="Business unit name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Business unit description")


# Create schemas (for POST requests)
class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""

    pass


class DivisionCreate(DivisionBase):
    """Schema for creating a division."""

    pass


class BusinessUnitCreate(BusinessUnitBase):
    """Schema for creating a business unit."""

    pass


# Response schemas (for API responses)
class BusinessUnitResponse(BusinessUnitBase):
    """Schema for business unit response."""

    id: int
    division_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DivisionResponse(DivisionBase):
    """Schema for division response."""

    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DivisionWithBusinessUnits(DivisionResponse):
    """Schema for division with business units."""

    business_units: list[BusinessUnitResponse] = []

    model_config = {"from_attributes": True}


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationWithHierarchy(OrganizationResponse):
    """Schema for organization with full hierarchy."""

    divisions: list[DivisionWithBusinessUnits] = []

    model_config = {"from_attributes": True}
