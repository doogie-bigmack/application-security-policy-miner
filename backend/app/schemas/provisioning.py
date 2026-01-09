"""Provisioning schemas for PBAC platform integration."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.provisioning import ProviderType, ProvisioningStatus

# PBAC Provider Schemas


class PBACProviderBase(BaseModel):
    """Base schema for PBAC provider."""

    provider_type: ProviderType
    name: str = Field(..., description="User-friendly name for the provider")
    endpoint_url: str = Field(..., description="Provider endpoint URL or region")
    api_key: str | None = Field(None, description="API key for authentication")
    configuration: str | None = Field(None, description="JSON configuration")


class PBACProviderCreate(PBACProviderBase):
    """Schema for creating a PBAC provider."""

    pass


class PBACProviderUpdate(BaseModel):
    """Schema for updating a PBAC provider."""

    name: str | None = None
    endpoint_url: str | None = None
    api_key: str | None = None
    configuration: str | None = None


class PBACProvider(PBACProviderBase):
    """Schema for PBAC provider response."""

    provider_id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Provisioning Operation Schemas


class ProvisioningOperationBase(BaseModel):
    """Base schema for provisioning operation."""

    provider_id: int
    policy_id: int


class ProvisioningOperationCreate(ProvisioningOperationBase):
    """Schema for creating a provisioning operation."""

    pass


class BulkProvisioningRequest(BaseModel):
    """Schema for bulk provisioning request."""

    provider_id: int
    policy_ids: list[int] = Field(..., description="List of policy IDs to provision")


class ProvisioningOperation(ProvisioningOperationBase):
    """Schema for provisioning operation response."""

    operation_id: int
    tenant_id: str
    status: ProvisioningStatus
    translated_policy: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
