#!/usr/bin/env bash

#
# claude_test_runner.sh
# Claude-driven E2E test executor
#
# This script uses Claude CLI with MCP browser tools to execute E2E tests
# by reading test definitions from e2e-tests.json and test prompts from e2e/prompts/
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMPTS_DIR="$SCRIPT_DIR/prompts"
SCREENSHOTS_DIR="$SCRIPT_DIR/screenshots"
E2E_TESTS_JSON="$PROJECT_ROOT/e2e-tests.json"

# Ensure screenshots directory exists
mkdir -p "$SCREENSHOTS_DIR"

# Usage information
usage() {
    echo "Usage: $0 <test_id>"
    echo ""
    echo "Executes a single E2E test using Claude with browser automation."
    echo ""
    echo "Arguments:"
    echo "  test_id    Test identifier from e2e-tests.json"
    echo ""
    echo "Examples:"
    echo "  $0 test_add_github_repository"
    echo "  $0 test_scan_repository"
    echo "  $0 test_view_policies"
    echo "  $0 test_add_pbac_provider"
    echo "  $0 test_provision_policy"
    echo ""
    echo "Available tests:"
    jq -r '.test_suites[].tests[].test_id' "$E2E_TESTS_JSON" 2>/dev/null || echo "  (e2e-tests.json not found)"
    exit 1
}

# Check arguments
if [ $# -ne 1 ]; then
    usage
fi

TEST_ID="$1"

# Validate test ID exists in e2e-tests.json
if ! jq -e ".test_suites[].tests[] | select(.test_id == \"$TEST_ID\")" "$E2E_TESTS_JSON" > /dev/null 2>&1; then
    echo -e "${RED}Error: Test ID '$TEST_ID' not found in e2e-tests.json${NC}"
    echo ""
    echo "Available tests:"
    jq -r '.test_suites[].tests[] | "\(.test_id) - \(.name)"' "$E2E_TESTS_JSON"
    exit 1
fi

# Check if prompt file exists
PROMPT_FILE="$PROMPTS_DIR/${TEST_ID}.md"
if [ ! -f "$PROMPT_FILE" ]; then
    echo -e "${RED}Error: Prompt file not found: $PROMPT_FILE${NC}"
    exit 1
fi

# Extract test definition from e2e-tests.json
TEST_DEF=$(jq ".test_suites[].tests[] | select(.test_id == \"$TEST_ID\")" "$E2E_TESTS_JSON")
TEST_NAME=$(echo "$TEST_DEF" | jq -r '.name')
TEST_PRIORITY=$(echo "$TEST_DEF" | jq -r '.priority')
PRD_STORY_ID=$(echo "$TEST_DEF" | jq -r '.prd_story_id')

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Claude-Driven E2E Test Executor                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test ID:${NC}        $TEST_ID"
echo -e "${BLUE}Test Name:${NC}      $TEST_NAME"
echo -e "${BLUE}Priority:${NC}       $TEST_PRIORITY"
echo -e "${BLUE}PRD Story:${NC}      $PRD_STORY_ID"
echo -e "${BLUE}Prompt File:${NC}    $PROMPT_FILE"
echo ""

# Check if Claude CLI is available
if ! command -v claude &> /dev/null; then
    echo -e "${YELLOW}Warning: 'claude' CLI not found in PATH${NC}"
    echo "Attempting to use: npx @anthropic-ai/claude-cli"
    CLAUDE_CMD="npx @anthropic-ai/claude-cli"
else
    CLAUDE_CMD="claude"
fi

# Check if MCP Docker server is available
echo -e "${BLUE}Checking MCP Docker server availability...${NC}"
# Note: This is a placeholder - actual MCP server check would go here
# For now, we assume it's running if this script is executed

# Prepare the combined prompt for Claude
COMBINED_PROMPT=$(cat <<EOF
You are an E2E test automation agent. Execute the following test using browser automation MCP tools.

# Test Definition from e2e-tests.json
\`\`\`json
$TEST_DEF
\`\`\`

# Test Execution Instructions
$(cat "$PROMPT_FILE")

# Additional Context
- Project root: $PROJECT_ROOT
- Screenshots directory: $SCREENSHOTS_DIR
- Test mode: \${TEST_MODE:-false}
- Environment: Development/Testing

# Execution Guidelines
1. Read the test prompt carefully and understand all steps
2. Use MCP browser tools (mcp__MCP_DOCKER__browser_*) for all browser interactions
3. Take screenshots on failure and save to: $SCREENSHOTS_DIR/
4. If a step fails, follow the failure handling instructions in the prompt
5. Report clear success/failure status at the end
6. Include any error messages or diagnostics in your response

# Important Notes
- ALWAYS use browser_snapshot before clicking to get element refs
- DO NOT use browser_take_screenshot for actions (use browser_snapshot instead)
- Save failure screenshots with descriptive names
- If TEST_MODE=true, backend returns mocked responses
- All services should be running: frontend (3333), backend (7777), postgres, redis

Begin test execution now.
EOF
)

# Save combined prompt to temporary file for debugging
TEMP_PROMPT_FILE="$SCREENSHOTS_DIR/${TEST_ID}_prompt.txt"
echo "$COMBINED_PROMPT" > "$TEMP_PROMPT_FILE"
echo -e "${BLUE}Combined prompt saved to:${NC} $TEMP_PROMPT_FILE"
echo ""

# Execute test with Claude
echo -e "${BLUE}Starting test execution with Claude...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

START_TIME=$(date +%s)

# Run Claude with the combined prompt
# Note: Using --dangerously-skip-permissions for automated E2E testing
if echo "$COMBINED_PROMPT" | $CLAUDE_CMD --dangerously-skip-permissions > "$SCREENSHOTS_DIR/${TEST_ID}_output.txt" 2>&1; then
    TEST_RESULT="PASSED"
    RESULT_COLOR="$GREEN"
else
    TEST_RESULT="FAILED"
    RESULT_COLOR="$RED"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# Display Claude's output
echo -e "${BLUE}Claude Output:${NC}"
cat "$SCREENSHOTS_DIR/${TEST_ID}_output.txt"
echo ""

# Check for screenshots generated during test
SCREENSHOT_COUNT=$(find "$SCREENSHOTS_DIR" -name "${TEST_ID}*.png" 2>/dev/null | wc -l | tr -d ' ')

# Display test result
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Test Result                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test ID:${NC}           $TEST_ID"
echo -e "${BLUE}Result:${NC}            ${RESULT_COLOR}$TEST_RESULT${NC}"
echo -e "${BLUE}Duration:${NC}          ${DURATION}s"
echo -e "${BLUE}Screenshots:${NC}       $SCREENSHOT_COUNT captured"
echo -e "${BLUE}Output:${NC}            $SCREENSHOTS_DIR/${TEST_ID}_output.txt"
echo -e "${BLUE}Prompt:${NC}            $TEMP_PROMPT_FILE"
echo ""

# List screenshots if any were captured
if [ "$SCREENSHOT_COUNT" -gt 0 ]; then
    echo -e "${BLUE}Screenshots captured:${NC}"
    find "$SCREENSHOTS_DIR" -name "${TEST_ID}*.png" -type f -printf "  - %f\n" 2>/dev/null || \
    find "$SCREENSHOTS_DIR" -name "${TEST_ID}*.png" -type f -exec basename {} \; | sed 's/^/  - /'
    echo ""
fi

# Exit with appropriate code
if [ "$TEST_RESULT" = "PASSED" ]; then
    echo -e "${GREEN}✓ Test completed successfully${NC}"
    exit 0
else
    echo -e "${RED}✗ Test failed${NC}"
    echo -e "${YELLOW}Check the output file for details: $SCREENSHOTS_DIR/${TEST_ID}_output.txt${NC}"
    exit 1
fi
