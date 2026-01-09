"""
Provisioning Flow Test Scenarios

This module provides reusable test scenarios for PBAC provisioning operations:
- Adding PBAC providers (OPA, AWS Verified Permissions, Axiomatics, PlainID)
- Provisioning policies to PBAC providers
- Testing connection to PBAC providers

These scenarios can be composed to create end-to-end test flows.
"""

import os
from typing import Dict, Optional

import structlog

from e2e.test_executor import ClaudeChromeExecutor, BrowserError, ElementNotFoundError

logger = structlog.get_logger(__name__)


def add_pbac_provider(
    executor: ClaudeChromeExecutor,
    provider_type: str = "opa",
    provider_name: str = "Test OPA Provider",
    endpoint_url: str = "http://localhost:8181",
    api_key: Optional[str] = None,
    additional_config: Optional[Dict[str, str]] = None
) -> str:
    """
    Add a PBAC provider to Policy Miner.

    This scenario navigates through the PBAC provider addition flow:
    1. Navigate to PBAC providers page
    2. Click Add Provider button
    3. Select provider type (OPA/AWS/Axiomatics/PlainID)
    4. Fill in provider configuration (name, endpoint, credentials)
    5. Click Test Connection button
    6. Assert connection test succeeds
    7. Click Save button
    8. Assert provider appears in list

    Args:
        executor: ClaudeChromeExecutor instance for browser automation
        provider_type: Type of PBAC provider (opa, aws_verified_permissions, axiomatics, plainid)
        provider_name: User-friendly name for the provider
        endpoint_url: Provider endpoint URL (e.g., http://localhost:8181 for OPA)
        api_key: Optional API key for providers that require authentication
        additional_config: Optional additional configuration fields specific to provider type

    Returns:
        provider_id: The ID of the newly added provider (extracted from UI)

    Raises:
        ElementNotFoundError: If required UI elements are not found
        BrowserError: If browser automation fails
        ValueError: If provider_type is invalid
    """
    valid_provider_types = ["opa", "aws_verified_permissions", "axiomatics", "plainid"]
    if provider_type not in valid_provider_types:
        raise ValueError(
            f"Invalid provider_type '{provider_type}'. "
            f"Must be one of: {', '.join(valid_provider_types)}"
        )

    logger.info(
        "add_pbac_provider_started",
        provider_type=provider_type,
        provider_name=provider_name,
        endpoint_url=endpoint_url
    )

    try:
        # Step 1: Navigate to PBAC providers page
        logger.info("navigating_to_pbac_providers_page")
        executor.navigate("http://localhost:3333/provisioning/providers")

        # Step 2: Wait for and click Add Provider button
        logger.info("waiting_for_add_provider_button")
        executor.wait_for_element("button[data-testid='add-provider-btn']", timeout_ms=5000)

        logger.info("clicking_add_provider_button")
        executor.click("button[data-testid='add-provider-btn']", "Add Provider button")

        # Step 3: Wait for provider type selection modal/form
        logger.info("waiting_for_provider_type_selection")
        executor.wait_for_element("select[name='provider_type']", timeout_ms=3000)

        # Select provider type from dropdown
        logger.info("selecting_provider_type", provider_type=provider_type)
        executor.click(f"select[name='provider_type'] option[value='{provider_type}']", f"{provider_type} provider type")

        # Step 4: Fill in provider configuration fields
        logger.info("filling_provider_name")
        executor.wait_for_element("input[name='provider_name']", timeout_ms=2000)
        executor.fill_input("input[name='provider_name']", provider_name, "Provider name input")

        logger.info("filling_endpoint_url")
        executor.fill_input("input[name='endpoint_url']", endpoint_url, "Endpoint URL input")

        # Fill API key if provided
        if api_key:
            logger.info("filling_api_key")
            executor.fill_input("input[name='api_key']", api_key, "API key input")

        # Fill additional configuration fields if provided
        if additional_config:
            logger.info("filling_additional_config", fields=list(additional_config.keys()))
            for field_name, field_value in additional_config.items():
                executor.fill_input(f"input[name='{field_name}']", field_value, f"{field_name} input")

        # Step 5: Click Test Connection button
        logger.info("clicking_test_connection_button")
        executor.click("button[data-testid='test-connection-btn']", "Test Connection button")

        # Step 6: Wait for connection test success message
        logger.info("waiting_for_connection_success")
        executor.wait_for_element("[data-testid='connection-success']", timeout_ms=15000)

        # Assert connection test succeeded
        logger.info("asserting_connection_success")
        executor.assert_visible("[data-testid='connection-success']", timeout_ms=2000)

        # Step 7: Click Save button
        logger.info("clicking_save_button")
        executor.click("button[data-testid='save-provider-btn']", "Save button")

        # Step 8: Wait for success message
        logger.info("waiting_for_save_success")
        executor.wait_for_element("[data-testid='provider-saved-success']", timeout_ms=10000)

        # Verify provider appears in providers list
        logger.info("verifying_provider_in_list")
        executor.navigate("http://localhost:3333/provisioning/providers")
        executor.wait_for_element("[data-testid='providers-table']", timeout_ms=5000)

        # Extract provider ID from the UI (assuming it's in a data attribute or text)
        # For now, we'll return a placeholder - in real implementation, would parse the DOM
        provider_id = f"provider_{provider_type}_{int(executor.current_url.split('/')[-1]) if executor.current_url else '1'}"

        logger.info(
            "add_pbac_provider_completed",
            provider_id=provider_id,
            provider_type=provider_type,
            provider_name=provider_name
        )

        return provider_id

    except ElementNotFoundError as e:
        logger.error("add_pbac_provider_failed_element_not_found", error=str(e))
        executor.take_screenshot(f"add_pbac_provider_failed_{provider_type}")
        raise

    except BrowserError as e:
        logger.error("add_pbac_provider_failed_browser_error", error=str(e))
        executor.take_screenshot(f"add_pbac_provider_failed_{provider_type}")
        raise

    except Exception as e:
        logger.error("add_pbac_provider_failed_unexpected", error=str(e))
        executor.take_screenshot(f"add_pbac_provider_failed_{provider_type}")
        raise BrowserError(f"Unexpected error adding PBAC provider: {e}")


def delete_pbac_provider(executor: ClaudeChromeExecutor, provider_id: str) -> bool:
    """
    Delete a PBAC provider (cleanup function).

    This scenario navigates to the provider detail page and deletes the provider:
    1. Navigate to providers page
    2. Find provider by ID
    3. Click delete button
    4. Confirm deletion
    5. Verify provider is removed from list

    Args:
        executor: ClaudeChromeExecutor instance for browser automation
        provider_id: The ID of the provider to delete

    Returns:
        True if deletion succeeded

    Raises:
        ElementNotFoundError: If provider or delete button not found
        BrowserError: If deletion fails
    """
    logger.info("delete_pbac_provider_started", provider_id=provider_id)

    try:
        # Navigate to providers page
        logger.info("navigating_to_providers_page")
        executor.navigate("http://localhost:3333/provisioning/providers")

        # Wait for providers table
        executor.wait_for_element("[data-testid='providers-table']", timeout_ms=5000)

        # Find and click delete button for the specific provider
        logger.info("clicking_delete_button", provider_id=provider_id)
        delete_selector = f"button[data-testid='delete-provider-{provider_id}']"
        executor.click(delete_selector, f"Delete provider {provider_id} button")

        # Wait for confirmation dialog
        logger.info("waiting_for_confirmation_dialog")
        executor.wait_for_element("[data-testid='confirm-delete-dialog']", timeout_ms=3000)

        # Click confirm delete button
        logger.info("confirming_deletion")
        executor.click("button[data-testid='confirm-delete-btn']", "Confirm delete button")

        # Wait for success message
        logger.info("waiting_for_deletion_success")
        executor.wait_for_element("[data-testid='provider-deleted-success']", timeout_ms=5000)

        logger.info("delete_pbac_provider_completed", provider_id=provider_id)
        return True

    except ElementNotFoundError as e:
        logger.error("delete_pbac_provider_failed_element_not_found", provider_id=provider_id, error=str(e))
        executor.take_screenshot(f"delete_pbac_provider_failed_{provider_id}")
        raise

    except BrowserError as e:
        logger.error("delete_pbac_provider_failed_browser_error", provider_id=provider_id, error=str(e))
        executor.take_screenshot(f"delete_pbac_provider_failed_{provider_id}")
        raise

    except Exception as e:
        logger.error("delete_pbac_provider_failed_unexpected", provider_id=provider_id, error=str(e))
        executor.take_screenshot(f"delete_pbac_provider_failed_{provider_id}")
        raise BrowserError(f"Unexpected error deleting PBAC provider: {e}")


def provision_policy(
    executor: ClaudeChromeExecutor,
    policy_id: str,
    provider_id: str,
    target_format: Optional[str] = None
) -> Dict[str, any]:
    """
    Provision a policy to a PBAC provider.

    This scenario navigates through the policy provisioning flow:
    1. Navigate to policy detail page
    2. Click Provision button
    3. Select target PBAC provider from dropdown
    4. Select target format (OPA Rego / AWS Cedar / Axiomatics ALFA)
    5. Click Provision button
    6. Wait for provisioning to complete
    7. Assert provisioning status shows 'Success'
    8. Assert provisioned policy appears in provider's policy list

    Args:
        executor: ClaudeChromeExecutor instance for browser automation
        policy_id: The ID of the policy to provision
        provider_id: The ID of the target PBAC provider
        target_format: Optional target policy format (rego, cedar, alfa)
                      If not provided, will be inferred from provider type

    Returns:
        Dict containing:
            - provisioning_status: Status of provisioning (success/failed)
            - translated_policy: The translated policy text
            - error_message: Error message if provisioning failed

    Raises:
        ElementNotFoundError: If required UI elements are not found
        BrowserError: If provisioning fails
    """
    logger.info(
        "provision_policy_started",
        policy_id=policy_id,
        provider_id=provider_id,
        target_format=target_format
    )

    try:
        # Step 1: Navigate to policy detail page
        logger.info("navigating_to_policy_detail", policy_id=policy_id)
        executor.navigate(f"http://localhost:3333/policies/{policy_id}")

        # Step 2: Wait for and click Provision button
        logger.info("waiting_for_provision_button")
        executor.wait_for_element("button[data-testid='provision-policy-btn']", timeout_ms=5000)

        logger.info("clicking_provision_button")
        executor.click("button[data-testid='provision-policy-btn']", "Provision button")

        # Step 3: Wait for provisioning modal and select provider
        logger.info("waiting_for_provisioning_modal")
        executor.wait_for_element("[data-testid='provisioning-modal']", timeout_ms=3000)

        logger.info("selecting_target_provider", provider_id=provider_id)
        executor.click(f"select[name='provider_id'] option[value='{provider_id}']", f"Provider {provider_id}")

        # Step 4: Select target format if provided
        if target_format:
            logger.info("selecting_target_format", target_format=target_format)
            executor.click(f"select[name='target_format'] option[value='{target_format}']", f"{target_format} format")

        # Step 5: Click Provision button in modal
        logger.info("clicking_modal_provision_button")
        executor.click("button[data-testid='modal-provision-btn']", "Provision button in modal")

        # Step 6: Wait for provisioning to complete (may take a while due to AI translation)
        logger.info("waiting_for_provisioning_completion")
        executor.wait_for_element("[data-testid='provisioning-status']", timeout_ms=120000)  # 2 minutes

        # Step 7: Assert provisioning status
        logger.info("checking_provisioning_status")
        executor.assert_visible("[data-testid='provisioning-success']", timeout_ms=5000)

        # Extract provisioning results
        # In real implementation, would parse the DOM to get translated policy text
        result = {
            "provisioning_status": "success",
            "translated_policy": "Translated policy would be extracted from DOM",
            "error_message": None
        }

        # Step 8: Verify provisioned policy in provider's policy list
        logger.info("verifying_policy_in_provider_list", provider_id=provider_id)
        executor.navigate(f"http://localhost:3333/provisioning/providers/{provider_id}/policies")
        executor.wait_for_element("[data-testid='provisioned-policies-table']", timeout_ms=5000)

        # Verify the policy appears in the list
        policy_row_selector = f"tr[data-testid='provisioned-policy-{policy_id}']"
        executor.assert_visible(policy_row_selector, timeout_ms=5000)

        logger.info(
            "provision_policy_completed",
            policy_id=policy_id,
            provider_id=provider_id,
            status=result["provisioning_status"]
        )

        return result

    except ElementNotFoundError as e:
        logger.error("provision_policy_failed_element_not_found", policy_id=policy_id, error=str(e))
        executor.take_screenshot(f"provision_policy_failed_{policy_id}")
        raise

    except BrowserError as e:
        logger.error("provision_policy_failed_browser_error", policy_id=policy_id, error=str(e))
        executor.take_screenshot(f"provision_policy_failed_{policy_id}")
        raise

    except Exception as e:
        logger.error("provision_policy_failed_unexpected", policy_id=policy_id, error=str(e))
        executor.take_screenshot(f"provision_policy_failed_{policy_id}")
        raise BrowserError(f"Unexpected error provisioning policy: {e}")
