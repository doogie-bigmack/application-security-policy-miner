"""Tests for multi-format policy translation service."""
import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.models.policy import Policy, SourceType
from app.services.translation_service import TranslationService


@pytest.fixture
def sample_policy():
    """Create a sample policy for testing."""
    policy = Mock(spec=Policy)
    policy.id = 1
    policy.subject = "Manager"
    policy.resource = "Expense Report"
    policy.action = "approve"
    policy.conditions = "amount < $5000"
    policy.description = "Managers can approve expense reports under $5000"
    policy.source_type = SourceType.BACKEND
    return policy


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    with patch("app.services.translation_service.get_llm_provider") as mock:
        provider = Mock()
        mock.return_value = provider
        yield provider


class TestMultiFormatTranslation:
    """Test multi-format policy translation."""

    @pytest.mark.asyncio
    async def test_translate_to_all_formats(self, sample_policy, mock_llm_provider):
        """Test translating a policy to all formats."""
        # Mock LLM responses for each format - synchronous, not async
        call_count = [0]  # Use list to allow mutation in closure

        def mock_create_message(*args, **kwargs):
            # Return Rego for first call, Cedar for second
            call_count[0] += 1

            if call_count[0] == 1:
                return """```rego
package authz

allow {
    input.user.role == "Manager"
    input.resource.type == "Expense Report"
    input.action == "approve"
    input.resource.amount < 5000
}
```"""
            else:
                return """```cedar
permit (
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"Expense Report"
)
when {
    resource.amount < 5000
};
```"""

        mock_llm_provider.create_message = mock_create_message

        service = TranslationService()
        translations = await service.translate_to_all_formats(sample_policy)

        # Verify all formats are present
        assert "rego" in translations
        assert "cedar" in translations
        assert "json" in translations

        # Verify Rego translation
        assert "package authz" in translations["rego"]
        assert "allow" in translations["rego"]

        # Verify Cedar translation
        assert "permit" in translations["cedar"]
        assert "principal" in translations["cedar"]

        # Verify JSON translation
        assert "Manager" in translations["json"]
        assert "Expense Report" in translations["json"]

    @pytest.mark.asyncio
    async def test_translate_to_all_formats_handles_error(
        self, sample_policy, mock_llm_provider
    ):
        """Test that translation handles errors gracefully."""
        # Mock LLM to raise an exception
        mock_llm_provider.create_message = AsyncMock(
            side_effect=Exception("LLM API error")
        )

        service = TranslationService()

        with pytest.raises(ValueError, match="Failed to translate policy to all formats"):
            await service.translate_to_all_formats(sample_policy)

    @pytest.mark.asyncio
    async def test_verify_semantic_equivalence(self, sample_policy, mock_llm_provider):
        """Test semantic equivalence verification."""
        # Mock LLM response for equivalence check - synchronous, not async
        def mock_create_message(*args, **kwargs):
            return """```json
{
    "rego": true,
    "cedar": true,
    "json": true,
    "explanation": "All translations preserve the same authorization logic"
}
```"""

        mock_llm_provider.create_message = mock_create_message

        service = TranslationService()
        translations = {
            "rego": "package authz\nallow { ... }",
            "cedar": "permit (...) when { ... };",
            "json": '{"subject": "Manager", ...}',
        }

        equivalence = await service.verify_semantic_equivalence(sample_policy, translations)

        # Verify all formats are marked as equivalent
        assert equivalence["rego"] is True
        assert equivalence["cedar"] is True
        assert equivalence["json"] is True

    @pytest.mark.asyncio
    async def test_verify_semantic_equivalence_with_differences(
        self, sample_policy, mock_llm_provider
    ):
        """Test semantic equivalence verification when translations differ."""
        # Mock LLM response indicating differences - synchronous, not async
        def mock_create_message(*args, **kwargs):
            return """```json
{
    "rego": true,
    "cedar": false,
    "json": true,
    "explanation": "Cedar translation has different condition logic"
}
```"""

        mock_llm_provider.create_message = mock_create_message

        service = TranslationService()
        translations = {
            "rego": "package authz\nallow { ... }",
            "cedar": "permit (...);",  # Missing condition
            "json": '{"subject": "Manager", ...}',
        }

        equivalence = await service.verify_semantic_equivalence(sample_policy, translations)

        # Verify Cedar is marked as not equivalent
        assert equivalence["rego"] is True
        assert equivalence["cedar"] is False
        assert equivalence["json"] is True

    @pytest.mark.asyncio
    async def test_verify_semantic_equivalence_handles_error(
        self, sample_policy, mock_llm_provider
    ):
        """Test that equivalence verification handles errors gracefully."""
        # Mock LLM to raise an exception
        mock_llm_provider.create_message = AsyncMock(
            side_effect=Exception("LLM API error")
        )

        service = TranslationService()
        translations = {
            "rego": "...",
            "cedar": "...",
            "json": "...",
        }

        equivalence = await service.verify_semantic_equivalence(sample_policy, translations)

        # All should default to False on error
        assert equivalence["rego"] is False
        assert equivalence["cedar"] is False
        assert equivalence["json"] is False

    @pytest.mark.asyncio
    async def test_parse_equivalence_response_with_valid_json(self, mock_llm_provider):
        """Test parsing valid equivalence response."""
        service = TranslationService()

        response = """```json
{
    "rego": true,
    "cedar": false,
    "json": true,
    "explanation": "Test"
}
```"""

        result = service._parse_equivalence_response(response)

        assert result["rego"] is True
        assert result["cedar"] is False
        assert result["json"] is True

    @pytest.mark.asyncio
    async def test_parse_equivalence_response_with_invalid_json(
        self, mock_llm_provider
    ):
        """Test parsing invalid equivalence response."""
        service = TranslationService()

        response = "This is not valid JSON"

        result = service._parse_equivalence_response(response)

        # Should default to False for all
        assert result["rego"] is False
        assert result["cedar"] is False
        assert result["json"] is False

    @pytest.mark.asyncio
    async def test_build_equivalence_verification_prompt(
        self, sample_policy, mock_llm_provider
    ):
        """Test building equivalence verification prompt."""
        service = TranslationService()

        translations = {
            "rego": "package authz\nallow { ... }",
            "cedar": "permit (...);",
            "json": '{"subject": "Manager"}',
        }

        prompt = service._build_equivalence_verification_prompt(sample_policy, translations)

        # Verify prompt contains all necessary information
        assert "Manager" in prompt
        assert "Expense Report" in prompt
        assert "approve" in prompt
        assert "amount < $5000" in prompt
        assert "package authz" in prompt
        assert "permit" in prompt
        assert "semantic" in prompt.lower()
        assert "json" in prompt.lower()
