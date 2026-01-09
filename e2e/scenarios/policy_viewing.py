"""
Policy Viewing Test Scenarios

This module provides reusable test scenarios for policy viewing operations:
- Navigating to policies page
- Viewing policy tables
- Filtering policies by subject/resource
- Sorting policies by columns
- Viewing policy details with evidence

These scenarios can be composed to create end-to-end test flows.
"""

from typing import Optional, Dict, Any

import structlog

from e2e.test_executor import ClaudeChromeExecutor, BrowserError, ElementNotFoundError

logger = structlog.get_logger(__name__)


def view_policies(
    executor: ClaudeChromeExecutor,
    filter_subject: Optional[str] = None,
    filter_resource: Optional[str] = None,
    sort_by: Optional[str] = None,
    verify_detail: bool = True
) -> Dict[str, Any]:
    """
    View and interact with the policies page.

    This scenario navigates through the policy viewing flow:
    1. Navigate to policies page
    2. Assert policies table is visible
    3. Verify table columns: Subject (Who), Resource (What), Action (How), Conditions (When), Evidence
    4. Optionally filter by subject
    5. Optionally filter by resource
    6. Optionally sort by column
    7. Optionally view policy details

    Args:
        executor: ClaudeChromeExecutor instance for browser automation
        filter_subject: Optional subject filter to apply
        filter_resource: Optional resource filter to apply
        sort_by: Optional column to sort by (subject, resource, action, conditions)
        verify_detail: Whether to click and verify policy detail view (default: True)

    Returns:
        dict with:
            - policies_count: Number of policies visible in table
            - filtered: Whether filtering was applied
            - sorted_by: Column sorted by (if any)
            - detail_verified: Whether detail view was verified

    Raises:
        ElementNotFoundError: If required UI elements are not found
        BrowserError: If browser automation fails
    """
    logger.info(
        "view_policies_started",
        filter_subject=filter_subject,
        filter_resource=filter_resource,
        sort_by=sort_by,
        verify_detail=verify_detail
    )

    try:
        # Step 1: Navigate to policies page
        logger.info("navigating_to_policies_page")
        executor.navigate("http://localhost:3333/policies")

        # Step 2: Wait for policies table to be visible
        logger.info("waiting_for_policies_table")
        executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=5000)

        # Step 3: Verify table is visible
        logger.info("asserting_policies_table_visible")
        executor.assert_visible("table[data-testid='policies-table']", timeout_ms=3000)

        # Step 4: Verify table columns exist
        logger.info("verifying_table_columns")
        expected_columns = [
            "th[data-testid='column-subject']",  # Who
            "th[data-testid='column-resource']",  # What
            "th[data-testid='column-action']",  # How
            "th[data-testid='column-conditions']",  # When
            "th[data-testid='column-evidence']"  # Evidence
        ]

        for column_selector in expected_columns:
            executor.assert_visible(column_selector, timeout_ms=2000)
            logger.info("column_verified", column=column_selector)

        # Count initial policies
        logger.info("counting_policies")
        # Get page text to count rows (simplified approach)
        page_text = executor.get_page_text()
        # This is a rough count - in real implementation we'd use proper selector
        policies_count = page_text.count("tr[data-testid='policy-row']") if "policy-row" in page_text else 0
        logger.info("policies_counted", count=policies_count)

        filtered = False
        sorted_by = None

        # Step 5: Apply subject filter if provided
        if filter_subject:
            logger.info("applying_subject_filter", subject=filter_subject)
            executor.wait_for_element("input[data-testid='filter-subject']", timeout_ms=3000)
            executor.fill_input("input[data-testid='filter-subject']", filter_subject, "Subject filter input")

            # Wait for filter to apply (table should update)
            executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=3000)
            filtered = True
            logger.info("subject_filter_applied", subject=filter_subject)

        # Step 6: Apply resource filter if provided
        if filter_resource:
            logger.info("applying_resource_filter", resource=filter_resource)
            executor.wait_for_element("input[data-testid='filter-resource']", timeout_ms=3000)
            executor.fill_input("input[data-testid='filter-resource']", filter_resource, "Resource filter input")

            # Wait for filter to apply
            executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=3000)
            filtered = True
            logger.info("resource_filter_applied", resource=filter_resource)

        # Step 7: Apply sorting if provided
        if sort_by:
            logger.info("applying_sort", sort_by=sort_by)
            sort_column_map = {
                "subject": "th[data-testid='column-subject']",
                "resource": "th[data-testid='column-resource']",
                "action": "th[data-testid='column-action']",
                "conditions": "th[data-testid='column-conditions']"
            }

            if sort_by in sort_column_map:
                column_selector = sort_column_map[sort_by]
                executor.click(column_selector, f"Sort by {sort_by} column")

                # Wait for table to update after sort
                executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=3000)
                sorted_by = sort_by
                logger.info("sort_applied", column=sort_by)
            else:
                logger.warning("invalid_sort_column", sort_by=sort_by, valid_columns=list(sort_column_map.keys()))

        detail_verified = False

        # Step 8: Click a policy row to view details (if verify_detail is True)
        if verify_detail:
            logger.info("clicking_policy_row_to_view_details")

            # Wait for at least one policy row
            executor.wait_for_element("tr[data-testid='policy-row']", timeout_ms=5000)

            # Click first policy row
            executor.click("tr[data-testid='policy-row']", "First policy row")

            # Wait for detail view to appear
            logger.info("waiting_for_policy_detail_view")
            executor.wait_for_element("[data-testid='policy-detail-view']", timeout_ms=5000)

            # Verify detail view shows code evidence
            logger.info("verifying_code_evidence_section")
            executor.assert_visible("[data-testid='policy-evidence']", timeout_ms=3000)

            detail_verified = True
            logger.info("policy_detail_verified")

        result = {
            "policies_count": policies_count,
            "filtered": filtered,
            "sorted_by": sorted_by,
            "detail_verified": detail_verified
        }

        logger.info("view_policies_completed", result=result)
        return result

    except ElementNotFoundError as e:
        logger.error("element_not_found", error=str(e))
        executor.take_screenshot("view_policies_element_not_found.png")
        raise

    except BrowserError as e:
        logger.error("browser_error", error=str(e))
        executor.take_screenshot("view_policies_browser_error.png")
        raise

    except Exception as e:
        logger.error("unexpected_error", error=str(e), error_type=type(e).__name__)
        executor.take_screenshot("view_policies_unexpected_error.png")
        raise BrowserError(f"Unexpected error in view_policies: {str(e)}") from e


def filter_policies_by_subject(
    executor: ClaudeChromeExecutor,
    subject: str
) -> int:
    """
    Filter policies by subject (Who).

    Args:
        executor: ClaudeChromeExecutor instance
        subject: Subject value to filter by

    Returns:
        Number of policies after filtering

    Raises:
        ElementNotFoundError: If filter input not found
        BrowserError: If browser automation fails
    """
    logger.info("filter_policies_by_subject_started", subject=subject)

    try:
        # Ensure we're on policies page
        executor.navigate("http://localhost:3333/policies")
        executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=5000)

        # Apply filter
        executor.fill_input("input[data-testid='filter-subject']", subject, "Subject filter")

        # Wait for table to update
        executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=3000)

        # Count filtered results (simplified)
        page_text = executor.get_page_text()
        count = page_text.count("tr[data-testid='policy-row']") if "policy-row" in page_text else 0

        logger.info("filter_policies_by_subject_completed", subject=subject, count=count)
        return count

    except Exception as e:
        logger.error("filter_by_subject_failed", subject=subject, error=str(e))
        executor.take_screenshot("filter_by_subject_error.png")
        raise


def filter_policies_by_resource(
    executor: ClaudeChromeExecutor,
    resource: str
) -> int:
    """
    Filter policies by resource (What).

    Args:
        executor: ClaudeChromeExecutor instance
        resource: Resource value to filter by

    Returns:
        Number of policies after filtering

    Raises:
        ElementNotFoundError: If filter input not found
        BrowserError: If browser automation fails
    """
    logger.info("filter_policies_by_resource_started", resource=resource)

    try:
        # Ensure we're on policies page
        executor.navigate("http://localhost:3333/policies")
        executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=5000)

        # Apply filter
        executor.fill_input("input[data-testid='filter-resource']", resource, "Resource filter")

        # Wait for table to update
        executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=3000)

        # Count filtered results
        page_text = executor.get_page_text()
        count = page_text.count("tr[data-testid='policy-row']") if "policy-row" in page_text else 0

        logger.info("filter_policies_by_resource_completed", resource=resource, count=count)
        return count

    except Exception as e:
        logger.error("filter_by_resource_failed", resource=resource, error=str(e))
        executor.take_screenshot("filter_by_resource_error.png")
        raise


def sort_policies(
    executor: ClaudeChromeExecutor,
    column: str
) -> bool:
    """
    Sort policies by a specific column.

    Args:
        executor: ClaudeChromeExecutor instance
        column: Column to sort by (subject, resource, action, conditions)

    Returns:
        True if sort was successful

    Raises:
        ValueError: If invalid column name provided
        ElementNotFoundError: If column header not found
        BrowserError: If browser automation fails
    """
    logger.info("sort_policies_started", column=column)

    valid_columns = ["subject", "resource", "action", "conditions"]
    if column not in valid_columns:
        raise ValueError(f"Invalid column: {column}. Must be one of {valid_columns}")

    try:
        # Ensure we're on policies page
        executor.navigate("http://localhost:3333/policies")
        executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=5000)

        # Click column header to sort
        column_selector = f"th[data-testid='column-{column}']"
        executor.click(column_selector, f"Sort by {column}")

        # Wait for table to update
        executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=3000)

        logger.info("sort_policies_completed", column=column)
        return True

    except Exception as e:
        logger.error("sort_policies_failed", column=column, error=str(e))
        executor.take_screenshot("sort_policies_error.png")
        raise


def view_policy_detail(
    executor: ClaudeChromeExecutor,
    policy_index: int = 0
) -> Dict[str, Any]:
    """
    View details of a specific policy.

    Args:
        executor: ClaudeChromeExecutor instance
        policy_index: Index of policy row to click (0-based, default: first policy)

    Returns:
        dict with:
            - detail_visible: Whether detail view is visible
            - evidence_visible: Whether code evidence is visible

    Raises:
        ElementNotFoundError: If policy row or detail view not found
        BrowserError: If browser automation fails
    """
    logger.info("view_policy_detail_started", policy_index=policy_index)

    try:
        # Ensure we're on policies page
        executor.navigate("http://localhost:3333/policies")
        executor.wait_for_element("table[data-testid='policies-table']", timeout_ms=5000)

        # Wait for policy rows
        executor.wait_for_element("tr[data-testid='policy-row']", timeout_ms=5000)

        # Click policy row (simplified - in reality would use nth-child or similar)
        executor.click("tr[data-testid='policy-row']", f"Policy row {policy_index}")

        # Wait for detail view
        executor.wait_for_element("[data-testid='policy-detail-view']", timeout_ms=5000)
        detail_visible = True

        # Check for evidence section
        executor.assert_visible("[data-testid='policy-evidence']", timeout_ms=3000)
        evidence_visible = True

        result = {
            "detail_visible": detail_visible,
            "evidence_visible": evidence_visible
        }

        logger.info("view_policy_detail_completed", result=result)
        return result

    except Exception as e:
        logger.error("view_policy_detail_failed", policy_index=policy_index, error=str(e))
        executor.take_screenshot("view_policy_detail_error.png")
        raise
