"""Tests for audit logging service."""

import pytest
from sqlalchemy.orm import Session

from app.models.audit_log import AuditEventType, AuditLog
from app.services.audit_service import AuditService


def test_log_ai_prompt(db: Session):
    """Test logging an AI prompt."""
    audit_log = AuditService.log_ai_prompt(
        db=db,
        tenant_id="test_tenant",
        prompt="Test prompt for policy extraction",
        model="claude-sonnet-4",
        provider="aws_bedrock",
        repository_id=1,
        additional_context={"file_path": "/test/file.py"},
    )

    assert audit_log.id is not None
    assert audit_log.tenant_id == "test_tenant"
    assert audit_log.event_type == AuditEventType.AI_PROMPT
    assert audit_log.ai_prompt == "Test prompt for policy extraction"
    assert audit_log.ai_model == "claude-sonnet-4"
    assert audit_log.ai_provider == "aws_bedrock"
    assert audit_log.repository_id == 1
    assert audit_log.additional_data["file_path"] == "/test/file.py"


def test_log_ai_response(db: Session):
    """Test logging an AI response."""
    audit_log = AuditService.log_ai_response(
        db=db,
        tenant_id="test_tenant",
        response="Test AI response with extracted policies",
        model="claude-sonnet-4",
        provider="aws_bedrock",
        repository_id=1,
        response_time_ms=1500,
        additional_context={"policies_extracted": 3},
    )

    assert audit_log.id is not None
    assert audit_log.event_type == AuditEventType.AI_RESPONSE
    assert audit_log.ai_response == "Test AI response with extracted policies"
    assert audit_log.response_metadata["response_time_ms"] == 1500
    assert audit_log.additional_data["policies_extracted"] == 3


def test_log_policy_approval(db: Session):
    """Test logging a policy approval."""
    audit_log = AuditService.log_policy_approval(
        db=db,
        tenant_id="test_tenant",
        policy_id=1,
        user_email="admin@test.com",
        additional_notes="Looks good, approved",
    )

    assert audit_log.id is not None
    assert audit_log.event_type == AuditEventType.POLICY_APPROVAL
    assert audit_log.policy_id == 1
    assert audit_log.user_email == "admin@test.com"
    assert audit_log.additional_data["notes"] == "Looks good, approved"


def test_log_policy_rejection(db: Session):
    """Test logging a policy rejection."""
    audit_log = AuditService.log_policy_rejection(
        db=db,
        tenant_id="test_tenant",
        policy_id=2,
        user_email="admin@test.com",
        reason="Incomplete authorization logic",
    )

    assert audit_log.id is not None
    assert audit_log.event_type == AuditEventType.POLICY_REJECTION
    assert audit_log.policy_id == 2
    assert audit_log.user_email == "admin@test.com"
    assert audit_log.additional_data["reason"] == "Incomplete authorization logic"


def test_log_provisioning_success(db: Session):
    """Test logging a successful provisioning."""
    audit_log = AuditService.log_provisioning(
        db=db,
        tenant_id="test_tenant",
        policy_id=1,
        target_platform="OPA",
        user_email="admin@test.com",
        success=True,
    )

    assert audit_log.id is not None
    assert audit_log.event_type == AuditEventType.PROVISIONING
    assert audit_log.policy_id == 1
    assert audit_log.additional_data["target_platform"] == "OPA"
    assert audit_log.additional_data["success"] is True


def test_log_provisioning_failure(db: Session):
    """Test logging a failed provisioning."""
    audit_log = AuditService.log_provisioning(
        db=db,
        tenant_id="test_tenant",
        policy_id=1,
        target_platform="OPA",
        user_email="admin@test.com",
        success=False,
        error_message="Connection timeout",
    )

    assert audit_log.id is not None
    assert audit_log.event_type == AuditEventType.PROVISIONING
    assert audit_log.additional_data["success"] is False
    assert audit_log.additional_data["error_message"] == "Connection timeout"


def test_audit_log_tenant_isolation(db: Session):
    """Test that audit logs are tenant-isolated."""
    # Create logs for tenant A
    AuditService.log_ai_prompt(
        db=db,
        tenant_id="tenant_a",
        prompt="Tenant A prompt",
        model="claude-sonnet-4",
        provider="aws_bedrock",
    )

    # Create logs for tenant B
    AuditService.log_ai_prompt(
        db=db,
        tenant_id="tenant_b",
        prompt="Tenant B prompt",
        model="claude-sonnet-4",
        provider="aws_bedrock",
    )

    # Query logs for tenant A
    tenant_a_logs = db.query(AuditLog).filter(AuditLog.tenant_id == "tenant_a").all()
    assert len(tenant_a_logs) == 1
    assert tenant_a_logs[0].ai_prompt == "Tenant A prompt"

    # Query logs for tenant B
    tenant_b_logs = db.query(AuditLog).filter(AuditLog.tenant_id == "tenant_b").all()
    assert len(tenant_b_logs) == 1
    assert tenant_b_logs[0].ai_prompt == "Tenant B prompt"
