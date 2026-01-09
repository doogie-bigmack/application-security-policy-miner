"""
Unit tests for provisioning_flow scenarios.
"""

import pytest
from unittest.mock import Mock, patch, call, MagicMock

from e2e.scenarios.provisioning_flow import (
    add_pbac_provider,
    delete_pbac_provider,
    provision_policy
)
from e2e.test_executor import ElementNotFoundError, BrowserError, ClaudeChromeExecutor


def create_mock_executor():
    """Create a properly mocked ClaudeChromeExecutor."""
    executor = MagicMock(spec=ClaudeChromeExecutor)
    executor.navigate = MagicMock(return_value=True)
    executor.click = MagicMock(return_value=True)
    executor.fill_input = MagicMock(return_value=True)
    executor.wait_for_element = MagicMock(return_value=True)
    executor.assert_visible = MagicMock(return_value=True)
    executor.take_screenshot = MagicMock(return_value="screenshot.png")
    executor.current_url = "http://localhost:3333/provisioning/providers/1"
    return executor


class TestAddPBACProvider:
    """Tests for add_pbac_provider function."""

    def test_add_opa_provider_success(self):
        """Test adding an OPA provider successfully."""
        executor = create_mock_executor()

        provider_id = add_pbac_provider(
            executor,
            provider_type="opa",
            provider_name="Test OPA",
            endpoint_url="http://localhost:8181"
        )

        # Verify navigation to providers page
        assert executor.navigate.call_count == 2  # Initial + verification
        executor.navigate.assert_any_call("http://localhost:3333/provisioning/providers")

        # Verify Add Provider button clicked
        executor.click.assert_any_call(
            "button[data-testid='add-provider-btn']",
            "Add Provider button"
        )

        # Verify provider type selected
        executor.click.assert_any_call(
            "select[name='provider_type'] option[value='opa']",
            "opa provider type"
        )

        # Verify form fields filled
        executor.fill_input.assert_any_call(
            "input[name='provider_name']",
            "Test OPA",
            "Provider name input"
        )
        executor.fill_input.assert_any_call(
            "input[name='endpoint_url']",
            "http://localhost:8181",
            "Endpoint URL input"
        )

        # Verify test connection clicked
        executor.click.assert_any_call(
            "button[data-testid='test-connection-btn']",
            "Test Connection button"
        )

        # Verify save button clicked
        executor.click.assert_any_call(
            "button[data-testid='save-provider-btn']",
            "Save button"
        )

        # Verify provider ID returned
        assert provider_id.startswith("provider_opa_")

    def test_add_aws_provider_with_api_key(self):
        """Test adding an AWS Verified Permissions provider with API key."""
        executor = create_mock_executor()
        executor.current_url = "http://localhost:3333/provisioning/providers/2"

        provider_id = add_pbac_provider(
            executor,
            provider_type="aws_verified_permissions",
            provider_name="Test AWS",
            endpoint_url="us-east-1",
            api_key="test-api-key-123"
        )

        # Verify API key was filled
        executor.fill_input.assert_any_call(
            "input[name='api_key']",
            "test-api-key-123",
            "API key input"
        )

        assert provider_id.startswith("provider_aws_verified_permissions_")

    def test_add_axiomatics_provider_with_additional_config(self):
        """Test adding an Axiomatics provider with additional configuration."""
        executor = create_mock_executor()
        executor.current_url = "http://localhost:3333/provisioning/providers/3"

        additional_config = {
            "policy_domain": "test-domain",
            "auth_method": "oauth2"
        }

        provider_id = add_pbac_provider(
            executor,
            provider_type="axiomatics",
            provider_name="Test Axiomatics",
            endpoint_url="https://axiomatics.example.com",
            api_key="axiom-key-456",
            additional_config=additional_config
        )

        # Verify additional config fields filled
        executor.fill_input.assert_any_call(
            "input[name='policy_domain']",
            "test-domain",
            "policy_domain input"
        )
        executor.fill_input.assert_any_call(
            "input[name='auth_method']",
            "oauth2",
            "auth_method input"
        )

        assert provider_id.startswith("provider_axiomatics_")

    def test_add_plainid_provider(self):
        """Test adding a PlainID provider."""
        executor = create_mock_executor()
        executor.current_url = "http://localhost:3333/provisioning/providers/4"

        provider_id = add_pbac_provider(
            executor,
            provider_type="plainid",
            provider_name="Test PlainID",
            endpoint_url="https://plainid.example.com"
        )

        # Verify provider type selected
        executor.click.assert_any_call(
            "select[name='provider_type'] option[value='plainid']",
            "plainid provider type"
        )

        assert provider_id.startswith("provider_plainid_")

    def test_invalid_provider_type_raises_error(self):
        """Test that invalid provider type raises ValueError."""
        executor = create_mock_executor()

        with pytest.raises(ValueError) as exc_info:
            add_pbac_provider(
                executor,
                provider_type="invalid_provider",
                provider_name="Test",
                endpoint_url="http://example.com"
            )

        assert "Invalid provider_type 'invalid_provider'" in str(exc_info.value)

    def test_element_not_found_takes_screenshot(self):
        """Test that ElementNotFoundError triggers screenshot."""
        executor = create_mock_executor()
        executor.navigate.side_effect = ElementNotFoundError("Button not found")

        with pytest.raises(ElementNotFoundError):
            add_pbac_provider(
                executor,
                provider_type="opa",
                provider_name="Test",
                endpoint_url="http://localhost:8181"
            )

        # Verify screenshot was taken
        executor.take_screenshot.assert_called_once_with("add_pbac_provider_failed_opa")

    def test_browser_error_takes_screenshot(self):
        """Test that BrowserError triggers screenshot."""
        executor = create_mock_executor()
        executor.click.side_effect = BrowserError("Click failed")

        with pytest.raises(BrowserError):
            add_pbac_provider(
                executor,
                provider_type="opa",
                provider_name="Test",
                endpoint_url="http://localhost:8181"
            )

        # Verify screenshot was taken
        executor.take_screenshot.assert_called_once_with("add_pbac_provider_failed_opa")


class TestDeletePBACProvider:
    """Tests for delete_pbac_provider function."""

    def test_delete_provider_success(self):
        """Test deleting a provider successfully."""
        executor = create_mock_executor()

        result = delete_pbac_provider(executor, "provider_123")

        # Verify navigation to providers page
        executor.navigate.assert_called_once_with("http://localhost:3333/provisioning/providers")

        # Verify delete button clicked
        executor.click.assert_any_call(
            "button[data-testid='delete-provider-provider_123']",
            "Delete provider provider_123 button"
        )

        # Verify confirmation clicked
        executor.click.assert_any_call(
            "button[data-testid='confirm-delete-btn']",
            "Confirm delete button"
        )

        # Verify waited for success message
        executor.wait_for_element.assert_any_call(
            "[data-testid='provider-deleted-success']",
            timeout_ms=5000
        )

        assert result is True

    def test_delete_provider_element_not_found(self):
        """Test delete provider with element not found."""
        executor = create_mock_executor()
        executor.click.side_effect = ElementNotFoundError("Provider not found")

        with pytest.raises(ElementNotFoundError):
            delete_pbac_provider(executor, "nonexistent_provider")

        # Verify screenshot taken
        executor.take_screenshot.assert_called_once_with("delete_pbac_provider_failed_nonexistent_provider")

    def test_delete_provider_browser_error(self):
        """Test delete provider with browser error."""
        executor = create_mock_executor()
        executor.wait_for_element.side_effect = BrowserError("Confirmation dialog failed")

        with pytest.raises(BrowserError):
            delete_pbac_provider(executor, "provider_456")

        # Verify screenshot taken
        executor.take_screenshot.assert_called_once_with("delete_pbac_provider_failed_provider_456")


class TestProvisionPolicy:
    """Tests for provision_policy function."""

    def test_provision_policy_success(self):
        """Test provisioning a policy successfully."""
        executor = create_mock_executor()

        result = provision_policy(
            executor,
            policy_id="policy_123",
            provider_id="provider_456"
        )

        # Verify navigation to policy detail page
        executor.navigate.assert_any_call("http://localhost:3333/policies/policy_123")

        # Verify provision button clicked
        executor.click.assert_any_call(
            "button[data-testid='provision-policy-btn']",
            "Provision button"
        )

        # Verify provider selected
        executor.click.assert_any_call(
            "select[name='provider_id'] option[value='provider_456']",
            "Provider provider_456"
        )

        # Verify modal provision button clicked
        executor.click.assert_any_call(
            "button[data-testid='modal-provision-btn']",
            "Provision button in modal"
        )

        # Verify provisioning status checked
        executor.assert_visible.assert_any_call(
            "[data-testid='provisioning-success']",
            timeout_ms=5000
        )

        # Verify navigation to provider's policy list
        executor.navigate.assert_any_call(
            "http://localhost:3333/provisioning/providers/provider_456/policies"
        )

        # Verify policy in provisioned list
        executor.assert_visible.assert_any_call(
            "tr[data-testid='provisioned-policy-policy_123']",
            timeout_ms=5000
        )

        # Check result
        assert result["provisioning_status"] == "success"
        assert result["error_message"] is None
        assert "translated_policy" in result

    def test_provision_policy_with_target_format(self):
        """Test provisioning a policy with specific target format."""
        executor = create_mock_executor()

        result = provision_policy(
            executor,
            policy_id="policy_789",
            provider_id="provider_123",
            target_format="cedar"
        )

        # Verify target format selected
        executor.click.assert_any_call(
            "select[name='target_format'] option[value='cedar']",
            "cedar format"
        )

        assert result["provisioning_status"] == "success"

    def test_provision_policy_element_not_found(self):
        """Test provision policy with element not found."""
        executor = create_mock_executor()
        executor.navigate.side_effect = ElementNotFoundError("Policy not found")

        with pytest.raises(ElementNotFoundError):
            provision_policy(
                executor,
                policy_id="nonexistent_policy",
                provider_id="provider_123"
            )

        # Verify screenshot taken
        executor.take_screenshot.assert_called_once_with("provision_policy_failed_nonexistent_policy")

    def test_provision_policy_browser_error(self):
        """Test provision policy with browser error."""
        executor = create_mock_executor()
        executor.click.side_effect = BrowserError("Provisioning modal failed to open")

        with pytest.raises(BrowserError):
            provision_policy(
                executor,
                policy_id="policy_999",
                provider_id="provider_888"
            )

        # Verify screenshot taken
        executor.take_screenshot.assert_called_once_with("provision_policy_failed_policy_999")

    def test_provision_policy_long_timeout(self):
        """Test that provision_policy waits up to 2 minutes for AI translation."""
        executor = create_mock_executor()

        provision_policy(
            executor,
            policy_id="policy_slow",
            provider_id="provider_slow"
        )

        # Verify long timeout for provisioning completion (120 seconds)
        executor.wait_for_element.assert_any_call(
            "[data-testid='provisioning-status']",
            timeout_ms=120000
        )
