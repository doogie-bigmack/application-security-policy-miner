# E2E Testing Infrastructure

This directory contains the end-to-end (E2E) testing infrastructure for the Policy Miner application.

## Directory Structure

```
e2e/
├── __init__.py              # Package initialization
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── test_executor.py        # ClaudeChromeExecutor wrapper (TEST-002)
├── test_reporter.py        # TestReporter for results (TEST-004)
├── e2e_runner.py          # E2ETestRunner orchestrator (TEST-005)
├── scenarios/             # Reusable test scenarios (TEST-007 to TEST-011)
│   ├── __init__.py
│   ├── repository_crud.py
│   ├── policy_viewing.py
│   └── provisioning_flow.py
└── screenshots/           # Screenshots captured on test failures
```

## Dependencies

- Python 3.12+
- Claude Chrome MCP integration (via Anthropic SDK)
- Docker services running (backend at localhost:7777, frontend at localhost:3333)

## Installation

```bash
pip install -r e2e/requirements.txt
```

System dependencies:
- `jq` command-line tool (for JSON processing)

Install jq:
- macOS: `brew install jq`
- Ubuntu/Debian: `apt-get install jq`
- Other: https://jqlang.github.io/jq/download/

## Test Definitions

Test scenarios are defined in `e2e-tests.json` at the project root. Each test maps to a product feature story in `prd.json`.

## Test Results

Test results are generated in `test-results.json` after each test run, containing:
- Summary statistics (pass/fail counts, duration)
- Detailed test results with error diagnostics
- Screenshots for failed tests
- AI-powered recommendations for fixing failures

## Running Tests

See `TESTING.md` in the project root for detailed usage instructions.

Quick start:
```bash
# Run all tests
python3 e2e/e2e_runner.py --test-suite e2e-tests.json --prd prd.json

# Run specific priority tests
python3 e2e/e2e_runner.py --test-suite e2e-tests.json --prd prd.json --filter-priority critical

# Run tests for specific story
python3 e2e/e2e_runner.py --test-suite e2e-tests.json --prd prd.json --filter-story-id FUNC-001
```

## Writing New Tests

1. Add test definition to `e2e-tests.json`
2. Map test to a `prd.json` story ID
3. Define test steps using available actions:
   - `navigate`: Navigate to URL
   - `click`: Click element by selector
   - `fill`: Fill input field
   - `wait_for_element`: Wait for element to appear
   - `assert_element_visible`: Assert element is visible
4. Add expected outcomes and cleanup steps

## Architecture

### ClaudeChromeExecutor (test_executor.py)
Wraps Claude Chrome MCP tools for browser automation:
- Navigate, click, fill inputs, take screenshots
- Element visibility assertions with timeout
- Error handling and retry logic

### E2ETestRunner (e2e_runner.py)
Orchestrates test execution:
- Loads test suite and PRD
- Executes tests using ClaudeChromeExecutor
- Captures screenshots on failures
- Generates test results

### TestReporter (test_reporter.py)
Generates test-results.json:
- Summary statistics
- Detailed error diagnostics
- AI-powered failure analysis
- Coverage analysis against PRD stories

### Test Scenarios (scenarios/)
Reusable test functions for common flows:
- Repository CRUD operations
- Policy viewing and filtering
- PBAC provider management
- Policy provisioning

## Development

This infrastructure is built and maintained by the autonomous test infrastructure loop (`damonnator_infra.sh`), separate from product feature development.
