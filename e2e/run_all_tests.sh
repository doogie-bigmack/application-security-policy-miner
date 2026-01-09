#!/usr/bin/env bash

#
# run_all_tests.sh
# Master E2E test runner - executes all tests in sequence
#
# This script runs all 5 E2E tests using Claude-driven browser automation
# and reports overall test suite results.
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_RUNNER="$SCRIPT_DIR/claude_test_runner.sh"
TEST_RESULTS_FILE="$PROJECT_ROOT/test-results.json"

# Test IDs to run (in order)
TESTS=(
    "test_add_github_repository"
    "test_scan_repository"
    "test_view_policies"
    "test_add_pbac_provider"
    "test_provision_policy"
)

# Counters
TOTAL_TESTS=${#TESTS[@]}
PASSED_COUNT=0
FAILED_COUNT=0
FAILED_TESTS=()

# Banner
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Policy Miner E2E Test Suite - Master Runner          ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check if TEST_MODE is set
if [ "${TEST_MODE:-}" != "true" ]; then
    echo -e "${YELLOW}Warning: TEST_MODE is not set to 'true'${NC}"
    echo -e "${YELLOW}Tests will make real API calls and may take longer.${NC}"
    echo -e "${YELLOW}Recommend: export TEST_MODE=true${NC}"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Check Docker services
echo -e "${BLUE}Checking Docker services...${NC}"
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}Warning: Docker services may not be running${NC}"
    echo "Run: docker-compose up -d"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Check if frontend is accessible
if ! curl -s http://localhost:3333 > /dev/null 2>&1; then
    echo -e "${RED}Error: Frontend service not accessible at http://localhost:3333${NC}"
    echo "Ensure Docker services are running: docker-compose up -d"
    exit 1
fi

# Check if backend is accessible
if ! curl -s http://localhost:7777/health > /dev/null 2>&1; then
    echo -e "${RED}Error: Backend service not accessible at http://localhost:7777${NC}"
    echo "Ensure Docker services are running: docker-compose up -d"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Initialize test results file
echo -e "${BLUE}Initializing test results...${NC}"
cat > "$TEST_RESULTS_FILE" <<EOF
{
  "schema_version": "1.0",
  "metadata": {
    "test_run_id": "e2e-run-$(date +%Y%m%d-%H%M%S)",
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "trigger": "manual",
    "environment": "development",
    "test_mode": "${TEST_MODE:-false}"
  },
  "summary": {
    "total_tests": $TOTAL_TESTS,
    "passed": 0,
    "failed": 0,
    "pass_rate": 0.0
  },
  "test_results": [],
  "completed_at": null
}
EOF
echo -e "${GREEN}✓ Test results initialized${NC}"
echo ""

# Display test plan
echo -e "${BOLD}${BLUE}Test Execution Plan:${NC}"
echo -e "${BLUE}═════════════════════════════════════════════════════════════${NC}"
for i in "${!TESTS[@]}"; do
    echo -e "  $((i+1)). ${TESTS[$i]}"
done
echo -e "${BLUE}═════════════════════════════════════════════════════════════${NC}"
echo ""

# Start test execution
START_TIME=$(date +%s)

for i in "${!TESTS[@]}"; do
    TEST_ID="${TESTS[$i]}"
    TEST_NUM=$((i+1))

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Test $TEST_NUM of $TOTAL_TESTS: ${TEST_ID}${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Run the test
    if "$TEST_RUNNER" "$TEST_ID"; then
        echo -e "${GREEN}✓ Test $TEST_NUM PASSED: $TEST_ID${NC}"
        ((PASSED_COUNT++))
    else
        echo -e "${RED}✗ Test $TEST_NUM FAILED: $TEST_ID${NC}"
        ((FAILED_COUNT++))
        FAILED_TESTS+=("$TEST_ID")
    fi

    echo ""
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Calculate pass rate
PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED_COUNT / $TOTAL_TESTS) * 100}")

# Update test results file
jq ".summary.passed = $PASSED_COUNT | \
    .summary.failed = $FAILED_COUNT | \
    .summary.pass_rate = $PASS_RATE | \
    .completed_at = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" \
    "$TEST_RESULTS_FILE" > "$TEST_RESULTS_FILE.tmp" && \
    mv "$TEST_RESULTS_FILE.tmp" "$TEST_RESULTS_FILE"

# Display final results
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    Test Suite Results                         ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Total Tests:${NC}      $TOTAL_TESTS"
echo -e "${GREEN}Passed:${NC}           $PASSED_COUNT"
echo -e "${RED}Failed:${NC}           $FAILED_COUNT"
echo -e "${BLUE}Pass Rate:${NC}        ${PASS_RATE}%"
echo -e "${BLUE}Duration:${NC}         ${DURATION}s"
echo -e "${BLUE}Results File:${NC}     $TEST_RESULTS_FILE"
echo ""

# List failed tests if any
if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "${RED}Failed Tests:${NC}"
    for failed_test in "${FAILED_TESTS[@]}"; do
        echo -e "  ${RED}✗${NC} $failed_test"
    done
    echo ""
fi

# Summary message
if [ $FAILED_COUNT -eq 0 ]; then
    echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║     ✓ ALL TESTS PASSED - Test Suite Successful!              ║${NC}"
    echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}${BOLD}║     ✗ TEST SUITE FAILED - $FAILED_COUNT test(s) failed${NC}"
    echo -e "${RED}${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Check individual test outputs in:${NC}"
    echo "  e2e/screenshots/<test_id>_output.txt"
    echo ""
    exit 1
fi
