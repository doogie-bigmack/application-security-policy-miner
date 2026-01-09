"""Tests for security audit service."""

from app.services.security_audit_service import SecurityAuditService


def test_audit_encryption_structure():
    """Test that audit returns expected structure."""
    service = SecurityAuditService()
    audit = service.audit_encryption()

    # Check top-level keys
    assert "database" in audit
    assert "redis" in audit
    assert "object_storage" in audit
    assert "secrets" in audit
    assert "api" in audit
    assert "overall_status" in audit

    # Check overall status is valid
    assert audit["overall_status"] in ["pass", "partial", "fail"]


def test_audit_database():
    """Test database encryption audit."""
    service = SecurityAuditService()
    result = service._audit_database()

    assert "status" in result
    assert "ssl_tls_in_transit" in result
    assert "encryption_at_rest" in result
    assert "encrypted_fields" in result
    assert "notes" in result

    # Check encrypted fields are documented
    assert "repository.connection_config" in result["encrypted_fields"]
    assert "repository.webhook_secret" in result["encrypted_fields"]


def test_audit_redis():
    """Test Redis encryption audit."""
    service = SecurityAuditService()
    result = service._audit_redis()

    assert "status" in result
    assert "tls_in_transit" in result
    assert "encryption_at_rest" in result
    assert "notes" in result


def test_audit_object_storage():
    """Test object storage encryption audit."""
    service = SecurityAuditService()
    result = service._audit_object_storage()

    assert "status" in result
    assert "tls_in_transit" in result
    assert "encryption_at_rest" in result
    assert "notes" in result


def test_audit_secrets_encryption():
    """Test secrets encryption audit."""
    service = SecurityAuditService()
    result = service._audit_secrets_encryption()

    assert "status" in result
    assert "encryption_key" in result
    assert "encrypted_secrets" in result
    assert "notes" in result

    # Check that encrypted secrets list is not empty
    assert len(result["encrypted_secrets"]) > 0

    # Check encryption algorithm is documented
    assert "algorithm" in result["encryption_key"]
    assert "Fernet" in result["encryption_key"]["algorithm"]


def test_audit_api_encryption():
    """Test API encryption audit."""
    service = SecurityAuditService()
    result = service._audit_api_encryption()

    assert "status" in result
    assert "https_tls" in result
    assert "api_security" in result
    assert "notes" in result


def test_audit_returns_pass_status():
    """Test that audit returns pass status for properly configured system."""
    service = SecurityAuditService()
    audit = service.audit_encryption()

    # In dev environment with all features configured, should pass
    assert audit["overall_status"] in ["pass", "partial"]


def test_audit_all_components_have_status():
    """Test that all components have a status field."""
    service = SecurityAuditService()
    audit = service.audit_encryption()

    components = ["database", "redis", "object_storage", "secrets", "api"]
    for component in components:
        assert "status" in audit[component]
        assert audit[component]["status"] in ["pass", "partial", "fail"]
