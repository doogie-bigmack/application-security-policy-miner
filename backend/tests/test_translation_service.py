"""Tests for the translation service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.policy import Policy, PolicyStatus, RiskLevel, SourceType
from app.services.translation_service import TranslationService


@pytest.fixture
def sample_policy():
    """Create a sample policy for testing."""
    policy = Policy(
        policy_id=1,
        tenant_id="test-tenant",
        repository_id=1,
        subject="Manager",
        resource="expense",
        action="approve",
        conditions="amount < 5000",
        description="Managers can approve expenses under $5000",
        status=PolicyStatus.APPROVED,
        risk_score=30,
        complexity_score=20,
        impact_score=40,
        confidence_score=90,
        historical_score=0,
        risk_level=RiskLevel.LOW,
        source_type=SourceType.BACKEND,
    )
    return policy


@pytest.mark.asyncio
async def test_translate_to_rego_success(sample_policy):
    """Test successful translation to Rego format."""
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text="""```rego
package authz

# Allow managers to approve expenses under $5000
allow {
    input.user.role == "Manager"
    input.resource.type == "expense"
    input.action == "approve"
    input.resource.amount < 5000
}
```"""
        )
    ]

    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(return_value=mock_response)
        mock_get_provider.return_value = mock_provider

        service = TranslationService()
        rego_policy = await service.translate_to_rego(sample_policy)

        assert "package authz" in rego_policy
        assert "allow" in rego_policy
        assert "Manager" in rego_policy or "manager" in rego_policy.lower()
        assert "expense" in rego_policy
        assert "approve" in rego_policy


@pytest.mark.asyncio
async def test_translate_to_rego_without_code_blocks(sample_policy):
    """Test translation when response has no markdown code blocks."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text="""package authz

allow {
    input.user.role == "Manager"
    input.action == "approve"
}"""
        )
    ]

    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(return_value=mock_response)
        mock_get_provider.return_value = mock_provider

        service = TranslationService()
        rego_policy = await service.translate_to_rego(sample_policy)

        assert "package authz" in rego_policy
        assert "allow" in rego_policy


@pytest.mark.asyncio
async def test_translate_to_cedar_success(sample_policy):
    """Test successful translation to Cedar format."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text="""```cedar
permit (
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"expense"
)
when {
    resource.amount < 5000
};
```"""
        )
    ]

    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(return_value=mock_response)
        mock_get_provider.return_value = mock_provider

        service = TranslationService()
        cedar_policy = await service.translate_to_cedar(sample_policy)

        assert "permit" in cedar_policy
        assert "Manager" in cedar_policy or "manager" in cedar_policy.lower()
        assert "approve" in cedar_policy
        assert "expense" in cedar_policy


@pytest.mark.asyncio
async def test_translate_to_json(sample_policy):
    """Test translation to JSON format."""
    service = TranslationService()
    json_policy = await service.translate_to_json(sample_policy)

    assert "Manager" in json_policy
    assert "expense" in json_policy
    assert "approve" in json_policy
    assert "amount < 5000" in json_policy
    assert "backend" in json_policy.lower()


@pytest.mark.asyncio
async def test_translation_error_handling(sample_policy):
    """Test error handling when translation fails."""
    with patch("app.services.llm_provider.get_llm_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.create_message = AsyncMock(side_effect=Exception("LLM error"))
        mock_get_provider.return_value = mock_provider

        service = TranslationService()

        with pytest.raises(ValueError, match="Failed to translate policy to Rego"):
            await service.translate_to_rego(sample_policy)


@pytest.mark.asyncio
async def test_build_rego_prompt_includes_all_fields(sample_policy):
    """Test that Rego prompt includes all policy fields."""
    service = TranslationService()
    prompt = service._build_rego_translation_prompt(sample_policy)

    assert "Manager" in prompt
    assert "expense" in prompt
    assert "approve" in prompt
    assert "amount < 5000" in prompt
    assert "Managers can approve expenses under $5000" in prompt
    assert "package authz" in prompt


@pytest.mark.asyncio
async def test_build_cedar_prompt_includes_all_fields(sample_policy):
    """Test that Cedar prompt includes all policy fields."""
    service = TranslationService()
    prompt = service._build_cedar_translation_prompt(sample_policy)

    assert "Manager" in prompt
    assert "expense" in prompt
    assert "approve" in prompt
    assert "amount < 5000" in prompt
    assert "Managers can approve expenses under $5000" in prompt
    assert "permit" in prompt


def test_extract_rego_from_response_with_rego_code_block():
    """Test extracting Rego from response with rego code block."""
    service = TranslationService()
    response_text = """Here is the Rego policy:

```rego
package authz
allow { true }
```

That's the policy."""

    rego = service._extract_rego_from_response(response_text)
    assert "package authz" in rego
    assert "allow { true }" in rego
    assert "Here is" not in rego


def test_extract_rego_from_response_with_generic_code_block():
    """Test extracting Rego from response with generic code block."""
    service = TranslationService()
    response_text = """```
package authz
allow { true }
```"""

    rego = service._extract_rego_from_response(response_text)
    assert "package authz" in rego
    assert "allow { true }" in rego


def test_extract_cedar_from_response():
    """Test extracting Cedar from response."""
    service = TranslationService()
    response_text = """```cedar
permit (principal, action, resource);
```"""

    cedar = service._extract_cedar_from_response(response_text)
    assert "permit" in cedar
    assert "principal" in cedar
