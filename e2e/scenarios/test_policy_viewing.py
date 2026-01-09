"""
Unit tests for policy_viewing test scenarios.
"""

import pytest
from unittest.mock import Mock
from e2e.scenarios.policy_viewing import (
    view_policies,
    filter_policies_by_subject,
    filter_policies_by_resource,
    sort_policies,
    view_policy_detail,
)
from e2e.test_executor import ElementNotFoundError, BrowserError


@pytest.fixture
def mock_executor():
    """Create a mock ClaudeChromeExecutor."""
    executor = Mock()
    executor.navigate = Mock()
    executor.click = Mock()
    executor.fill_input = Mock()
    executor.wait_for_element = Mock()
    executor.assert_visible = Mock()
    executor.get_page_text = Mock(return_value="policy-row appears 5 times here")
    executor.take_screenshot = Mock()
    return executor


class TestViewPolicies:
    """Tests for view_policies function."""

    def test_view_policies_basic(self, mock_executor):
        """Test basic policy viewing without filters."""
        result = view_policies(mock_executor, verify_detail=False)

        # Verify navigation
        mock_executor.navigate.assert_called_once_with("http://localhost:3333/policies")

        # Verify table visibility check
        assert mock_executor.wait_for_element.called
        assert mock_executor.assert_visible.called

        # Verify result structure
        assert "policies_count" in result
        assert "filtered" in result
        assert "sorted_by" in result
        assert "detail_verified" in result
        assert result["filtered"] is False
        assert result["detail_verified"] is False

    def test_view_policies_with_subject_filter(self, mock_executor):
        """Test policy viewing with subject filter."""
        result = view_policies(
            mock_executor,
            filter_subject="user:john",
            verify_detail=False
        )

        # Verify filter was applied
        mock_executor.fill_input.assert_any_call(
            "input[data-testid='filter-subject']",
            "user:john",
            "Subject filter input"
        )
        assert result["filtered"] is True

    def test_view_policies_with_resource_filter(self, mock_executor):
        """Test policy viewing with resource filter."""
        result = view_policies(
            mock_executor,
            filter_resource="/api/users",
            verify_detail=False
        )

        # Verify filter was applied
        mock_executor.fill_input.assert_any_call(
            "input[data-testid='filter-resource']",
            "/api/users",
            "Resource filter input"
        )
        assert result["filtered"] is True

    def test_view_policies_with_sorting(self, mock_executor):
        """Test policy viewing with sorting."""
        result = view_policies(
            mock_executor,
            sort_by="subject",
            verify_detail=False
        )

        # Verify sort was applied
        mock_executor.click.assert_any_call(
            "th[data-testid='column-subject']",
            "Sort by subject column"
        )
        assert result["sorted_by"] == "subject"

    def test_view_policies_with_detail_verification(self, mock_executor):
        """Test policy viewing with detail view verification."""
        result = view_policies(mock_executor, verify_detail=True)

        # Verify policy row click
        mock_executor.click.assert_any_call(
            "tr[data-testid='policy-row']",
            "First policy row"
        )

        # Verify detail view checks
        assert result["detail_verified"] is True

    def test_view_policies_element_not_found(self, mock_executor):
        """Test handling of ElementNotFoundError."""
        mock_executor.wait_for_element.side_effect = ElementNotFoundError("Table not found")

        with pytest.raises(ElementNotFoundError):
            view_policies(mock_executor)

        # Verify screenshot was taken
        mock_executor.take_screenshot.assert_called()

    def test_view_policies_browser_error(self, mock_executor):
        """Test handling of BrowserError."""
        mock_executor.navigate.side_effect = BrowserError("Navigation failed")

        with pytest.raises(BrowserError):
            view_policies(mock_executor)

        # Verify screenshot was taken
        mock_executor.take_screenshot.assert_called()


class TestFilterPoliciesBySubject:
    """Tests for filter_policies_by_subject function."""

    def test_filter_by_subject_success(self, mock_executor):
        """Test successful subject filtering."""
        count = filter_policies_by_subject(mock_executor, "user:alice")

        # Verify navigation
        mock_executor.navigate.assert_called_once_with("http://localhost:3333/policies")

        # Verify filter input
        mock_executor.fill_input.assert_called_once_with(
            "input[data-testid='filter-subject']",
            "user:alice",
            "Subject filter"
        )

        # Verify count returned
        assert isinstance(count, int)

    def test_filter_by_subject_error(self, mock_executor):
        """Test error handling in subject filtering."""
        mock_executor.fill_input.side_effect = ElementNotFoundError("Filter not found")

        with pytest.raises(ElementNotFoundError):
            filter_policies_by_subject(mock_executor, "user:bob")

        # Verify screenshot taken
        mock_executor.take_screenshot.assert_called()


class TestFilterPoliciesByResource:
    """Tests for filter_policies_by_resource function."""

    def test_filter_by_resource_success(self, mock_executor):
        """Test successful resource filtering."""
        count = filter_policies_by_resource(mock_executor, "/api/data")

        # Verify navigation
        mock_executor.navigate.assert_called_once_with("http://localhost:3333/policies")

        # Verify filter input
        mock_executor.fill_input.assert_called_once_with(
            "input[data-testid='filter-resource']",
            "/api/data",
            "Resource filter"
        )

        # Verify count returned
        assert isinstance(count, int)

    def test_filter_by_resource_error(self, mock_executor):
        """Test error handling in resource filtering."""
        mock_executor.fill_input.side_effect = BrowserError("Browser crashed")

        with pytest.raises(BrowserError):
            filter_policies_by_resource(mock_executor, "/api/admin")

        # Verify screenshot taken
        mock_executor.take_screenshot.assert_called()


class TestSortPolicies:
    """Tests for sort_policies function."""

    def test_sort_by_subject(self, mock_executor):
        """Test sorting by subject column."""
        result = sort_policies(mock_executor, "subject")

        # Verify click on subject column
        mock_executor.click.assert_called_once_with(
            "th[data-testid='column-subject']",
            "Sort by subject"
        )
        assert result is True

    def test_sort_by_resource(self, mock_executor):
        """Test sorting by resource column."""
        result = sort_policies(mock_executor, "resource")

        # Verify click on resource column
        mock_executor.click.assert_called_once_with(
            "th[data-testid='column-resource']",
            "Sort by resource"
        )
        assert result is True

    def test_sort_by_invalid_column(self, mock_executor):
        """Test error on invalid column name."""
        with pytest.raises(ValueError, match="Invalid column"):
            sort_policies(mock_executor, "invalid_column")

    def test_sort_error_handling(self, mock_executor):
        """Test error handling during sorting."""
        mock_executor.click.side_effect = ElementNotFoundError("Column not found")

        with pytest.raises(ElementNotFoundError):
            sort_policies(mock_executor, "action")

        # Verify screenshot taken
        mock_executor.take_screenshot.assert_called()


class TestViewPolicyDetail:
    """Tests for view_policy_detail function."""

    def test_view_detail_success(self, mock_executor):
        """Test successful policy detail viewing."""
        result = view_policy_detail(mock_executor, policy_index=0)

        # Verify navigation
        mock_executor.navigate.assert_called_once_with("http://localhost:3333/policies")

        # Verify policy row click
        mock_executor.click.assert_called_once_with(
            "tr[data-testid='policy-row']",
            "Policy row 0"
        )

        # Verify result structure
        assert result["detail_visible"] is True
        assert result["evidence_visible"] is True

    def test_view_detail_with_index(self, mock_executor):
        """Test viewing detail of specific policy by index."""
        result = view_policy_detail(mock_executor, policy_index=2)

        # Verify correct index in click call
        mock_executor.click.assert_called_once_with(
            "tr[data-testid='policy-row']",
            "Policy row 2"
        )
        assert result["detail_visible"] is True

    def test_view_detail_error_handling(self, mock_executor):
        """Test error handling in policy detail viewing."""
        mock_executor.click.side_effect = ElementNotFoundError("Policy row not found")

        with pytest.raises(ElementNotFoundError):
            view_policy_detail(mock_executor)

        # Verify screenshot taken
        mock_executor.take_screenshot.assert_called()
