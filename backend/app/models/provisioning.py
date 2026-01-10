"""Provisioning models for PBAC platform integration."""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.repository import Base


class ProviderType(str, enum.Enum):
    """PBAC provider types."""

    OPA = "opa"
    AWS_VERIFIED_PERMISSIONS = "aws_verified_permissions"
    AXIOMATICS = "axiomatics"
    PLAINID = "plainid"


class ProvisioningStatus(str, enum.Enum):
    """Provisioning operation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class PBACProvider(Base):
    """PBAC provider configuration."""

    __tablename__ = "pbac_providers"

    provider_id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    provider_type = Column(Enum(ProviderType), nullable=False)
    name = Column(String, nullable=False)  # User-friendly name
    endpoint_url = Column(String, nullable=False)  # OPA endpoint, AWS region, etc.
    api_key = Column(String, nullable=True)  # For platforms requiring API key
    configuration = Column(Text, nullable=True)  # JSON configuration specific to provider
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="pbac_providers")
    provisioning_operations = relationship("ProvisioningOperation", back_populates="provider")


class ProvisioningOperation(Base):
    """Provisioning operation tracking."""

    __tablename__ = "provisioning_operations"

    operation_id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("pbac_providers.provider_id"), nullable=False)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    status = Column(Enum(ProvisioningStatus), nullable=False, default=ProvisioningStatus.PENDING)
    translated_policy = Column(Text, nullable=True)  # Rego, Cedar, etc.
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    provider = relationship("PBACProvider", back_populates="provisioning_operations")
    policy = relationship("Policy")
