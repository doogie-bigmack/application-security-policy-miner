"""
Unit tests for TestReporter class.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile

from test_reporter import (
    TestReporter,
    TestResult,
    TestStatus,
    ErrorType,
    ErrorDiagnostic
)


@pytest.fixture
def temp_output_file():
    """Create a temporary output file for test reports."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def reporter(temp_output_file):
    """Create a TestReporter instance."""
    return TestReporter(output_path=temp_output_file)


def test_reporter_initialization(temp_output_file):
    """Test TestReporter initializes correctly."""
    reporter = TestReporter(output_path=temp_output_file)

    assert reporter.output_path == Path(temp_output_file)
    assert reporter.test_results == []
    assert reporter.run_start_time is None
    assert reporter.run_end_time is None
    assert reporter.trigger == "manual"


def test_start_run(reporter):
    """Test start_run marks the beginning of a test run."""
    test_run_id = "test-run-123"
    trigger = "damonnator"

    reporter.start_run(test_run_id=test_run_id, trigger=trigger)

    assert reporter.test_run_id == test_run_id
    assert reporter.trigger == trigger
    assert reporter.run_start_time is not None
    assert isinstance(reporter.run_start_time, datetime)


def test_end_run(reporter):
    """Test end_run marks the end of a test run."""
    reporter.start_run(test_run_id="test-run-123")
    reporter.end_run()

    assert reporter.run_end_time is not None
    assert isinstance(reporter.run_end_time, datetime)
    assert reporter.run_end_time >= reporter.run_start_time


def test_add_test_result(reporter):
    """Test adding test results."""
    result = TestResult(
        test_id="test_001",
        test_name="Test One",
        prd_story_id="FUNC-001",
        status=TestStatus.PASSED,
        duration_seconds=5.5,
        started_at="2026-01-09T10:00:00Z",
        completed_at="2026-01-09T10:00:05Z",
        steps_completed=10,
        steps_total=10
    )

    reporter.add_test_result(result)

    assert len(reporter.test_results) == 1
    assert reporter.test_results[0] == result


def test_set_prd_stories(reporter):
    """Test setting PRD stories for coverage analysis."""
    stories = ["FUNC-001", "FUNC-002", "AI-001", "UI-001"]

    reporter.set_prd_stories(stories)

    assert reporter.prd_stories == stories


def test_generate_summary_all_passed(reporter):
    """Test summary generation when all tests pass."""
    reporter.start_run("test-run-123")

    # Add 3 passing tests
    for i in range(3):
        result = TestResult(
            test_id=f"test_{i:03d}",
            test_name=f"Test {i}",
            prd_story_id=f"FUNC-{i:03d}",
            status=TestStatus.PASSED,
            duration_seconds=5.0,
            started_at="2026-01-09T10:00:00Z",
            completed_at="2026-01-09T10:00:05Z",
            steps_completed=10,
            steps_total=10
        )
        reporter.add_test_result(result)

    reporter.end_run()
    summary = reporter._generate_summary()

    assert summary.total_tests == 3
    assert summary.passed == 3
    assert summary.failed == 0
    assert summary.skipped == 0
    assert summary.error == 0
    assert summary.pass_rate == 100.0


def test_generate_summary_mixed_results(reporter):
    """Test summary generation with mixed pass/fail/skip."""
    reporter.start_run("test-run-123")

    # Add 2 passing, 1 failed, 1 skipped
    results = [
        TestResult("test_001", "Test 1", "FUNC-001", TestStatus.PASSED, 5.0,
                  "2026-01-09T10:00:00Z", "2026-01-09T10:00:05Z", 10, 10),
        TestResult("test_002", "Test 2", "FUNC-002", TestStatus.PASSED, 5.0,
                  "2026-01-09T10:00:00Z", "2026-01-09T10:00:05Z", 10, 10),
        TestResult("test_003", "Test 3", "FUNC-003", TestStatus.FAILED, 5.0,
                  "2026-01-09T10:00:00Z", "2026-01-09T10:00:05Z", 5, 10),
        TestResult("test_004", "Test 4", "FUNC-004", TestStatus.SKIPPED, 0.0,
                  "2026-01-09T10:00:00Z", "2026-01-09T10:00:00Z", 0, 10)
    ]

    for result in results:
        reporter.add_test_result(result)

    reporter.end_run()
    summary = reporter._generate_summary()

    assert summary.total_tests == 4
    assert summary.passed == 2
    assert summary.failed == 1
    assert summary.skipped == 1
    assert summary.error == 0
    assert summary.pass_rate == 50.0


def test_generate_coverage_analysis(reporter):
    """Test coverage analysis generation."""
    reporter.start_run("test-run-123")

    # Set all PRD stories
    all_stories = ["FUNC-001", "FUNC-002", "FUNC-003", "AI-001", "UI-001"]
    reporter.set_prd_stories(all_stories)

    # Add test results covering only some stories
    tested_stories = ["FUNC-001", "FUNC-002", "AI-001"]
    for story in tested_stories:
        result = TestResult(
            test_id=f"test_{story}",
            test_name=f"Test for {story}",
            prd_story_id=story,
            status=TestStatus.PASSED,
            duration_seconds=5.0,
            started_at="2026-01-09T10:00:00Z",
            completed_at="2026-01-09T10:00:05Z",
            steps_completed=10,
            steps_total=10
        )
        reporter.add_test_result(result)

    reporter.end_run()
    coverage = reporter._generate_coverage_analysis()

    assert len(coverage.prd_stories_tested) == 3
    assert coverage.prd_stories_total == 5
    assert coverage.coverage_percentage == 60.0
    assert set(coverage.untested_stories) == {"FUNC-003", "UI-001"}


def test_generate_recommendations_all_passed(reporter):
    """Test recommendations when all tests pass."""
    reporter.start_run("test-run-123")

    result = TestResult(
        test_id="test_001",
        test_name="Test 1",
        prd_story_id="FUNC-001",
        status=TestStatus.PASSED,
        duration_seconds=5.0,
        started_at="2026-01-09T10:00:00Z",
        completed_at="2026-01-09T10:00:05Z",
        steps_completed=10,
        steps_total=10
    )
    reporter.add_test_result(result)

    reporter.end_run()
    summary = reporter._generate_summary()
    recommendations = reporter._generate_recommendations(summary)

    assert any("All tests passed" in rec for rec in recommendations)


def test_generate_recommendations_element_not_found(reporter):
    """Test recommendations for element not found errors."""
    reporter.start_run("test-run-123")

    error = ErrorDiagnostic(
        type=ErrorType.ELEMENT_NOT_FOUND,
        message="Element not found: button[data-testid='submit']",
        step_index=5,
        step_description="Click submit button"
    )

    result = TestResult(
        test_id="test_001",
        test_name="Test 1",
        prd_story_id="FUNC-001",
        status=TestStatus.FAILED,
        duration_seconds=5.0,
        started_at="2026-01-09T10:00:00Z",
        completed_at="2026-01-09T10:00:05Z",
        steps_completed=5,
        steps_total=10,
        error=error
    )
    reporter.add_test_result(result)

    reporter.end_run()
    summary = reporter._generate_summary()
    recommendations = reporter._generate_recommendations(summary)

    assert any("element not found" in rec.lower() for rec in recommendations)
    assert any("data-testid" in rec for rec in recommendations)


def test_generate_recommendations_timeout(reporter):
    """Test recommendations for timeout errors."""
    reporter.start_run("test-run-123")

    error = ErrorDiagnostic(
        type=ErrorType.TIMEOUT,
        message="Timeout waiting for element",
        step_index=3,
        step_description="Wait for page load"
    )

    result = TestResult(
        test_id="test_001",
        test_name="Test 1",
        prd_story_id="FUNC-001",
        status=TestStatus.FAILED,
        duration_seconds=5.0,
        started_at="2026-01-09T10:00:00Z",
        completed_at="2026-01-09T10:00:05Z",
        steps_completed=3,
        steps_total=10,
        error=error
    )
    reporter.add_test_result(result)

    reporter.end_run()
    summary = reporter._generate_summary()
    recommendations = reporter._generate_recommendations(summary)

    assert any("timeout" in rec.lower() for rec in recommendations)
    assert any("docker-compose ps" in rec for rec in recommendations)


def test_write_report(reporter):
    """Test writing report to JSON file."""
    reporter.start_run("test-run-123", trigger="manual")

    # Add a passing test
    result = TestResult(
        test_id="test_001",
        test_name="Test 1",
        prd_story_id="FUNC-001",
        status=TestStatus.PASSED,
        duration_seconds=5.0,
        started_at="2026-01-09T10:00:00Z",
        completed_at="2026-01-09T10:00:05Z",
        steps_completed=10,
        steps_total=10
    )
    reporter.add_test_result(result)

    reporter.end_run()
    reporter.write_report()

    # Verify file was created
    assert reporter.output_path.exists()

    # Verify file contains valid JSON
    with open(reporter.output_path) as f:
        data = json.load(f)

    # Verify structure
    assert "metadata" in data
    assert "summary" in data
    assert "test_results" in data
    assert "recommendations" in data
    assert "coverage_analysis" in data

    # Verify metadata
    assert data["metadata"]["test_run_id"] == "test-run-123"
    assert data["metadata"]["trigger"] == "manual"

    # Verify summary
    assert data["summary"]["total_tests"] == 1
    assert data["summary"]["passed"] == 1
    assert data["summary"]["pass_rate"] == 100.0

    # Verify test results
    assert len(data["test_results"]) == 1
    assert data["test_results"][0]["test_id"] == "test_001"
    assert data["test_results"][0]["status"] == "passed"


def test_error_diagnostic_with_screenshot(reporter):
    """Test error diagnostic includes screenshot path."""
    reporter.start_run("test-run-123")

    error = ErrorDiagnostic(
        type=ErrorType.ELEMENT_NOT_FOUND,
        message="Element not found",
        step_index=5,
        step_description="Click button",
        screenshot="e2e/screenshots/test_failure.png",
        console_errors=["Error 1", "Error 2"]
    )

    result = TestResult(
        test_id="test_001",
        test_name="Test 1",
        prd_story_id="FUNC-001",
        status=TestStatus.FAILED,
        duration_seconds=5.0,
        started_at="2026-01-09T10:00:00Z",
        completed_at="2026-01-09T10:00:05Z",
        steps_completed=5,
        steps_total=10,
        error=error
    )
    reporter.add_test_result(result)

    reporter.end_run()
    reporter.write_report()

    # Read report and verify error details
    with open(reporter.output_path) as f:
        data = json.load(f)

    error_data = data["test_results"][0]["error"]
    assert error_data["screenshot"] == "e2e/screenshots/test_failure.png"
    assert len(error_data["console_errors"]) == 2
    assert error_data["type"] == "element_not_found"


def test_generate_report_not_initialized_raises_error(reporter):
    """Test that generate_report raises error if run not initialized."""
    with pytest.raises(ValueError, match="Test run not properly initialized"):
        reporter.generate_report()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
