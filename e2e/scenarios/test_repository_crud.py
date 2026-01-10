"""
Unit tests for repository_crud scenarios.

These tests verify that the scenario functions have the correct signatures
and can be imported successfully. Actual browser automation testing is done
through the E2E test runner.
"""

import pytest

from e2e.scenarios import add_github_repository, delete_repository, scan_repository
from e2e.test_executor import ClaudeChromeExecutor


def test_add_github_repository_function_exists():
    """Test that add_github_repository function is importable."""
    assert callable(add_github_repository)


def test_delete_repository_function_exists():
    """Test that delete_repository function is importable."""
    assert callable(delete_repository)


def test_scan_repository_function_exists():
    """Test that scan_repository function is importable."""
    assert callable(scan_repository)


def test_add_github_repository_signature():
    """Test that add_github_repository has the expected signature."""
    import inspect

    sig = inspect.signature(add_github_repository)
    params = list(sig.parameters.keys())

    assert "executor" in params
    assert "repository_url" in params
    assert "github_token" in params


def test_delete_repository_signature():
    """Test that delete_repository has the expected signature."""
    import inspect

    sig = inspect.signature(delete_repository)
    params = list(sig.parameters.keys())

    assert "executor" in params
    assert "repository_id" in params


def test_scan_repository_signature():
    """Test that scan_repository has the expected signature."""
    import inspect

    sig = inspect.signature(scan_repository)
    params = list(sig.parameters.keys())

    assert "executor" in params
    assert "repository_id" in params


@pytest.mark.skip(reason="Requires actual browser automation - tested via E2E runner")
def test_add_github_repository_integration():
    """Integration test for add_github_repository (requires browser)."""
    executor = ClaudeChromeExecutor()
    # This would call the actual function with a test repository
    # repository_id = add_github_repository(executor, "https://github.com/test/repo")
    # assert repository_id is not None
    pass


@pytest.mark.skip(reason="Requires actual browser automation - tested via E2E runner")
def test_scan_repository_integration():
    """Integration test for scan_repository (requires browser)."""
    executor = ClaudeChromeExecutor()
    # This would call the actual function with a test repository ID
    # scan_results = scan_repository(executor, "test-repo")
    # assert scan_results["policies_count"] > 0
    pass


@pytest.mark.skip(reason="Requires actual browser automation - tested via E2E runner")
def test_delete_repository_integration():
    """Integration test for delete_repository (requires browser)."""
    executor = ClaudeChromeExecutor()
    # This would call the actual function with a test repository ID
    # success = delete_repository(executor, "test-repo")
    # assert success is True
    pass
