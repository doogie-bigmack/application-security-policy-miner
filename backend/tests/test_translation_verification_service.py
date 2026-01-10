"""Tests for translation verification service."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.policy import Policy
from app.services.translation_verification_service import TranslationVerificationService


class TestTranslationVerificationService:
    """Test translation verification service."""

    @pytest.fixture
    def service(self):
        """Create a translation verification service instance."""
        with patch("app.services.translation_verification_service.get_llm_provider") as mock_provider:
            mock_provider.return_value = Mock()
            return TranslationVerificationService()

    @pytest.fixture
    def sample_policy(self):
        """Create a sample policy for testing."""
        policy = Mock(spec=Policy)
        policy.id = 1
        policy.subject = "Manager"
        policy.resource = "Expense"
        policy.action = "approve"
        policy.conditions = "amount < 5000"
        policy.tenant_id = "test-tenant"
        return policy

    @pytest.fixture
    def sample_original_code(self):
        """Sample Java authorization code."""
        return """
if (user.hasRole("Manager") && expense.getAmount() < 5000) {
    return AuthorizationDecision.ALLOW;
} else {
    return AuthorizationDecision.DENY;
}
"""

    @pytest.fixture
    def sample_rego_policy(self):
        """Sample OPA Rego policy."""
        return """
package authz

allow {
    input.user.role == "Manager"
    input.expense.amount < 5000
}
"""

    @pytest.fixture
    def sample_test_cases(self):
        """Sample test cases."""
        return [
            {
                "description": "Manager approves expense under limit",
                "input": {
                    "user": {"role": "Manager"},
                    "expense": {"amount": 4000},
                },
                "expected_output": "ALLOWED",
                "reasoning": "Manager with amount < 5000",
            },
            {
                "description": "Manager denied for expense over limit",
                "input": {
                    "user": {"role": "Manager"},
                    "expense": {"amount": 6000},
                },
                "expected_output": "DENIED",
                "reasoning": "Amount exceeds limit",
            },
            {
                "description": "Non-manager denied",
                "input": {
                    "user": {"role": "Employee"},
                    "expense": {"amount": 1000},
                },
                "expected_output": "DENIED",
                "reasoning": "Missing Manager role",
            },
        ]

    @pytest.mark.asyncio
    async def test_generate_test_cases_success(
        self, service, sample_policy, sample_original_code, sample_rego_policy
    ):
        """Test successful test case generation."""
        # Mock LLM response
        test_cases_json = json.dumps([
            {
                "description": "Test case 1",
                "input": {"user": {"role": "Manager"}},
                "expected_output": "ALLOWED",
                "reasoning": "Test reasoning",
            }
        ])

        async def mock_create_message(messages, max_tokens):
            mock_response = Mock()
            mock_response.content = [Mock(text=f"```json\n{test_cases_json}\n```")]
            return mock_response

        service.llm_provider.create_message = mock_create_message

        # Generate test cases
        result = await service.generate_test_cases(
            sample_policy, sample_original_code, sample_rego_policy, "rego"
        )

        # Verify
        assert len(result) == 1
        assert result[0]["description"] == "Test case 1"
        assert result[0]["expected_output"] == "ALLOWED"

    @pytest.mark.asyncio
    async def test_generate_test_cases_invalid_json(
        self, service, sample_policy, sample_original_code, sample_rego_policy
    ):
        """Test handling of invalid JSON response."""
        # Mock LLM response with invalid JSON
        async def mock_create_message(messages, max_tokens):
            mock_response = Mock()
            mock_response.content = [Mock(text="No JSON here")]
            return mock_response

        service.llm_provider.create_message = mock_create_message

        # Generate test cases
        result = await service.generate_test_cases(
            sample_policy, sample_original_code, sample_rego_policy, "rego"
        )

        # Verify empty result
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_original_code_allowed(self, service, sample_original_code):
        """Test executing original code that allows access."""
        # Mock LLM response
        async def mock_create_message(messages, max_tokens):
            mock_response = Mock()
            mock_response.content = [Mock(text="ALLOWED")]
            return mock_response

        service.llm_provider.create_message = mock_create_message

        test_case = {
            "input": {"user": {"role": "Manager"}, "expense": {"amount": 4000}}
        }

        # Execute
        result = await service._execute_original_code(sample_original_code, test_case)

        # Verify
        assert result == "ALLOWED"

    @pytest.mark.asyncio
    async def test_execute_original_code_denied(self, service, sample_original_code):
        """Test executing original code that denies access."""
        # Mock LLM response
        async def mock_create_message(messages, max_tokens):
            mock_response = Mock()
            mock_response.content = [Mock(text="DENIED")]
            return mock_response

        service.llm_provider.create_message = mock_create_message

        test_case = {
            "input": {"user": {"role": "Employee"}, "expense": {"amount": 1000}}
        }

        # Execute
        result = await service._execute_original_code(sample_original_code, test_case)

        # Verify
        assert result == "DENIED"

    @pytest.mark.asyncio
    async def test_execute_translated_policy_allowed(self, service, sample_rego_policy):
        """Test executing translated policy that allows access."""
        # Mock LLM response
        async def mock_create_message(messages, max_tokens):
            mock_response = Mock()
            mock_response.content = [Mock(text="ALLOWED")]
            return mock_response

        service.llm_provider.create_message = mock_create_message

        test_case = {
            "input": {"user": {"role": "Manager"}, "expense": {"amount": 4000}}
        }

        # Execute
        result = await service._execute_translated_policy(
            sample_rego_policy, "rego", test_case
        )

        # Verify
        assert result == "ALLOWED"

    @pytest.mark.asyncio
    async def test_execute_test_cases_all_match(
        self, service, sample_original_code, sample_rego_policy, sample_test_cases
    ):
        """Test executing test cases where all results match."""
        # Mock LLM to always return expected results
        async def mock_create_message(messages, max_tokens):
            content = messages[0]["content"]
            # Parse test case expected output from the message
            if "ALLOWED" in content or "4000" in content or "1000" in str(sample_test_cases[0]["input"]):
                result = "ALLOWED"
            else:
                result = "DENIED"

            # Match expected outputs for our test cases
            if "Employee" in content:
                result = "DENIED"
            elif "6000" in content:
                result = "DENIED"
            elif "Manager" in content and "4000" in content:
                result = "ALLOWED"

            mock_response = Mock()
            mock_response.content = [Mock(text=result)]
            return mock_response

        service.llm_provider.create_message = mock_create_message

        # Execute
        results = await service.execute_test_cases(
            sample_test_cases, sample_original_code, sample_rego_policy, "rego"
        )

        # Verify
        assert results["total_tests"] == 3
        assert results["equivalence_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_execute_test_cases_with_differences(
        self, service, sample_original_code, sample_rego_policy, sample_test_cases
    ):
        """Test executing test cases where some results differ."""
        # Mock LLM to return different results
        call_count = [0]

        async def mock_create_message(messages, max_tokens):
            call_count[0] += 1
            # Make original code and translated policy disagree on second test
            if call_count[0] % 2 == 0:  # Translated policy calls
                if call_count[0] == 4:  # Second test case, translated
                    result = "ALLOWED"  # Disagree with original
                else:
                    result = "ALLOWED" if call_count[0] == 2 else "DENIED"
            else:  # Original code calls
                result = "ALLOWED" if call_count[0] == 1 else "DENIED"

            mock_response = Mock()
            mock_response.content = [Mock(text=result)]
            return mock_response

        service.llm_provider.create_message = mock_create_message

        # Execute
        results = await service.execute_test_cases(
            sample_test_cases, sample_original_code, sample_rego_policy, "rego"
        )

        # Verify some failures
        assert results["total_tests"] == 3
        assert results["failed"] > 0
        assert results["equivalence_percentage"] < 100.0
        assert len(results["differences"]) > 0

    @pytest.mark.asyncio
    async def test_verify_translation_100_percent_match(
        self, service, sample_policy, sample_original_code, sample_rego_policy
    ):
        """Test complete verification workflow with 100% equivalence."""
        # Mock test case generation
        test_cases = [
            {
                "description": "Test 1",
                "input": {"user": {"role": "Manager"}},
                "expected_output": "ALLOWED",
                "reasoning": "Test",
            }
        ]
        service.generate_test_cases = AsyncMock(return_value=test_cases)

        # Mock execution with 100% match
        execution_results = {
            "total_tests": 1,
            "passed": 1,
            "failed": 0,
            "test_results": [],
            "equivalence_percentage": 100.0,
            "differences": [],
        }
        service.execute_test_cases = AsyncMock(return_value=execution_results)

        # Verify
        result = await service.verify_translation(
            sample_policy, sample_original_code, sample_rego_policy, "rego"
        )

        # Check result
        assert result["status"] == "verified"
        assert result["results"]["equivalence_percentage"] == 100.0
        assert "semantically equivalent" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_verify_translation_mostly_equivalent(
        self, service, sample_policy, sample_original_code, sample_rego_policy
    ):
        """Test verification with 90-99% equivalence."""
        # Mock test case generation
        test_cases = [{"description": "Test", "input": {}, "expected_output": "ALLOWED", "reasoning": "Test"}]
        service.generate_test_cases = AsyncMock(return_value=test_cases)

        # Mock execution with 95% match
        execution_results = {
            "total_tests": 20,
            "passed": 19,
            "failed": 1,
            "test_results": [],
            "equivalence_percentage": 95.0,
            "differences": [{"test_case": "Test", "original": "ALLOWED", "translated": "DENIED"}],
        }
        service.execute_test_cases = AsyncMock(return_value=execution_results)

        # Verify
        result = await service.verify_translation(
            sample_policy, sample_original_code, sample_rego_policy, "rego"
        )

        # Check result
        assert result["status"] == "mostly_equivalent"
        assert result["results"]["equivalence_percentage"] == 95.0

    @pytest.mark.asyncio
    async def test_verify_translation_not_equivalent(
        self, service, sample_policy, sample_original_code, sample_rego_policy
    ):
        """Test verification with low equivalence."""
        # Mock test case generation
        test_cases = [{"description": "Test", "input": {}, "expected_output": "ALLOWED", "reasoning": "Test"}]
        service.generate_test_cases = AsyncMock(return_value=test_cases)

        # Mock execution with 50% match
        execution_results = {
            "total_tests": 10,
            "passed": 5,
            "failed": 5,
            "test_results": [],
            "equivalence_percentage": 50.0,
            "differences": [],
        }
        service.execute_test_cases = AsyncMock(return_value=execution_results)

        # Verify
        result = await service.verify_translation(
            sample_policy, sample_original_code, sample_rego_policy, "rego"
        )

        # Check result
        assert result["status"] == "not_equivalent"
        assert result["results"]["equivalence_percentage"] == 50.0
        assert "significant differences" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_verify_translation_no_test_cases(
        self, service, sample_policy, sample_original_code, sample_rego_policy
    ):
        """Test verification when test case generation fails."""
        # Mock empty test case generation
        service.generate_test_cases = AsyncMock(return_value=[])

        # Verify
        result = await service.verify_translation(
            sample_policy, sample_original_code, sample_rego_policy, "rego"
        )

        # Check error result
        assert result["status"] == "error"
        assert "Failed to generate test cases" in result["message"]
