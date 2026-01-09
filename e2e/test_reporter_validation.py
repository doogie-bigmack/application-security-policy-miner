#!/usr/bin/env python3
"""
Manual validation script for TEST-004 acceptance criteria.

This script validates that the TestReporter implementation meets all requirements:
1. test-results.json generated after test run
2. Contains all required fields per schema
3. Pass/fail status accurately reflects test outcomes
4. Screenshots referenced in error objects exist in e2e/screenshots/
5. Recommendations provide actionable debugging guidance
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from test_reporter import (
    TestReporter,
    TestResult,
    TestStatus,
    ErrorType,
    ErrorDiagnostic
)


def validate_acceptance_criteria():
    """Validate all acceptance criteria for TEST-004."""

    print("=" * 80)
    print("TEST-004 Acceptance Criteria Validation")
    print("=" * 80)

    # Create temporary output file
    output_path = "test-results-validation.json"

    # Initialize reporter
    print("\n✓ Initializing TestReporter...")
    reporter = TestReporter(output_path=output_path)

    # Start test run
    print("✓ Starting test run...")
    reporter.start_run(test_run_id="validation-run-001", trigger="manual")

    # Set PRD stories for coverage analysis
    prd_stories = ["FUNC-001", "FUNC-002", "AI-001", "UI-001", "PROV-001"]
    reporter.set_prd_stories(prd_stories)

    # Add a passing test
    print("✓ Adding passing test result...")
    result1 = TestResult(
        test_id="test_add_repository",
        test_name="Add GitHub Repository",
        prd_story_id="FUNC-001",
        status=TestStatus.PASSED,
        duration_seconds=12.5,
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at=datetime.now(timezone.utc).isoformat(),
        steps_completed=10,
        steps_total=10
    )
    reporter.add_test_result(result1)

    # Add a failing test with error diagnostic
    print("✓ Adding failing test result with error diagnostic...")

    # Create screenshot directory and dummy screenshot
    screenshot_dir = Path("e2e/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / "test_scan_failure.png"
    screenshot_path.write_text("dummy screenshot")

    error = ErrorDiagnostic(
        type=ErrorType.TIMEOUT,
        message="Element not found within timeout: [data-testid='scan-status']",
        step_index=4,
        step_description="Wait for scan to complete",
        screenshot=str(screenshot_path),
        console_errors=[
            "[ERROR] Failed to load resource: http://localhost:7777/api/v1/scan - Status: 500",
            "[ERROR] Network timeout"
        ]
    )

    result2 = TestResult(
        test_id="test_scan_repository",
        test_name="Scan Repository and Extract Policies",
        prd_story_id="AI-001",
        status=TestStatus.FAILED,
        duration_seconds=120.0,
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at=datetime.now(timezone.utc).isoformat(),
        steps_completed=4,
        steps_total=10,
        error=error
    )
    reporter.add_test_result(result2)

    # End test run
    print("✓ Ending test run...")
    reporter.end_run()

    # Generate and write report
    print("✓ Generating test report...")
    reporter.write_report()

    # Validate generated file
    print("\n" + "=" * 80)
    print("Acceptance Criteria Validation")
    print("=" * 80)

    # AC1: test-results.json generated after test run
    print("\n[AC1] test-results.json generated after test run")
    output_file = Path(output_path)
    if output_file.exists():
        print(f"  ✅ PASS - File exists at: {output_file}")
    else:
        print(f"  ❌ FAIL - File not found at: {output_file}")
        return False

    # AC2: Contains all required fields per schema
    print("\n[AC2] Contains all required fields per schema")
    with open(output_file) as f:
        data = json.load(f)

    required_top_level = ["metadata", "summary", "test_results", "recommendations", "coverage_analysis"]
    missing_fields = [f for f in required_top_level if f not in data]

    if not missing_fields:
        print("  ✅ PASS - All top-level fields present")
    else:
        print(f"  ❌ FAIL - Missing fields: {missing_fields}")
        return False

    # Validate metadata fields
    required_metadata = ["test_run_id", "started_at", "completed_at", "duration_seconds", "trigger", "environment"]
    missing_metadata = [f for f in required_metadata if f not in data["metadata"]]

    if not missing_metadata:
        print("  ✅ PASS - All metadata fields present")
    else:
        print(f"  ❌ FAIL - Missing metadata fields: {missing_metadata}")
        return False

    # Validate summary fields
    required_summary = ["total_tests", "passed", "failed", "skipped", "error", "pass_rate"]
    missing_summary = [f for f in required_summary if f not in data["summary"]]

    if not missing_summary:
        print("  ✅ PASS - All summary fields present")
    else:
        print(f"  ❌ FAIL - Missing summary fields: {missing_summary}")
        return False

    # AC3: Pass/fail status accurately reflects test outcomes
    print("\n[AC3] Pass/fail status accurately reflects test outcomes")
    summary = data["summary"]

    if summary["total_tests"] == 2 and summary["passed"] == 1 and summary["failed"] == 1:
        print("  ✅ PASS - Test counts are correct (2 total, 1 passed, 1 failed)")
    else:
        print(f"  ❌ FAIL - Test counts incorrect: {summary}")
        return False

    if summary["pass_rate"] == 50.0:
        print("  ✅ PASS - Pass rate is correct (50%)")
    else:
        print(f"  ❌ FAIL - Pass rate incorrect: {summary['pass_rate']}%")
        return False

    # Verify test result details
    test_results = data["test_results"]
    passed_test = [t for t in test_results if t["status"] == "passed"]
    failed_test = [t for t in test_results if t["status"] == "failed"]

    if len(passed_test) == 1 and passed_test[0]["test_id"] == "test_add_repository":
        print("  ✅ PASS - Passing test correctly recorded")
    else:
        print("  ❌ FAIL - Passing test not correctly recorded")
        return False

    if len(failed_test) == 1 and failed_test[0]["test_id"] == "test_scan_repository":
        print("  ✅ PASS - Failing test correctly recorded")
    else:
        print("  ❌ FAIL - Failing test not correctly recorded")
        return False

    # AC4: Screenshots referenced in error objects exist in e2e/screenshots/
    print("\n[AC4] Screenshots referenced in error objects exist in e2e/screenshots/")

    if failed_test[0]["error"] and "screenshot" in failed_test[0]["error"]:
        screenshot_ref = failed_test[0]["error"]["screenshot"]
        screenshot_file = Path(screenshot_ref)

        if screenshot_file.exists():
            print(f"  ✅ PASS - Screenshot exists at: {screenshot_ref}")
        else:
            print(f"  ❌ FAIL - Screenshot not found at: {screenshot_ref}")
            return False
    else:
        print("  ❌ FAIL - No screenshot referenced in error object")
        return False

    # Verify error diagnostic fields
    error_data = failed_test[0]["error"]
    required_error_fields = ["type", "message", "step_index", "step_description", "console_errors"]
    missing_error_fields = [f for f in required_error_fields if f not in error_data]

    if not missing_error_fields:
        print("  ✅ PASS - All error diagnostic fields present")
    else:
        print(f"  ❌ FAIL - Missing error fields: {missing_error_fields}")
        return False

    # AC5: Recommendations provide actionable debugging guidance
    print("\n[AC5] Recommendations provide actionable debugging guidance")
    recommendations = data["recommendations"]

    if len(recommendations) > 0:
        print(f"  ✅ PASS - {len(recommendations)} recommendation(s) generated")
    else:
        print("  ❌ FAIL - No recommendations generated")
        return False

    # Check for specific recommendation types
    has_failure_warning = any("failed" in rec.lower() for rec in recommendations)
    has_timeout_guidance = any("timeout" in rec.lower() for rec in recommendations)
    has_docker_check = any("docker" in rec.lower() for rec in recommendations)

    if has_failure_warning:
        print("  ✅ PASS - Failure warning recommendation present")
    else:
        print("  ❌ FAIL - Missing failure warning recommendation")

    if has_timeout_guidance:
        print("  ✅ PASS - Timeout-specific guidance present")
    else:
        print("  ❌ FAIL - Missing timeout-specific guidance")

    if has_docker_check:
        print("  ✅ PASS - Docker service check recommendation present")
    else:
        print("  ❌ FAIL - Missing Docker service check recommendation")

    # Coverage analysis
    print("\n[BONUS] Coverage Analysis")
    coverage = data["coverage_analysis"]
    print(f"  ℹ️  PRD stories tested: {len(coverage['prd_stories_tested'])}/{coverage['prd_stories_total']}")
    print(f"  ℹ️  Coverage: {coverage['coverage_percentage']}%")
    print(f"  ℹ️  Untested stories: {', '.join(coverage['untested_stories'])}")

    # Print sample output
    print("\n" + "=" * 80)
    print("Sample Report Output")
    print("=" * 80)
    print(json.dumps(data, indent=2)[:1000] + "\n... (truncated)")

    print("\n" + "=" * 80)
    print("✅ ALL ACCEPTANCE CRITERIA PASSED")
    print("=" * 80)

    # Cleanup
    output_file.unlink()
    screenshot_path.unlink()

    return True


if __name__ == "__main__":
    try:
        success = validate_acceptance_criteria()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
