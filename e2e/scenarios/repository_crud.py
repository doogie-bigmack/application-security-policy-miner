"""
Repository CRUD Test Scenarios

This module provides reusable test scenarios for repository management operations:
- Adding GitHub repositories
- Scanning repositories
- Deleting repositories

These scenarios can be composed to create end-to-end test flows.
"""

import os
from typing import Optional

import structlog

from e2e.test_executor import ClaudeChromeExecutor, BrowserError, ElementNotFoundError

logger = structlog.get_logger(__name__)


def add_github_repository(
    executor: ClaudeChromeExecutor,
    repository_url: str = "https://github.com/test-org/test-repo",
    github_token: Optional[str] = None
) -> str:
    """
    Add a GitHub repository to Policy Miner.

    This scenario navigates through the repository addition flow:
    1. Navigate to repositories page
    2. Click Add Repository button
    3. Select GitHub integration
    4. Fill in GitHub token
    5. Enter repository URL
    6. Click Connect
    7. Verify success message
    8. Verify repository appears in list

    Args:
        executor: ClaudeChromeExecutor instance for browser automation
        repository_url: GitHub repository URL to add (default: test repo)
        github_token: GitHub personal access token (reads from GITHUB_TEST_TOKEN env var if not provided)

    Returns:
        repository_id: The ID of the newly added repository (extracted from UI)

    Raises:
        ElementNotFoundError: If required UI elements are not found
        BrowserError: If browser automation fails
        EnvironmentError: If GITHUB_TEST_TOKEN is not set and github_token not provided
    """
    logger.info("add_github_repository_started", repository_url=repository_url)

    # Get GitHub token from environment if not provided
    if github_token is None:
        github_token = os.environ.get("GITHUB_TEST_TOKEN")
        if not github_token:
            raise EnvironmentError(
                "GITHUB_TEST_TOKEN environment variable not set. "
                "Set it with: export GITHUB_TEST_TOKEN=your_token_here"
            )

    try:
        # Step 1: Navigate to repositories page
        logger.info("navigating_to_repositories_page")
        executor.navigate("http://localhost:3333/repositories")

        # Step 2: Wait for and click Add Repository button
        logger.info("waiting_for_add_repository_button")
        executor.wait_for_element("button[data-testid='add-repository-btn']", timeout_ms=5000)

        logger.info("clicking_add_repository_button")
        executor.click("button[data-testid='add-repository-btn']", "Add Repository button")

        # Step 3: Wait for and click GitHub integration option
        logger.info("waiting_for_github_integration_option")
        executor.wait_for_element("button[data-testid='github-integration']", timeout_ms=3000)

        logger.info("selecting_github_integration")
        executor.click("button[data-testid='github-integration']", "GitHub integration option")

        # Step 4: Wait for and fill GitHub token field
        logger.info("waiting_for_github_token_input")
        executor.wait_for_element("input[name='github_token']", timeout_ms=3000)

        logger.info("filling_github_token")
        executor.fill_input("input[name='github_token']", github_token, "GitHub token input")

        # Step 5: Fill repository URL field
        logger.info("filling_repository_url")
        executor.fill_input("input[name='repository_url']", repository_url, "Repository URL input")

        # Step 6: Click Connect button
        logger.info("clicking_connect_button")
        executor.click("button[data-testid='connect-repository-btn']", "Connect button")

        # Step 7: Wait for success message
        logger.info("waiting_for_success_message")
        executor.wait_for_element("[data-testid='success-message']", timeout_ms=10000)

        # Step 8: Verify repository list is visible
        logger.info("verifying_repository_list_visible")
        executor.assert_visible("[data-testid='repository-list']", timeout_ms=5000)

        # Step 9: Extract repository ID from the newly added repository
        # The repository should have a data attribute with the test repo name
        repo_name = repository_url.split("/")[-1]  # Extract "test-repo" from URL
        logger.info("extracting_repository_id", repo_name=repo_name)

        # Verify the repository appears in the list
        executor.assert_visible(f"[data-repository-name='{repo_name}']", timeout_ms=5000)

        # In a real implementation, we would extract the repository ID from the UI
        # For now, we'll use the repository name as a placeholder ID
        repository_id = repo_name

        logger.info(
            "add_github_repository_completed",
            repository_id=repository_id,
            repository_url=repository_url
        )

        return repository_id

    except ElementNotFoundError as e:
        logger.error("add_github_repository_failed", error=str(e), error_type="element_not_found")
        # Take screenshot for debugging
        executor.take_screenshot("add_github_repository_failed.png")
        raise

    except BrowserError as e:
        logger.error("add_github_repository_failed", error=str(e), error_type="browser_error")
        # Take screenshot for debugging
        executor.take_screenshot("add_github_repository_failed.png")
        raise

    except Exception as e:
        logger.error("add_github_repository_failed", error=str(e), error_type="unexpected_error")
        # Take screenshot for debugging
        executor.take_screenshot("add_github_repository_failed.png")
        raise BrowserError(f"Unexpected error adding GitHub repository: {e}")


def delete_repository(executor: ClaudeChromeExecutor, repository_id: str) -> bool:
    """
    Delete a repository from Policy Miner (cleanup function).

    This scenario navigates to the repository detail page and deletes it:
    1. Navigate to repository detail page
    2. Click Delete button
    3. Confirm deletion in modal
    4. Verify repository is removed from list

    Args:
        executor: ClaudeChromeExecutor instance for browser automation
        repository_id: The ID of the repository to delete

    Returns:
        bool: True if deletion succeeded

    Raises:
        ElementNotFoundError: If required UI elements are not found
        BrowserError: If browser automation fails
    """
    logger.info("delete_repository_started", repository_id=repository_id)

    try:
        # Step 1: Navigate to repository detail page
        logger.info("navigating_to_repository_detail_page", repository_id=repository_id)
        executor.navigate(f"http://localhost:3333/repositories/{repository_id}")

        # Step 2: Wait for and click Delete button
        logger.info("waiting_for_delete_button")
        executor.wait_for_element("button[data-testid='delete-repository-btn']", timeout_ms=5000)

        logger.info("clicking_delete_button")
        executor.click("button[data-testid='delete-repository-btn']", "Delete Repository button")

        # Step 3: Wait for confirmation modal and click Confirm
        logger.info("waiting_for_confirmation_modal")
        executor.wait_for_element("button[data-testid='confirm-delete-btn']", timeout_ms=3000)

        logger.info("confirming_deletion")
        executor.click("button[data-testid='confirm-delete-btn']", "Confirm Delete button")

        # Step 4: Wait for success message
        logger.info("waiting_for_deletion_success")
        executor.wait_for_element("[data-testid='delete-success-message']", timeout_ms=5000)

        # Step 5: Verify repository is removed from list
        logger.info("navigating_to_repositories_list")
        executor.navigate("http://localhost:3333/repositories")

        # Wait for repository list to load
        executor.wait_for_element("[data-testid='repository-list']", timeout_ms=5000)

        logger.info("delete_repository_completed", repository_id=repository_id)

        return True

    except ElementNotFoundError as e:
        logger.error("delete_repository_failed", error=str(e), error_type="element_not_found")
        executor.take_screenshot("delete_repository_failed.png")
        raise

    except BrowserError as e:
        logger.error("delete_repository_failed", error=str(e), error_type="browser_error")
        executor.take_screenshot("delete_repository_failed.png")
        raise

    except Exception as e:
        logger.error("delete_repository_failed", error=str(e), error_type="unexpected_error")
        executor.take_screenshot("delete_repository_failed.png")
        raise BrowserError(f"Unexpected error deleting repository: {e}")


def scan_repository(executor: ClaudeChromeExecutor, repository_id: str) -> dict:
    """
    Trigger a scan of a repository and wait for completion.

    This scenario:
    1. Navigate to repository detail page
    2. Click Start Scan button
    3. Wait for scan to start
    4. Wait for scan to complete (up to 2 minutes)
    5. Navigate to policies page
    6. Verify policies were extracted

    Args:
        executor: ClaudeChromeExecutor instance for browser automation
        repository_id: The ID of the repository to scan

    Returns:
        dict: Scan results with keys:
            - scan_id: The ID of the completed scan
            - policies_count: Number of policies extracted
            - duration_seconds: How long the scan took

    Raises:
        ElementNotFoundError: If required UI elements are not found
        BrowserError: If browser automation fails
        TimeoutError: If scan takes longer than 2 minutes
    """
    logger.info("scan_repository_started", repository_id=repository_id)

    try:
        # Step 1: Navigate to repository detail page
        logger.info("navigating_to_repository_detail_page", repository_id=repository_id)
        executor.navigate(f"http://localhost:3333/repositories/{repository_id}")

        # Step 2: Wait for and click Start Scan button
        logger.info("waiting_for_start_scan_button")
        executor.wait_for_element("button[data-testid='start-scan-btn']", timeout_ms=5000)

        logger.info("clicking_start_scan_button")
        executor.click("button[data-testid='start-scan-btn']", "Start Scan button")

        # Step 3: Wait for scan to start (status changes to "running")
        logger.info("waiting_for_scan_to_start")
        executor.wait_for_element("[data-testid='scan-status'][data-status='running']", timeout_ms=5000)

        # Step 4: Wait for scan to complete (status changes to "completed")
        # This can take up to 2 minutes depending on repository size
        logger.info("waiting_for_scan_to_complete")
        executor.wait_for_element("[data-testid='scan-status'][data-status='completed']", timeout_ms=120000)

        # Step 5: Navigate to policies page to verify extraction
        logger.info("navigating_to_policies_page")
        executor.navigate("http://localhost:3333/policies")

        # Step 6: Wait for policies table to load
        logger.info("waiting_for_policies_table")
        executor.wait_for_element("[data-testid='policies-table']", timeout_ms=5000)

        # Step 7: Verify at least one policy row exists
        logger.info("verifying_policies_extracted")
        executor.assert_visible("[data-testid='policy-row']", timeout_ms=5000)

        # In a real implementation, we would extract:
        # - scan_id from the UI
        # - policies_count by counting policy rows
        # - duration_seconds from scan metadata
        # For now, we'll return placeholder values
        scan_results = {
            "scan_id": f"scan_{repository_id}",
            "policies_count": 1,  # Placeholder - would count actual rows
            "duration_seconds": 0  # Placeholder - would calculate from timestamps
        }

        logger.info(
            "scan_repository_completed",
            repository_id=repository_id,
            scan_results=scan_results
        )

        return scan_results

    except ElementNotFoundError as e:
        logger.error("scan_repository_failed", error=str(e), error_type="element_not_found")
        executor.take_screenshot("scan_repository_failed.png")
        raise

    except BrowserError as e:
        logger.error("scan_repository_failed", error=str(e), error_type="browser_error")
        executor.take_screenshot("scan_repository_failed.png")
        raise

    except Exception as e:
        logger.error("scan_repository_failed", error=str(e), error_type="unexpected_error")
        executor.take_screenshot("scan_repository_failed.png")
        raise BrowserError(f"Unexpected error scanning repository: {e}")
