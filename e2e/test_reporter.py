"""
TestReporter - Generates test-results.json after E2E test execution.

This module provides structured reporting for E2E test runs, including:
- Test run metadata (timing, trigger, etc.)
- Summary statistics (pass/fail counts, pass rate)
- Detailed test results with error diagnostics
- AI-powered recommendations for debugging failures
- Coverage analysis mapping to PRD stories
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class TestStatus(str, Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ErrorType(str, Enum):
    """Types of test errors."""
    ELEMENT_NOT_FOUND = "element_not_found"
    TIMEOUT = "timeout"
    ASSERTION_FAILED = "assertion_failed"
    NAVIGATION_ERROR = "navigation_error"
    BROWSER_ERROR = "browser_error"
    PREREQUISITE_FAILED = "prerequisite_failed"
    UNKNOWN = "unknown"


@dataclass
class ErrorDiagnostic:
    """Detailed error diagnostic information."""
    type: str
    message: str
    step_index: int
    step_description: str
    screenshot: Optional[str] = None
    console_errors: List[str] = None
    stack_trace: Optional[str] = None

    def __post_init__(self):
        if self.console_errors is None:
            self.console_errors = []


@dataclass
class TestResult:
    """Individual test result."""
    test_id: str
    test_name: str
    prd_story_id: str
    status: str
    duration_seconds: float
    started_at: str
    completed_at: str
    steps_completed: int
    steps_total: int
    error: Optional[ErrorDiagnostic] = None


@dataclass
class TestSummary:
    """Test run summary statistics."""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    error: int
    pass_rate: float = 0.0

    def __post_init__(self):
        """Calculate pass rate."""
        if self.total_tests > 0:
            self.pass_rate = round((self.passed / self.total_tests) * 100, 2)
        else:
            self.pass_rate = 0.0


@dataclass
class CoverageAnalysis:
    """PRD story coverage analysis."""
    prd_stories_tested: List[str]
    prd_stories_total: int
    coverage_percentage: float
    untested_stories: List[str]


@dataclass
class TestRunMetadata:
    """Test run metadata."""
    test_run_id: str
    started_at: str
    completed_at: str
    duration_seconds: float
    trigger: str
    environment: Dict[str, str]


@dataclass
class TestReport:
    """Complete test report."""
    metadata: TestRunMetadata
    summary: TestSummary
    test_results: List[TestResult]
    recommendations: List[str]
    coverage_analysis: CoverageAnalysis


class TestReporter:
    """
    Generates comprehensive test reports in JSON format.

    This class collects test execution results and produces structured
    reports with error diagnostics, recommendations, and coverage analysis.
    """

    def __init__(self, output_path: str = "test-results.json"):
        """
        Initialize TestReporter.

        Args:
            output_path: Path to write test-results.json
        """
        self.output_path = Path(output_path)
        self.test_results: List[TestResult] = []
        self.run_start_time: Optional[datetime] = None
        self.run_end_time: Optional[datetime] = None
        self.test_run_id: Optional[str] = None
        self.trigger: str = "manual"
        self.prd_stories: List[str] = []

        logger.info("test_reporter_initialized", output_path=str(self.output_path))

    def start_run(self, test_run_id: str, trigger: str = "manual") -> None:
        """
        Mark the start of a test run.

        Args:
            test_run_id: Unique identifier for this test run
            trigger: What triggered the run (manual, ci, damonnator)
        """
        self.test_run_id = test_run_id
        self.trigger = trigger
        self.run_start_time = datetime.now(timezone.utc)
        self.test_results = []

        logger.info(
            "test_run_started",
            test_run_id=test_run_id,
            trigger=trigger,
            started_at=self.run_start_time.isoformat()
        )

    def end_run(self) -> None:
        """Mark the end of a test run."""
        self.run_end_time = datetime.now(timezone.utc)

        logger.info(
            "test_run_ended",
            test_run_id=self.test_run_id,
            completed_at=self.run_end_time.isoformat()
        )

    def add_test_result(self, result: TestResult) -> None:
        """
        Add a test result to the report.

        Args:
            result: TestResult object containing test execution details
        """
        self.test_results.append(result)

        logger.info(
            "test_result_added",
            test_id=result.test_id,
            status=result.status,
            duration=result.duration_seconds
        )

    def set_prd_stories(self, prd_stories: List[str]) -> None:
        """
        Set the list of all PRD story IDs for coverage analysis.

        Args:
            prd_stories: List of all PRD story IDs
        """
        self.prd_stories = prd_stories
        logger.info("prd_stories_set", count=len(prd_stories))

    def _generate_summary(self) -> TestSummary:
        """Generate summary statistics from test results."""
        status_counts = {
            TestStatus.PASSED: 0,
            TestStatus.FAILED: 0,
            TestStatus.SKIPPED: 0,
            TestStatus.ERROR: 0
        }

        for result in self.test_results:
            status_counts[result.status] += 1

        return TestSummary(
            total_tests=len(self.test_results),
            passed=status_counts[TestStatus.PASSED],
            failed=status_counts[TestStatus.FAILED],
            skipped=status_counts[TestStatus.SKIPPED],
            error=status_counts[TestStatus.ERROR]
        )

    def _generate_coverage_analysis(self) -> CoverageAnalysis:
        """Generate PRD story coverage analysis."""
        tested_stories = list(set(result.prd_story_id for result in self.test_results))
        total_stories = len(self.prd_stories) if self.prd_stories else len(tested_stories)

        untested_stories = []
        if self.prd_stories:
            untested_stories = [s for s in self.prd_stories if s not in tested_stories]

        coverage_pct = 0.0
        if total_stories > 0:
            coverage_pct = round((len(tested_stories) / total_stories) * 100, 2)

        return CoverageAnalysis(
            prd_stories_tested=tested_stories,
            prd_stories_total=total_stories,
            coverage_percentage=coverage_pct,
            untested_stories=untested_stories
        )

    def _generate_recommendations(self, summary: TestSummary) -> List[str]:
        """
        Generate AI-powered recommendations based on test failures.

        Args:
            summary: Test summary statistics

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        if summary.failed > 0:
            recommendations.append(
                f"⚠️ {summary.failed} test(s) failed. Review error diagnostics below for root cause analysis."
            )

            # Analyze failure patterns
            failure_types = {}
            for result in self.test_results:
                if result.status in [TestStatus.FAILED, TestStatus.ERROR] and result.error:
                    error_type = result.error.type
                    failure_types[error_type] = failure_types.get(error_type, 0) + 1

            # Most common failure type
            if failure_types:
                most_common = max(failure_types.items(), key=lambda x: x[1])
                error_type, count = most_common

                if error_type == ErrorType.ELEMENT_NOT_FOUND:
                    recommendations.append(
                        f"🔍 {count} test(s) failed due to element not found. "
                        "Check if UI selectors changed or if elements are dynamically loaded. "
                        "Review frontend/src components for data-testid attributes."
                    )
                elif error_type == ErrorType.TIMEOUT:
                    recommendations.append(
                        f"⏱️ {count} test(s) failed due to timeout. "
                        "Check if backend services are running (docker-compose ps). "
                        "Verify API response times with backend logs."
                    )
                elif error_type == ErrorType.ASSERTION_FAILED:
                    recommendations.append(
                        f"❌ {count} test(s) failed assertions. "
                        "Expected behavior may have changed. Review test expectations "
                        "and compare with actual application behavior."
                    )
                elif error_type == ErrorType.NAVIGATION_ERROR:
                    recommendations.append(
                        f"🧭 {count} test(s) failed to navigate. "
                        "Verify frontend is running on localhost:3333. "
                        "Check docker logs for frontend service errors."
                    )
                elif error_type == ErrorType.BROWSER_ERROR:
                    recommendations.append(
                        f"🌐 {count} test(s) encountered browser errors. "
                        "Review screenshots and console errors. "
                        "Check for JavaScript errors in browser developer console."
                    )

            # Check for screenshot availability
            screenshots = [r.error.screenshot for r in self.test_results
                          if r.error and r.error.screenshot]
            if screenshots:
                recommendations.append(
                    f"📸 {len(screenshots)} screenshot(s) captured. "
                    f"Review screenshots in e2e/screenshots/ for visual debugging."
                )

        if summary.passed == summary.total_tests and summary.total_tests > 0:
            recommendations.append(
                "✅ All tests passed! Test suite is healthy."
            )

        if summary.skipped > 0:
            recommendations.append(
                f"⏭️ {summary.skipped} test(s) skipped. "
                "Review prerequisites or test conditions that caused skips."
            )

        return recommendations

    def generate_report(self) -> TestReport:
        """
        Generate complete test report.

        Returns:
            TestReport object containing all report data
        """
        if not self.run_start_time or not self.run_end_time:
            raise ValueError("Test run not properly initialized. Call start_run() and end_run().")

        duration = (self.run_end_time - self.run_start_time).total_seconds()

        metadata = TestRunMetadata(
            test_run_id=self.test_run_id or "unknown",
            started_at=self.run_start_time.isoformat(),
            completed_at=self.run_end_time.isoformat(),
            duration_seconds=round(duration, 2),
            trigger=self.trigger,
            environment={
                "frontend_url": "http://localhost:3333",
                "backend_url": "http://localhost:7777",
                "python_version": "3.12+"
            }
        )

        summary = self._generate_summary()
        coverage = self._generate_coverage_analysis()
        recommendations = self._generate_recommendations(summary)

        report = TestReport(
            metadata=metadata,
            summary=summary,
            test_results=self.test_results,
            recommendations=recommendations,
            coverage_analysis=coverage
        )

        logger.info(
            "test_report_generated",
            total_tests=summary.total_tests,
            passed=summary.passed,
            failed=summary.failed,
            pass_rate=summary.pass_rate
        )

        return report

    def write_report(self) -> None:
        """Write test report to JSON file."""
        report = self.generate_report()

        # Convert dataclasses to dicts
        report_dict = {
            "metadata": asdict(report.metadata),
            "summary": asdict(report.summary),
            "test_results": [asdict(r) for r in report.test_results],
            "recommendations": report.recommendations,
            "coverage_analysis": asdict(report.coverage_analysis)
        }

        # Ensure parent directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON with pretty formatting
        with open(self.output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

        logger.info(
            "test_report_written",
            output_path=str(self.output_path),
            size_bytes=self.output_path.stat().st_size
        )

        print(f"\n✅ Test report written to: {self.output_path}")
        print(f"📊 Summary: {report.summary.passed}/{report.summary.total_tests} passed "
              f"({report.summary.pass_rate}% pass rate)")
