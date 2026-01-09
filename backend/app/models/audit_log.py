"""Audit Log model for tracking all AI operations and user decisions."""

import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB

from app.models.repository import Base


class AuditEventType(str, enum.Enum):
    """Types of auditable events."""
    AI_PROMPT = "ai_prompt"
    AI_RESPONSE = "ai_response"
    POLICY_APPROVAL = "policy_approval"
    POLICY_REJECTION = "policy_rejection"
    POLICY_UPDATE = "policy_update"
    POLICY_DELETE = "policy_delete"
    PROVISIONING = "provisioning"
    CONFLICT_DETECTION = "conflict_detection"
    CONFLICT_RESOLUTION = "conflict_resolution"
    SCAN_START = "scan_start"
    SCAN_COMPLETE = "scan_complete"
    USER_LOGIN = "user_login"
    REPOSITORY_CREATE = "repository_create"
    REPOSITORY_UPDATE = "repository_update"
    REPOSITORY_DELETE = "repository_delete"


class AuditLog(Base):
    """Model for audit log entries."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    user_email = Column(String, nullable=True, index=True)  # User who triggered the event
    event_type = Column(SQLEnum(AuditEventType), nullable=False, index=True)
    event_description = Column(String, nullable=False)

    # Related entity IDs
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True, index=True)
    conflict_id = Column(Integer, ForeignKey("policy_conflicts.id"), nullable=True, index=True)

    # AI-specific fields
    ai_prompt = Column(Text, nullable=True)  # Full prompt sent to LLM
    ai_response = Column(Text, nullable=True)  # Full response from LLM
    ai_model = Column(String, nullable=True)  # Model used (e.g., "claude-sonnet-4")
    ai_provider = Column(String, nullable=True)  # Provider used (aws_bedrock, azure_openai)

    # Request/response metadata
    request_metadata = Column(JSONB, nullable=True)  # Request details (IP, user agent, etc.)
    response_metadata = Column(JSONB, nullable=True)  # Response details (status, duration, etc.)

    # Additional data
    additional_data = Column(JSONB, nullable=True)  # Any other relevant data

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index('ix_audit_logs_tenant_event_type', 'tenant_id', 'event_type'),
        Index('ix_audit_logs_tenant_created_at', 'tenant_id', 'created_at'),
        Index('ix_audit_logs_user_created_at', 'user_email', 'created_at'),
    )
