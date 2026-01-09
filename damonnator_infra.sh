#!/bin/bash

# damonnator_infra.sh - Build Test Infrastructure from test-prd.json
# Usage: ./damonnator_infra.sh [iterations]
#
# This script reads test-prd.json and builds the E2E testing infrastructure.
# It is separate from damonnator.sh to keep concerns separated:
# - damonnator.sh: builds product features from prd.json
# - damonnator_infra.sh: builds test infrastructure from test-prd.json
# - damonnator_test.sh: validates features using the test infrastructure

ITERATIONS=${1:-20}
REPO="https://github.com/doogie-bigmack/application-security-policy-miner"

echo ""
echo "=========================================="
echo "🏗️  Damonnator Infrastructure Builder"
echo "=========================================="
echo "Building E2E testing infrastructure from test-prd.json"
echo "Repo: $REPO"
echo "Iterations: $ITERATIONS"
echo ""

for ((i=1; i<=$ITERATIONS; i++)); do
    echo ""
    echo "=========================================="
    echo "Iteration $i of $ITERATIONS"
    echo "=========================================="
    echo ""

    # Create temp output file
    TEMP_OUTPUT=$(mktemp)

    echo "🤖 Starting Claude (this may take 10-30 seconds before output appears)..."
    echo ""

    # Run claude with heredoc - focuses on test-prd.json instead of prd.json
    claude --dangerously-skip-permissions -p "@test-prd.json @progress.txt" << 'PROMPT' | tee "$TEMP_OUTPUT"
You are an autonomous software engineer building E2E testing infrastructure.

## REPO
https://github.com/doogie-bigmack/application-security-policy-miner

## STACK
- Frontend: Bun, React, TailwindCSS, TypeScript
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Linting: ESLint/Prettier (frontend), Ruff (backend)
- Deployment: Docker (use docker-compose for local dev)
- Testing: Python 3.12, Claude Chrome MCP integration

## START EVERY SESSION
1. Read the test-prd.json file above - this defines the test infrastructure to build
2. Read the progress.txt file above - this is what was done recently
3. Run: git log --oneline -10
4. Ensure Docker containers are running: docker-compose up -d

## YOUR JOB
You are building the E2E testing infrastructure, NOT product features.

1. Pick ONE task from test-prd.json that has passes: false
2. Create a feature branch: git checkout -b test-infra/[task-id]
3. Implement it following the steps in test-prd.json
4. Validate it works:
   - Run linters and fix any errors
   - Test the code manually (e.g., run e2e_runner.py)
   - Verify Python imports work correctly
   - For test scenarios, verify they can execute against localhost:3333
5. Update test-prd.json - set passes: true for the completed task
6. Update progress.txt with what you did
7. Commit: git add -A && git commit -m "test: [description]"
8. Push branch: git push -u origin test-infra/[task-id]
9. Create PR and merge to main:
   - gh pr create --fill --base main
   - gh pr merge --auto --squash
10. Return to main: git checkout main && git pull

## CRITICAL GUIDANCE
- You are building TEST INFRASTRUCTURE, not application features
- Focus on test-prd.json stories (TEST-001 through TEST-014)
- Build reusable components: ClaudeChromeExecutor, E2ETestRunner, TestReporter
- Create test scenarios that can be composed for different flows
- Ensure all Python code has proper error handling
- Use Claude's Chrome MCP tools correctly (mcp__claude-in-chrome__*)
- Test against localhost:3333 (frontend) and localhost:7777 (backend)

## BROWSER AUTOMATION
When implementing ClaudeChromeExecutor, use these MCP tools:
- mcp__claude-in-chrome__navigate - navigate to URLs
- mcp__claude-in-chrome__computer - click elements, take screenshots
- mcp__claude-in-chrome__form_input - fill form fields
- mcp__claude-in-chrome__read_page - read page accessibility tree
- mcp__claude-in-chrome__tabs_context_mcp - get tab context

## RULES
- Only work on ONE task per iteration
- Each task gets its own branch and PR
- Never mark passes: true without validating the code works
- Never leave broken code - if stuck, revert and document in progress.txt
- Always commit working code
- Use docker-compose for all services

## COMPLETION
When ALL tasks in test-prd.json have passes: true, output exactly: <promise>TEST_INFRA_COMPLETE</promise>

Now start working.
PROMPT

    # Check if complete
    if grep -q "<promise>TEST_INFRA_COMPLETE</promise>" "$TEMP_OUTPUT"; then
        echo ""
        echo "🎉 Test infrastructure COMPLETE after $i iterations!"
        rm -f "$TEMP_OUTPUT"
        osascript -e 'display notification "Test infrastructure is ready!" with title "Damonnator Infra" sound name "Glass"'
        exit 0
    fi

    # Clean up temp file
    rm -f "$TEMP_OUTPUT"

done

echo ""
echo "Finished $ITERATIONS iterations"
osascript -e 'display notification "Damonnator Infra completed all iterations" with title "Damonnator Infra" sound name "Ping"'
