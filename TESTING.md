# Testing Guide

This guide covers end-to-end testing for the Policy Miner application.

## Table of Contents

- [Quick Start](#quick-start)
- [Running E2E Tests Manually](#running-e2e-tests-manually)
- [Understanding Test Results](#understanding-test-results)
- [Debugging Failed Tests](#debugging-failed-tests)
- [Writing New Test Scenarios](#writing-new-test-scenarios)
- [Troubleshooting](#troubleshooting)

## Quick Start

```bash
# Start Docker services
make docker-up

# Run E2E tests
make e2e

# View status
make status
```

## Running E2E Tests Manually

### Prerequisites

1. **Docker services running**: All services must be healthy
   ```bash
   make docker-up
   ```

2. **E2E virtual environment**: Created automatically by `make e2e`
   ```bash
   cd e2e
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

### Running All Tests

Run all E2E tests with default settings:

```bash
make e2e
```

Or directly with the Python module:

```bash
e2e/.venv/bin/python3 -m e2e.e2e_runner \
  --test-suite e2e-tests.json \
  --prd prd.json \
  --output test-results.json
```

**Expected Output:**
```
2026-01-09 11:28:51 [info] e2e_runner_initialized
2026-01-09 11:28:51 [info] test_suite_loaded num_suites=3 total_tests=5
2026-01-09 11:28:51 [info] test_run_started
...
✅ Test report written to: test-results.json
📊 Summary: 5/5 passed (100.0% pass rate)
✅ All tests passed!
```

### Command Line Options

```bash
e2e/.venv/bin/python3 -m e2e.e2e_runner [OPTIONS]
```

**Options:**

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--test-suite` | Path to e2e-tests.json | `e2e-tests.json` | `--test-suite tests/custom.json` |
| `--prd` | Path to prd.json | `prd.json` | `--prd docs/requirements.json` |
| `--output` | Path to test-results.json | `test-results.json` | `--output results/run1.json` |
| `--filter-priority` | Only run tests with priority | None | `--filter-priority critical` |
| `--filter-story-id` | Only run tests for story IDs | None | `--filter-story-id FUNC-001 --filter-story-id AI-001` |
| `--max-retries` | Retry attempts for flaky tests | `1` | `--max-retries 3` |
| `--verbose` / `-v` | Enable verbose logging | False | `-v` |

### Filtering Tests

**Run only critical priority tests:**
```bash
e2e/.venv/bin/python3 -m e2e.e2e_runner \
  --filter-priority critical
```

**Run tests for specific PRD stories:**
```bash
e2e/.venv/bin/python3 -m e2e.e2e_runner \
  --filter-story-id FUNC-001 \
  --filter-story-id AI-001
```

**Run with verbose logging:**
```bash
e2e/.venv/bin/python3 -m e2e.e2e_runner -v
```

### Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed

## Understanding Test Results

After running tests, results are saved to `test-results.json`.

### test-results.json Schema

```json
{
  "metadata": {
    "test_run_id": "run_20260109_172851_3c96f7b6",
    "started_at": "2026-01-09T17:28:51.647923+00:00",
    "completed_at": "2026-01-09T17:28:51.650495+00:00",
    "duration_seconds": 0.0,
    "trigger": "manual",
    "environment": {
      "frontend_url": "http://localhost:3333",
      "backend_url": "http://localhost:7777",
      "python_version": "3.12+"
    }
  },
  "summary": {
    "total_tests": 5,
    "passed": 5,
    "failed": 0,
    "skipped": 0,
    "error": 0,
    "pass_rate": 100.0
  },
  "test_results": [
    {
      "test_id": "test_add_github_repository",
      "test_name": "Add GitHub Repository",
      "prd_story_id": "FUNC-001",
      "status": "passed",
      "duration_seconds": 0.000469,
      "started_at": "2026-01-09T17:28:51.647982+00:00",
      "completed_at": "2026-01-09T17:28:51.648451+00:00",
      "steps_completed": 12,
      "steps_total": 12,
      "error": null
    }
  ],
  "recommendations": [
    "✅ All tests passed! Test suite is healthy."
  ],
  "coverage_analysis": {
    "prd_stories_tested": ["FUNC-001", "AI-001", "UI-001", "PROV-001", "PROV-002"],
    "prd_stories_total": 5,
    "coverage_percentage": 100.0,
    "untested_stories": []
  }
}
```

### Key Sections

#### 1. metadata
- `test_run_id`: Unique identifier for this test run
- `started_at` / `completed_at`: ISO 8601 timestamps
- `duration_seconds`: Total test execution time
- `trigger`: How tests were triggered (`manual`, `ci`, `scheduled`)
- `environment`: URLs and versions

#### 2. summary
- `total_tests`: Number of tests executed
- `passed` / `failed` / `skipped` / `error`: Test counts by status
- `pass_rate`: Percentage of tests that passed

#### 3. test_results
Array of individual test outcomes:
- `test_id`: Unique test identifier
- `test_name`: Human-readable test name
- `prd_story_id`: Maps to PRD story (e.g., FUNC-001)
- `status`: `passed`, `failed`, `skipped`, or `error`
- `duration_seconds`: Test execution time
- `steps_completed` / `steps_total`: Progress through test steps
- `error`: Null if passed, or ErrorDiagnostic object if failed

#### 4. recommendations
AI-generated recommendations based on failure patterns:
- Element not found → Check UI selectors
- Timeout → Check backend services
- Assertion failed → Review test expectations

#### 5. coverage_analysis
- `prd_stories_tested`: Which PRD stories have test coverage
- `coverage_percentage`: Percentage of PRD stories tested
- `untested_stories`: PRD stories without tests

### Viewing Results with make status

```bash
make status
```

**Output:**
```
==========================================
📊 Policy Miner Status
==========================================

🐳 Docker Services:
  7/7 running and healthy

📋 Product Features (prd.json):
  Total: 78
  Completed: 57 (73%)
  Remaining: 21

🧪 Test Infrastructure (test-prd.json):
  Total: 14
  Completed: 13 (92%)
  Remaining: 1

📊 Latest E2E Test Results:
  Passed: 5
  Failed: 0
  Pass Rate: 100.0%
```

## Debugging Failed Tests

When tests fail, the test runner captures diagnostics to help you debug.

### Error Diagnostics Structure

Failed tests include an `error` object with detailed diagnostics:

```json
{
  "test_id": "test_add_github_repository",
  "status": "failed",
  "error": {
    "type": "element_not_found",
    "message": "Element not found: button[data-testid='add-repository-btn']",
    "step_index": 1,
    "step_description": "Click the Add Repository button",
    "screenshot": "e2e/screenshots/test_add_github_repository_20260109_172851_failure.png",
    "console_errors": [
      "TypeError: Cannot read property 'map' of undefined",
      "Failed to load resource: the server responded with a status of 500"
    ],
    "stack_trace": "Traceback (most recent call last):\n  File \"e2e/test_executor.py\", line 45, in click\n    raise ElementNotFoundError(selector)"
  }
}
```

### Error Types

| Error Type | Description | Common Causes |
|------------|-------------|---------------|
| `element_not_found` | Element selector didn't match any elements | Wrong selector, page not loaded, element hidden |
| `timeout` | Operation exceeded timeout | Slow backend, network issues, infinite loading |
| `assertion_failed` | Assertion did not pass | Wrong expected value, UI change, data issue |
| `navigation_error` | Failed to navigate to URL | Service down, wrong URL, network issue |
| `browser_error` | Browser/JavaScript error | JS exception, render error, missing dependency |
| `form_fill_error` | Failed to fill form input | Wrong selector, input disabled, validation issue |
| `unknown_error` | Unexpected error | See stack_trace for details |

### Using Screenshots

Failed tests automatically capture screenshots to `e2e/screenshots/`:

```bash
# List screenshots
ls -la e2e/screenshots/

# View screenshot (macOS)
open e2e/screenshots/test_add_github_repository_20260109_172851_failure.png
```

**Screenshot naming pattern:**
```
{test_id}_{timestamp}_failure.png
```

### Step-by-Step Debugging

1. **Check the error type and message**
   ```bash
   cat test-results.json | jq '.test_results[] | select(.status == "failed") | .error'
   ```

2. **Review the screenshot**
   ```bash
   open e2e/screenshots/*.png
   ```

3. **Check console errors**
   ```bash
   cat test-results.json | jq '.test_results[] | select(.status == "failed") | .error.console_errors'
   ```

4. **Review recommendations**
   ```bash
   cat test-results.json | jq '.recommendations'
   ```

5. **Re-run with verbose logging**
   ```bash
   e2e/.venv/bin/python3 -m e2e.e2e_runner -v
   ```

### Common Debugging Scenarios

#### Scenario: Element Not Found

**Error:**
```json
{
  "type": "element_not_found",
  "message": "Element not found: button[data-testid='add-repository-btn']"
}
```

**Debugging Steps:**
1. Check if the frontend is running: `curl http://localhost:3333`
2. View the screenshot to see actual page state
3. Verify the selector in browser DevTools: `document.querySelector("button[data-testid='add-repository-btn']")`
4. Check if element is hidden or disabled

#### Scenario: Timeout

**Error:**
```json
{
  "type": "timeout",
  "message": "Timeout waiting for element: [data-testid='scan-status'][data-status='completed']"
}
```

**Debugging Steps:**
1. Check backend logs: `docker-compose logs backend`
2. Verify backend is responsive: `curl http://localhost:7777/health`
3. Increase timeout in e2e-tests.json for slow operations
4. Check if operation actually completes manually

#### Scenario: Assertion Failed

**Error:**
```json
{
  "type": "assertion_failed",
  "message": "Expected element to be visible: [data-testid='repository-list']"
}
```

**Debugging Steps:**
1. Review screenshot to see actual UI state
2. Check if element exists but is hidden: `display: none` or `visibility: hidden`
3. Verify test expectations match actual behavior
4. Check for recent UI changes

## Writing New Test Scenarios

### e2e-tests.json Schema

Tests are defined in `e2e-tests.json` using this schema:

```json
{
  "schema_version": "1.0",
  "description": "E2E test suite for Policy Miner",
  "test_suites": [
    {
      "suite_id": "repository_management",
      "name": "Repository Management Tests",
      "description": "Tests for adding, scanning, and managing repositories",
      "tests": [
        {
          "test_id": "test_add_github_repository",
          "prd_story_id": "FUNC-001",
          "name": "Add GitHub Repository",
          "priority": "critical",
          "description": "Test adding a GitHub repository",
          "prerequisites": {
            "services": ["frontend", "backend", "postgres"],
            "test_data": {
              "github_token": "GITHUB_TEST_TOKEN",
              "repository_url": "https://github.com/test-org/test-repo"
            }
          },
          "steps": [
            {
              "action": "navigate",
              "target": "http://localhost:3333/repositories",
              "description": "Navigate to repositories page"
            },
            {
              "action": "wait_for_element",
              "selector": "button[data-testid='add-repository-btn']",
              "timeout_ms": 5000,
              "description": "Wait for button to be visible"
            },
            {
              "action": "click",
              "selector": "button[data-testid='add-repository-btn']",
              "description": "Click the Add Repository button"
            },
            {
              "action": "fill",
              "selector": "input[name='github_token']",
              "value": "${GITHUB_TEST_TOKEN}",
              "description": "Fill in GitHub token"
            },
            {
              "action": "assert_element_visible",
              "selector": "[data-testid='success-message']",
              "timeout_ms": 10000,
              "description": "Verify success message"
            }
          ],
          "expected_outcomes": [
            "Repository appears in list",
            "Success message displayed",
            "Repository status shows 'connected'"
          ],
          "cleanup": [
            {
              "action": "navigate",
              "target": "http://localhost:3333/repositories"
            },
            {
              "action": "click",
              "selector": "[data-repository-name='test-repo'] button[data-testid='delete-btn']"
            }
          ]
        }
      ]
    }
  ]
}
```

### Supported Actions

| Action | Required Fields | Optional Fields | Description |
|--------|----------------|-----------------|-------------|
| `navigate` | `target` | - | Navigate to URL |
| `click` | `selector` | - | Click element |
| `fill` | `selector`, `value` | - | Fill form input |
| `wait_for_element` | `selector` | `timeout_ms` | Wait for element to appear |
| `assert_element_visible` | `selector` | `timeout_ms` | Assert element is visible |

### Environment Variables

Use `${VAR_NAME}` syntax to reference environment variables:

```json
{
  "action": "fill",
  "selector": "input[name='api_key']",
  "value": "${API_KEY}"
}
```

Set environment variables before running tests:

```bash
export GITHUB_TEST_TOKEN="ghp_test_token_here"
export API_KEY="test_api_key_here"
make e2e
```

### Test Priorities

Tests can have 4 priority levels:
- `critical`: Must pass for every deploy (run first)
- `high`: Important functionality (run frequently)
- `medium`: Standard features (run regularly)
- `low`: Nice-to-have checks (run periodically)

### Example: Adding a New Test

Let's add a test for filtering policies by resource:

```json
{
  "test_id": "test_filter_policies_by_resource",
  "prd_story_id": "UI-002",
  "name": "Filter Policies by Resource",
  "priority": "high",
  "description": "Test filtering policies by resource name",
  "prerequisites": {
    "services": ["frontend", "backend", "postgres"],
    "test_data": {
      "existing_policies": "At least 5 policies with different resources"
    }
  },
  "steps": [
    {
      "action": "navigate",
      "target": "http://localhost:3333/policies",
      "description": "Navigate to policies page"
    },
    {
      "action": "wait_for_element",
      "selector": "[data-testid='policies-table']",
      "timeout_ms": 5000,
      "description": "Wait for policies table"
    },
    {
      "action": "fill",
      "selector": "input[data-testid='filter-resource']",
      "value": "database",
      "description": "Filter by resource 'database'"
    },
    {
      "action": "wait_for_element",
      "selector": "[data-testid='policy-row']",
      "timeout_ms": 3000,
      "description": "Wait for filtered results"
    },
    {
      "action": "assert_element_visible",
      "selector": "[data-resource='database']",
      "timeout_ms": 5000,
      "description": "Verify filtered policies shown"
    }
  ],
  "expected_outcomes": [
    "Policies filtered to show only 'database' resources",
    "Filter input shows 'database'",
    "Table updates with filtered results"
  ],
  "cleanup": []
}
```

### Using Reusable Scenarios

For common flows, use the scenario modules in `e2e/scenarios/`:

```python
from e2e.scenarios.repository_crud import add_github_repository, scan_repository
from e2e.scenarios.policy_viewing import view_policies, filter_policies_by_subject
from e2e.scenarios.provisioning_flow import add_pbac_provider, provision_policy

# Add a repository
repo_id = add_github_repository(
    executor,
    token="ghp_test_token",
    repo_url="https://github.com/test-org/test-repo"
)

# Scan the repository
scan_results = scan_repository(executor, repo_id)

# View and filter policies
view_policies(executor, filter_subject="admin")

# Add PBAC provider
provider_id = add_pbac_provider(
    executor,
    provider_type="opa",
    name="Test OPA Instance",
    endpoint="http://localhost:8181"
)

# Provision policy
provision_policy(executor, policy_id="pol_123", provider_id=provider_id)
```

## Troubleshooting

### Common Issues

#### Issue: ModuleNotFoundError: No module named 'structlog'

**Solution:** Install E2E dependencies in virtual environment
```bash
cd e2e
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Or use `make e2e` which automatically creates the venv.

#### Issue: Connection refused to localhost:3333

**Solution:** Start Docker services
```bash
make docker-up

# Wait for services to be healthy
docker-compose ps
```

#### Issue: Tests pass locally but fail in CI

**Potential causes:**
1. Missing environment variables
2. Different service URLs
3. Timing issues (increase timeouts)
4. Docker networking differences

**Solution:** Check CI logs and compare environment:
```bash
# Check CI environment
env | grep -E "(FRONTEND|BACKEND|GITHUB)"

# Increase timeouts for CI
e2e/.venv/bin/python3 -m e2e.e2e_runner --max-retries 3
```

#### Issue: Screenshots not captured on failure

**Solution:** Ensure screenshots directory exists
```bash
mkdir -p e2e/screenshots
chmod 755 e2e/screenshots
```

#### Issue: Tests hang indefinitely

**Potential causes:**
1. Backend service unresponsive
2. Frontend not rendering
3. Infinite loading state
4. Network timeout

**Solution:** Check service logs and reduce timeouts:
```bash
docker-compose logs backend
docker-compose logs frontend

# Check service health
curl http://localhost:3333
curl http://localhost:7777/health
```

### Getting Help

1. **Check test-results.json**: Review error messages and recommendations
2. **View screenshots**: Visual debugging in `e2e/screenshots/`
3. **Check logs**: `docker-compose logs [service]`
4. **Run with verbose logging**: `e2e/.venv/bin/python3 -m e2e.e2e_runner -v`
5. **Review test-progress.txt**: See recent test infrastructure changes

### Reporting Issues

When reporting test failures, include:
1. test-results.json (full file or relevant test_results entry)
2. Screenshot (if available)
3. Docker service status: `docker-compose ps`
4. Service logs: `docker-compose logs backend frontend`
5. Steps to reproduce

---

## Additional Resources

- **prd.json**: Product requirements and feature definitions
- **test-prd.json**: Test infrastructure requirements
- **e2e-tests.json**: Test definitions
- **test-results.json**: Latest test results
- **progress.txt**: Product development progress
- **test-progress.txt**: Test infrastructure progress

## Quick Reference

```bash
# Start services
make docker-up

# Run all tests
make e2e

# Run critical tests only
e2e/.venv/bin/python3 -m e2e.e2e_runner --filter-priority critical

# Run tests for specific story
e2e/.venv/bin/python3 -m e2e.e2e_runner --filter-story-id FUNC-001

# Run with retries
e2e/.venv/bin/python3 -m e2e.e2e_runner --max-retries 3

# View status
make status

# View test results
cat test-results.json | jq '.summary'

# Check failed tests
cat test-results.json | jq '.test_results[] | select(.status == "failed")'

# View recommendations
cat test-results.json | jq '.recommendations'

# Clean screenshots
rm -f e2e/screenshots/*.png
```
