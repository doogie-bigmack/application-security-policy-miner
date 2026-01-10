"""Tests for TranslationService TEST_MODE functionality."""

import os
from unittest.mock import Mock, patch

import pytest

from app.models.policy import Policy, PolicyStatus, RiskLevel, SourceType


@pytest.fixture
def mock_policy():
    """Create a mock policy for testing."""
    policy = Mock(spec=Policy)
    policy.id = 1
    policy.subject = "Manager"
    policy.resource = "Expense"
    policy.action = "approve"
    policy.conditions = "amount < 5000"
    policy.description = "Managers can approve expenses under $5000"
    policy.source_type = SourceType.BACKEND
    policy.status = PolicyStatus.PENDING
    policy.risk_level = RiskLevel.LOW
    return policy


@pytest.mark.asyncio
async def test_translation_service_test_mode_enabled():
    """Test that TranslationService detects TEST_MODE correctly."""
    from app.services.translation_service import TranslationService

    # Set TEST_MODE
    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        service = TranslationService()
        assert service.test_mode is True
        assert service.llm_provider is None


@pytest.mark.asyncio
async def test_translation_service_test_mode_disabled():
    """Test that TranslationService works normally when TEST_MODE is disabled."""
    from app.services.translation_service import TranslationService

    # Unset TEST_MODE and set ANTHROPIC_API_KEY for normal operation
    with patch.dict(os.environ, {"TEST_MODE": "false", "ANTHROPIC_API_KEY": "test-key"}):
        service = TranslationService()
        assert service.test_mode is False
        assert service.llm_provider is not None


@pytest.mark.asyncio
async def test_translate_to_rego_test_mode(mock_policy):
    """Test that translate_to_rego returns mock data in TEST_MODE."""
    from app.services.translation_service import TranslationService

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        service = TranslationService()
        rego_policy = await service.translate_to_rego(mock_policy)

        # Verify it's a valid Rego policy structure
        assert "package authz" in rego_policy
        assert "allow {" in rego_policy
        assert mock_policy.subject in rego_policy
        assert mock_policy.resource in rego_policy
        assert mock_policy.action in rego_policy
        assert mock_policy.conditions in rego_policy
        assert mock_policy.description in rego_policy


@pytest.mark.asyncio
async def test_translate_to_cedar_test_mode(mock_policy):
    """Test that translate_to_cedar returns mock data in TEST_MODE."""
    from app.services.translation_service import TranslationService

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        service = TranslationService()
        cedar_policy = await service.translate_to_cedar(mock_policy)

        # Verify it's a valid Cedar policy structure
        assert "permit (" in cedar_policy
        assert cedar_policy.strip().endswith(";")
        assert "principal" in cedar_policy
        assert "action" in cedar_policy
        assert "resource" in cedar_policy
        assert mock_policy.subject in cedar_policy
        assert mock_policy.resource in cedar_policy
        assert mock_policy.action in cedar_policy
        assert mock_policy.conditions in cedar_policy


@pytest.mark.asyncio
async def test_translate_to_json_test_mode(mock_policy):
    """Test that translate_to_json works the same in TEST_MODE (no LLM call)."""
    import json

    from app.services.translation_service import TranslationService

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        service = TranslationService()
        json_policy = await service.translate_to_json(mock_policy)

        # Verify it's valid JSON
        parsed = json.loads(json_policy)
        assert parsed["subject"] == mock_policy.subject
        assert parsed["resource"] == mock_policy.resource
        assert parsed["action"] == mock_policy.action
        assert parsed["conditions"] == mock_policy.conditions
        assert parsed["description"] == mock_policy.description


@pytest.mark.asyncio
async def test_mock_rego_policy_no_conditions():
    """Test mock Rego generation when policy has no conditions."""
    from app.services.translation_service import TranslationService

    policy = Mock(spec=Policy)
    policy.id = 2
    policy.subject = "Admin"
    policy.resource = "System"
    policy.action = "configure"
    policy.conditions = None
    policy.description = "Admin system configuration"

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        service = TranslationService()
        rego_policy = await service.translate_to_rego(policy)

        assert "package authz" in rego_policy
        assert "Admin" in rego_policy
        assert "System" in rego_policy
        assert "configure" in rego_policy
        # Should not have conditions check
        assert "# Conditions:" not in rego_policy


@pytest.mark.asyncio
async def test_mock_cedar_policy_no_conditions():
    """Test mock Cedar generation when policy has no conditions."""
    from app.services.translation_service import TranslationService

    policy = Mock(spec=Policy)
    policy.id = 3
    policy.subject = "Developer"
    policy.resource = "Code"
    policy.action = "commit"
    policy.conditions = None
    policy.description = "Developers can commit code"

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        service = TranslationService()
        cedar_policy = await service.translate_to_cedar(policy)

        assert "permit (" in cedar_policy
        assert "Developer" in cedar_policy
        assert "Code" in cedar_policy
        assert "commit" in cedar_policy
        # Should not have when clause
        assert "when {" not in cedar_policy


@pytest.mark.asyncio
async def test_mock_rego_policy_structure():
    """Test that mock Rego policy has correct structure."""
    from app.services.translation_service import TranslationService

    policy = Mock(spec=Policy)
    policy.id = 4
    policy.subject = "User"
    policy.resource = "Document"
    policy.action = "read"
    policy.conditions = "status == 'published'"
    policy.description = "Users can read published documents"

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        service = TranslationService()
        rego_policy = await service.translate_to_rego(policy)

        # Verify the structure
        lines = rego_policy.split("\n")

        # First line should be package declaration
        assert lines[0] == "package authz"

        # Should contain comments
        assert any("# Users can read published documents" in line for line in lines)
        assert any("# Subject: User" in line for line in lines)
        assert any("# Resource: Document" in line for line in lines)
        assert any("# Action: read" in line for line in lines)

        # Should contain allow block
        assert "allow {" in rego_policy

        # Should contain input checks
        assert 'input.user.role == "User"' in rego_policy
        assert 'input.resource.type == "Document"' in rego_policy
        assert 'input.action == "read"' in rego_policy


@pytest.mark.asyncio
async def test_mock_cedar_policy_structure():
    """Test that mock Cedar policy has correct structure."""
    from app.services.translation_service import TranslationService

    policy = Mock(spec=Policy)
    policy.id = 5
    policy.subject = "Analyst"
    policy.resource = "Report"
    policy.action = "generate"
    policy.conditions = "department == 'Finance'"
    policy.description = "Analysts can generate reports for Finance"

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        service = TranslationService()
        cedar_policy = await service.translate_to_cedar(policy)

        # Verify the structure
        assert cedar_policy.strip().endswith(";")

        # Should contain comments
        assert "// Analysts can generate reports for Finance" in cedar_policy
        assert "// Subject: Analyst" in cedar_policy
        assert "// Resource: Report" in cedar_policy
        assert "// Action: generate" in cedar_policy

        # Should contain permit statement
        assert "permit (" in cedar_policy

        # Should contain policy elements
        assert 'principal in Role::"Analyst"' in cedar_policy
        assert 'action == Action::"generate"' in cedar_policy
        assert 'resource in ResourceType::"Report"' in cedar_policy

        # Should contain when clause
        assert "when {" in cedar_policy
        assert "department == 'Finance'" in cedar_policy
