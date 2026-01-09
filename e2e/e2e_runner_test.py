"""
Unit tests for E2ETestRunner
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from e2e.e2e_runner import E2ETestRunner
from e2e.test_reporter import TestStatus, ErrorType


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_test_suite(temp_dir):
    """Create a sample test suite JSON file."""
    test_suite = {
        "schema_version": "1.0",
        "test_suites": [
            {
                "suite_id": "test_suite_1",
                "name": "Test Suite 1",
                "tests": [
                    {
                        "test_id": "test_1",
                        "name": "Test 1",
                        "prd_story_id": "STORY-001",
                        "priority": "critical",
                        "steps": [
                            {
                                "action": "navigate",
                                "target": "http://localhost:3333",
                                "description": "Navigate to homepage",
                            },
                            {
                                "action": "wait_for_element",
                                "selector": "button[data-testid='test-btn']",
                                "timeout_ms": 5000,
                                "description": "Wait for button",
                            },
                        ],
                    }
                ],
            }
        ],
    }

    test_suite_path = temp_dir / "test-suite.json"
    with open(test_suite_path, "w") as f:
        json.dump(test_suite, f)

    return test_suite_path


@pytest.fixture
def sample_prd(temp_dir):
    """Create a sample PRD JSON file."""
    prd = {
        "stories": [
            {"id": "STORY-001", "description": "Test story 1"},
            {"id": "STORY-002", "description": "Test story 2"},
        ]
    }

    prd_path = temp_dir / "prd.json"
    with open(prd_path, "w") as f:
        json.dump(prd, f)

    return prd_path


@pytest.fixture
def runner(sample_test_suite, sample_prd, temp_dir):
    """Create a test runner instance."""
    output_path = temp_dir / "test-results.json"
    return E2ETestRunner(
        test_suite_path=str(sample_test_suite),
        prd_path=str(sample_prd),
        output_path=str(output_path),
    )


def test_e2e_runner_initialization(runner, sample_test_suite, sample_prd, temp_dir):
    """Test E2ETestRunner initialization."""
    assert runner.test_suite_path == Path(sample_test_suite)
    assert runner.prd_path == Path(sample_prd)
    assert runner.output_path == temp_dir / "test-results.json"
    assert runner.max_retries == 1
    assert runner.executor is not None
    assert runner.reporter is not None


def test_load_test_suite(runner):
    """Test loading test suite from JSON."""
    runner.load_test_suite()

    assert len(runner.test_suites) == 1
    assert runner.test_suites[0]["suite_id"] == "test_suite_1"
    assert len(runner.test_suites[0]["tests"]) == 1
    assert runner.test_suites[0]["tests"][0]["test_id"] == "test_1"


def test_load_test_suite_file_not_found(temp_dir):
    """Test loading test suite with missing file."""
    runner = E2ETestRunner(
        test_suite_path=str(temp_dir / "nonexistent.json"),
        prd_path="prd.json",
    )

    with pytest.raises(FileNotFoundError):
        runner.load_test_suite()


def test_load_prd(runner):
    """Test loading PRD from JSON."""
    runner.load_prd()

    assert len(runner.prd_stories) == 2
    assert runner.prd_stories[0]["id"] == "STORY-001"
    assert runner.prd_stories[1]["id"] == "STORY-002"


def test_load_prd_file_not_found(temp_dir):
    """Test loading PRD with missing file."""
    runner = E2ETestRunner(
        test_suite_path="e2e-tests.json",
        prd_path=str(temp_dir / "nonexistent.json"),
    )

    with pytest.raises(FileNotFoundError):
        runner.load_prd()


def test_substitute_env_vars(runner):
    """Test environment variable substitution."""
    os.environ["TEST_VAR"] = "test_value"

    result = runner._substitute_env_vars("URL: ${TEST_VAR}")
    assert result == "URL: test_value"

    result = runner._substitute_env_vars("Multiple: ${TEST_VAR} and ${TEST_VAR}")
    assert result == "Multiple: test_value and test_value"

    # Test missing variable (should leave as-is)
    result = runner._substitute_env_vars("Missing: ${NONEXISTENT_VAR}")
    assert result == "Missing: ${NONEXISTENT_VAR}"

    # Test non-string input
    result = runner._substitute_env_vars(123)
    assert result == 123

    # Cleanup
    del os.environ["TEST_VAR"]


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_execute_test_step_navigate(mock_executor_class, runner):
    """Test executing a navigate step."""
    mock_executor = MagicMock()
    runner.executor = mock_executor

    step = {
        "action": "navigate",
        "target": "http://localhost:3333",
        "description": "Navigate to homepage",
    }

    runner._execute_test_step(step, "test_1")
    mock_executor.navigate.assert_called_once_with("http://localhost:3333")


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_execute_test_step_click(mock_executor_class, runner):
    """Test executing a click step."""
    mock_executor = MagicMock()
    runner.executor = mock_executor

    step = {
        "action": "click",
        "selector": "button[data-testid='test-btn']",
        "description": "Click button",
    }

    runner._execute_test_step(step, "test_1")
    mock_executor.click.assert_called_once_with("button[data-testid='test-btn']")


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_execute_test_step_fill(mock_executor_class, runner):
    """Test executing a fill step."""
    mock_executor = MagicMock()
    runner.executor = mock_executor

    step = {
        "action": "fill",
        "selector": "input[name='test']",
        "value": "test_value",
        "description": "Fill input",
    }

    runner._execute_test_step(step, "test_1")
    mock_executor.fill_input.assert_called_once_with("input[name='test']", "test_value")


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_execute_test_step_wait_for_element(mock_executor_class, runner):
    """Test executing a wait_for_element step."""
    mock_executor = MagicMock()
    runner.executor = mock_executor

    step = {
        "action": "wait_for_element",
        "selector": "div[data-testid='content']",
        "timeout_ms": 5000,
        "description": "Wait for content",
    }

    runner._execute_test_step(step, "test_1")
    mock_executor.wait_for_element.assert_called_once_with(
        "div[data-testid='content']", 5000
    )


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_execute_test_step_assert_visible(mock_executor_class, runner):
    """Test executing an assert_element_visible step."""
    mock_executor = MagicMock()
    # Explicitly configure the assert_visible method as a regular method
    mock_executor.configure_mock(**{"assert_visible": MagicMock()})
    runner.executor = mock_executor

    step = {
        "action": "assert_element_visible",
        "selector": "div[data-testid='result']",
        "timeout_ms": 3000,
        "description": "Assert result visible",
    }

    runner._execute_test_step(step, "test_1")
    mock_executor.assert_visible.assert_called_once_with(
        "div[data-testid='result']", 3000
    )


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_execute_test_success(mock_executor_class, runner):
    """Test successful test execution."""
    mock_executor = MagicMock()
    runner.executor = mock_executor

    test = {
        "test_id": "test_success",
        "name": "Success Test",
        "prd_story_id": "STORY-001",
        "steps": [
            {"action": "navigate", "target": "http://localhost:3333"},
            {"action": "click", "selector": "button"},
        ],
    }

    result = runner._execute_test(test, "suite_1")

    assert result["test_id"] == "test_success"
    assert result["status"] == TestStatus.PASSED
    assert result["error"] is None
    assert result["duration_seconds"] > 0


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_execute_test_element_not_found(mock_executor_class, runner):
    """Test test execution with element not found error."""
    from e2e.test_executor import ElementNotFoundError

    mock_executor = MagicMock()
    mock_executor.click.side_effect = ElementNotFoundError("Element not found")
    mock_executor.take_screenshot.return_value = "screenshot.png"
    runner.executor = mock_executor

    test = {
        "test_id": "test_fail",
        "name": "Fail Test",
        "prd_story_id": "STORY-001",
        "steps": [
            {"action": "click", "selector": "button", "description": "Click button"},
        ],
    }

    result = runner._execute_test(test, "suite_1")

    assert result["test_id"] == "test_fail"
    assert result["status"] == TestStatus.FAILED
    assert result["error"] is not None
    assert result["error"].type == ErrorType.ELEMENT_NOT_FOUND.value
    assert result["screenshot"] == "screenshot.png"


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_run_tests_no_filters(mock_executor_class, runner):
    """Test running all tests without filters."""
    mock_executor = MagicMock()
    runner.executor = mock_executor

    runner.load_test_suite()
    runner.load_prd()
    runner.run_tests()

    # Verify reporter was used
    assert runner.reporter.run_start_time is not None
    assert runner.reporter.run_end_time is not None

    # Verify output file exists
    assert runner.output_path.exists()

    # Verify output is valid JSON
    with open(runner.output_path, "r") as f:
        results = json.load(f)
        assert "metadata" in results
        assert "summary" in results
        assert "test_results" in results


@patch("e2e.e2e_runner.ClaudeChromeExecutor")
def test_run_tests_filter_priority(mock_executor_class, runner, temp_dir):
    """Test running tests filtered by priority."""
    # Create test suite with multiple priorities
    test_suite = {
        "schema_version": "1.0",
        "test_suites": [
            {
                "suite_id": "suite_1",
                "tests": [
                    {
                        "test_id": "test_critical",
                        "name": "Critical Test",
                        "prd_story_id": "STORY-001",
                        "priority": "critical",
                        "steps": [],
                    },
                    {
                        "test_id": "test_high",
                        "name": "High Test",
                        "prd_story_id": "STORY-002",
                        "priority": "high",
                        "steps": [],
                    },
                ],
            }
        ],
    }

    test_suite_path = temp_dir / "multi-priority.json"
    with open(test_suite_path, "w") as f:
        json.dump(test_suite, f)

    runner = E2ETestRunner(
        test_suite_path=str(test_suite_path),
        prd_path=str(runner.prd_path),
        output_path=str(temp_dir / "results.json"),
    )

    mock_executor = MagicMock()
    runner.executor = mock_executor

    runner.load_test_suite()
    runner.load_prd()
    runner.run_tests(filter_priority="critical")

    # Verify only critical test was run
    with open(temp_dir / "results.json", "r") as f:
        results = json.load(f)
        assert results["summary"]["total_tests"] == 1
        assert results["test_results"][0]["test_id"] == "test_critical"


def test_main_cli_help(capsys):
    """Test CLI help output."""
    from e2e.e2e_runner import main

    with pytest.raises(SystemExit) as exc_info:
        import sys

        sys.argv = ["e2e_runner.py", "--help"]
        main()

    assert exc_info.value.code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
