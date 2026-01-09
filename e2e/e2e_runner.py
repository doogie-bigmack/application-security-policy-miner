"""
E2ETestRunner - Orchestrates end-to-end test execution.

This module provides the main test runner that:
- Loads test definitions from e2e-tests.json
- Loads PRD stories from prd.json
- Executes tests using ClaudeChromeExecutor
- Captures errors and screenshots on failure
- Generates test-results.json using TestReporter
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from e2e.test_executor import ClaudeChromeExecutor, BrowserError, ElementNotFoundError, NavigationError
from e2e.test_reporter import (
    TestReporter,
    TestStatus,
    ErrorType,
    ErrorDiagnostic,
    TestResult,
)

logger = structlog.get_logger(__name__)


class E2ETestRunner:
    """
    Orchestrates E2E test execution.

    This class loads test definitions, executes them using the browser executor,
    captures results, and generates comprehensive test reports.
    """

    def __init__(
        self,
        test_suite_path: str = "e2e-tests.json",
        prd_path: str = "prd.json",
        output_path: str = "test-results.json",
        max_retries: int = 1,
    ):
        """
        Initialize the E2ETestRunner.

        Args:
            test_suite_path: Path to e2e-tests.json file
            prd_path: Path to prd.json file
            output_path: Path to write test-results.json
            max_retries: Maximum number of retries for flaky tests (default: 1)
        """
        self.test_suite_path = Path(test_suite_path)
        self.prd_path = Path(prd_path)
        self.output_path = Path(output_path)
        self.max_retries = max_retries

        self.test_suites: List[Dict[str, Any]] = []
        self.prd_stories: List[Dict[str, Any]] = []
        self.executor = ClaudeChromeExecutor()
        self.reporter = TestReporter(output_path=str(output_path))

        logger.info(
            "e2e_runner_initialized",
            test_suite_path=str(test_suite_path),
            prd_path=str(prd_path),
            output_path=str(output_path),
            max_retries=max_retries,
        )

    def load_test_suite(self) -> None:
        """Load test suite from e2e-tests.json."""
        try:
            with open(self.test_suite_path, "r") as f:
                data = json.load(f)
                self.test_suites = data.get("test_suites", [])
                logger.info(
                    "test_suite_loaded",
                    num_suites=len(self.test_suites),
                    total_tests=sum(len(suite.get("tests", [])) for suite in self.test_suites),
                )
        except FileNotFoundError:
            logger.error("test_suite_not_found", path=str(self.test_suite_path))
            raise
        except json.JSONDecodeError as e:
            logger.error("test_suite_invalid_json", path=str(self.test_suite_path), error=str(e))
            raise

    def load_prd(self) -> None:
        """Load PRD stories from prd.json."""
        try:
            with open(self.prd_path, "r") as f:
                data = json.load(f)
                self.prd_stories = data.get("stories", [])

                # Extract story IDs for coverage tracking
                prd_story_ids = [story.get("id") for story in self.prd_stories if story.get("id")]
                self.reporter.set_prd_stories(prd_story_ids)

                logger.info(
                    "prd_loaded",
                    num_stories=len(self.prd_stories),
                )
        except FileNotFoundError:
            logger.error("prd_not_found", path=str(self.prd_path))
            raise
        except json.JSONDecodeError as e:
            logger.error("prd_invalid_json", path=str(self.prd_path), error=str(e))
            raise

    def _substitute_env_vars(self, value: str) -> str:
        """
        Substitute environment variables in test values.

        Supports ${VAR_NAME} syntax for environment variable substitution.

        Args:
            value: String potentially containing ${VAR_NAME} patterns

        Returns:
            String with environment variables substituted
        """
        if not isinstance(value, str):
            return value

        # Simple regex-free substitution
        result = value
        start = 0
        while True:
            start_pos = result.find("${", start)
            if start_pos == -1:
                break
            end_pos = result.find("}", start_pos)
            if end_pos == -1:
                break

            var_name = result[start_pos + 2:end_pos]
            env_value = os.environ.get(var_name, f"${{{var_name}}}")
            result = result[:start_pos] + env_value + result[end_pos + 1:]
            start = start_pos + len(env_value)

        return result

    def _execute_test_step(self, step: Dict[str, Any], test_id: str) -> None:
        """
        Execute a single test step.

        Args:
            step: Test step definition
            test_id: ID of the test being executed

        Raises:
            BrowserError: If the step execution fails
        """
        action = step.get("action")
        selector = self._substitute_env_vars(step.get("selector", ""))
        target = self._substitute_env_vars(step.get("target", ""))
        value = self._substitute_env_vars(step.get("value", ""))
        timeout_ms = step.get("timeout_ms", 5000)
        description = step.get("description", "")

        logger.info(
            "executing_step",
            test_id=test_id,
            action=action,
            description=description,
        )

        try:
            if action == "navigate":
                self.executor.navigate(target)
            elif action == "click":
                self.executor.click(selector)
            elif action == "fill":
                self.executor.fill_input(selector, value)
            elif action == "wait_for_element":
                self.executor.wait_for_element(selector, timeout_ms)
            elif action == "assert_element_visible":
                self.executor.assert_visible(selector, timeout_ms)
            elif action == "api_call":
                # API calls for cleanup - skip in main execution
                logger.info("skipping_api_call", description=description)
            else:
                logger.warning("unknown_action", action=action, test_id=test_id)

        except Exception as e:
            logger.error(
                "step_execution_failed",
                test_id=test_id,
                action=action,
                error=str(e),
            )
            raise

    def _execute_test(self, test: Dict[str, Any], suite_id: str) -> Dict[str, Any]:
        """
        Execute a single test.

        Args:
            test: Test definition
            suite_id: ID of the test suite

        Returns:
            Test result dictionary
        """
        test_id = test.get("test_id")
        test_name = test.get("name")
        prd_story_id = test.get("prd_story_id")
        steps = test.get("steps", [])

        logger.info(
            "test_started",
            test_id=test_id,
            test_name=test_name,
            prd_story_id=prd_story_id,
            num_steps=len(steps),
        )

        start_time = datetime.now(timezone.utc)
        status = TestStatus.PASSED
        error_diagnostic = None
        screenshot_path = None
        steps_completed = 0

        try:
            for step_index, step in enumerate(steps):
                steps_completed = step_index
                try:
                    self._execute_test_step(step, test_id)
                    steps_completed = step_index + 1
                except ElementNotFoundError as e:
                    status = TestStatus.FAILED
                    screenshot_path = self.executor.take_screenshot(f"{test_id}_failure")
                    error_diagnostic = ErrorDiagnostic(
                        type=ErrorType.ELEMENT_NOT_FOUND.value,
                        message=str(e),
                        step_index=step_index,
                        step_description=step.get("description", ""),
                        screenshot=screenshot_path,
                        console_errors=[],
                        stack_trace=None,
                    )
                    break
                except NavigationError as e:
                    status = TestStatus.FAILED
                    screenshot_path = self.executor.take_screenshot(f"{test_id}_failure")
                    error_diagnostic = ErrorDiagnostic(
                        type=ErrorType.NAVIGATION_ERROR.value,
                        message=str(e),
                        step_index=step_index,
                        step_description=step.get("description", ""),
                        screenshot=screenshot_path,
                        console_errors=[],
                        stack_trace=None,
                    )
                    break
                except BrowserError as e:
                    status = TestStatus.FAILED
                    screenshot_path = self.executor.take_screenshot(f"{test_id}_failure")
                    error_diagnostic = ErrorDiagnostic(
                        type=ErrorType.BROWSER_ERROR.value,
                        message=str(e),
                        step_index=step_index,
                        step_description=step.get("description", ""),
                        screenshot=screenshot_path,
                        console_errors=[],
                        stack_trace=None,
                    )
                    break
                except Exception as e:
                    status = TestStatus.ERROR
                    screenshot_path = self.executor.take_screenshot(f"{test_id}_error")
                    error_diagnostic = ErrorDiagnostic(
                        type=ErrorType.UNKNOWN.value,
                        message=str(e),
                        step_index=step_index,
                        step_description=step.get("description", ""),
                        screenshot=screenshot_path,
                        console_errors=[],
                        stack_trace=None,
                    )
                    break

        except Exception as e:
            status = TestStatus.ERROR
            screenshot_path = self.executor.take_screenshot(f"{test_id}_error")
            error_diagnostic = ErrorDiagnostic(
                type=ErrorType.UNKNOWN.value,
                message=str(e),
                step_index=0,
                step_description="Test execution failed",
                screenshot=screenshot_path,
                console_errors=[],
                stack_trace=None,
            )

        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(
            "test_completed",
            test_id=test_id,
            status=status.value,
            duration_seconds=duration_seconds,
        )

        return {
            "test_id": test_id,
            "test_name": test_name,
            "prd_story_id": prd_story_id,
            "status": status,
            "duration_seconds": duration_seconds,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "steps_completed": steps_completed,
            "steps_total": len(steps),
            "error": error_diagnostic,
            "screenshot": screenshot_path,
        }

    def run_tests(
        self,
        filter_priority: Optional[str] = None,
        filter_story_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Run all tests matching the filters.

        Args:
            filter_priority: Only run tests with this priority (e.g., "critical")
            filter_story_ids: Only run tests for these PRD story IDs
        """
        logger.info(
            "test_run_started",
            filter_priority=filter_priority,
            filter_story_ids=filter_story_ids,
        )

        # Generate test run ID
        import uuid
        test_run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.reporter.start_run(test_run_id=test_run_id, trigger="manual")

        # Collect all tests to run
        tests_to_run = []
        for suite in self.test_suites:
            suite_id = suite.get("suite_id")
            for test in suite.get("tests", []):
                # Apply filters
                if filter_priority and test.get("priority") != filter_priority:
                    continue
                if filter_story_ids and test.get("prd_story_id") not in filter_story_ids:
                    continue

                tests_to_run.append((suite_id, test))

        logger.info("tests_filtered", total_tests=len(tests_to_run))

        # Execute tests
        for suite_id, test in tests_to_run:
            test_id = test.get("test_id")

            # Retry logic for flaky tests
            for attempt in range(self.max_retries + 1):
                if attempt > 0:
                    logger.info("retrying_test", test_id=test_id, attempt=attempt)

                result = self._execute_test(test, suite_id)

                # Add result to reporter
                test_result = TestResult(
                    test_id=result["test_id"],
                    test_name=result["test_name"],
                    prd_story_id=result["prd_story_id"],
                    status=result["status"].value,  # Convert enum to string
                    duration_seconds=result["duration_seconds"],
                    started_at=result["started_at"],
                    completed_at=result["completed_at"],
                    steps_completed=result["steps_completed"],
                    steps_total=result["steps_total"],
                    error=result["error"],
                )
                self.reporter.add_test_result(test_result)

                # If test passed or we're out of retries, break
                if result["status"] == TestStatus.PASSED or attempt == self.max_retries:
                    break

        self.reporter.end_run()

        # Generate and write report
        report = self.reporter.generate_report()
        self.reporter.write_report()

        logger.info(
            "test_run_completed",
            total_tests=report.summary.total_tests,
            passed=report.summary.passed,
            failed=report.summary.failed,
            pass_rate=report.summary.pass_rate,
        )


def main() -> int:
    """
    Main entry point for E2E test runner CLI.

    Returns:
        Exit code (0 if all tests pass, 1 if any fail)
    """
    parser = argparse.ArgumentParser(
        description="Run E2E tests for Policy Miner application"
    )
    parser.add_argument(
        "--test-suite",
        default="e2e-tests.json",
        help="Path to test suite JSON file (default: e2e-tests.json)",
    )
    parser.add_argument(
        "--prd",
        default="prd.json",
        help="Path to PRD JSON file (default: prd.json)",
    )
    parser.add_argument(
        "--output",
        default="test-results.json",
        help="Path to write test results (default: test-results.json)",
    )
    parser.add_argument(
        "--filter-priority",
        choices=["critical", "high", "medium", "low"],
        help="Only run tests with this priority",
    )
    parser.add_argument(
        "--filter-story-id",
        action="append",
        help="Only run tests for this PRD story ID (can be specified multiple times)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Maximum number of retries for flaky tests (default: 1)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        )

    # Create runner and execute tests
    runner = E2ETestRunner(
        test_suite_path=args.test_suite,
        prd_path=args.prd,
        output_path=args.output,
        max_retries=args.max_retries,
    )

    try:
        runner.load_test_suite()
        runner.load_prd()
        runner.run_tests(
            filter_priority=args.filter_priority,
            filter_story_ids=args.filter_story_id,
        )

        # Read results and determine exit code
        with open(args.output, "r") as f:
            results = json.load(f)
            summary = results.get("summary", {})
            failed = summary.get("failed", 0)

            if failed > 0:
                print(f"\n❌ {failed} test(s) failed")
                return 1
            else:
                print("\n✅ All tests passed!")
                return 0

    except Exception as e:
        logger.error("test_run_failed", error=str(e))
        print(f"\n❌ Test run failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
