#!/bin/bash

# damonnator.sh - Long-Running Claude Code Loop for macOS
# Usage: ./damonnator.sh [iterations]

ITERATIONS=${1:-100}
REPO="https://github.com/doogie-bigmack/application-security-policy-miner"

for ((i=1; i<=$ITERATIONS; i++)); do
    echo ""
    echo "========================================"
    echo "Iteration $i of $ITERATIONS"
    echo "========================================"
    echo ""

    # Create temp output file
    TEMP_OUTPUT=$(mktemp)

    # Run claude with heredoc (like test_claude.sh does)
    claude --dangerously-skip-permissions -p "@prd.json @progress.txt" << 'PROMPT' | tee "$TEMP_OUTPUT"
You are an autonomous software engineer. You have access to the browser, terminal, and file system.

## REPO
https://github.com/doogie-bigmack/application-security-policy-miner

## STACK
- Frontend: Bun, React, TailwindCSS, TypeScript
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Linting: ESLint/Prettier (frontend), Ruff (backend)
- Deployment: Docker (use docker-compose for local dev)

## START EVERY SESSION
1. Read the prd.json file above - this is your task list
2. Read the progress.txt file above - this is what was done recently
3. Run: git log --oneline -10
4. Ensure Docker containers are running: docker-compose up -d

## YOUR JOB
1. Pick ONE task from prd.json that has passes: false
2. Create a feature branch: git checkout -b feat/[task-name]
3. Implement it
4. Validate it works:
   - Run linters and fix any errors
   - Run tests if they exist, if they dont' exist create unit, integration test and UI tests
   - Rebuild containers if needed: docker-compose up -d --build
   - Open the frontend in browser and visually verify using claude code's chrome browswer integration
   - Click through it like a real user would
5. Update prd.json - set passes: true for the completed task
6. Update progress.txt with what you did
7. Commit: git add -A && git commit -m "feat: [description]"
8. Push branch: git push -u origin feat/[task-name]
9. Create PR and merge to main:
   - gh pr create --fill --base main
   - gh pr merge --auto --squash
10. Return to main: git checkout main && git pull

## BROWSER VALIDATION
After implementing any UI feature, open the frontend in browser and:
- Verify it looks correct
- Click buttons, fill forms, test the actual user flow
- If something looks broken, fix it before marking complete

## RULES
- Only work on ONE task per iteration
- Each task gets its own branch and PR
- Never mark passes: true without validating in browser (for UI tasks)
- Never leave broken code - if stuck, revert and document in progress.txt
- Always commit working code
- Use docker-compose for all services

## COMPLETION
When ALL tasks in prd.json have passes: true, output exactly: <promise>COMPLETE</promise>

Now start working.
PROMPT

    # Check if complete
    if grep -q "<promise>COMPLETE</promise>" "$TEMP_OUTPUT"; then
        echo ""
        echo "🎉 PRD COMPLETE after $i iterations!"
        rm -f "$TEMP_OUTPUT"
        osascript -e 'display notification "Damonnator finished the PRD!" with title "Damonnator" sound name "Glass"'
        exit 0
    fi

    # Clean up temp file
    rm -f "$TEMP_OUTPUT"

done

echo ""
echo "Finished $ITERATIONS iterations"
osascript -e 'display notification "Damonnator completed all iterations" with title "Damonnator" sound name "Ping"'
