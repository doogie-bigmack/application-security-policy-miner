# E2E Testing & Autonomous Validation System

## Overview

This project uses **two autonomous Claude loops** working together:

1. **damonnator.sh** - Builds features from `prd.json`
2. **damonnator_test.sh** - Validates features with E2E tests

## Quick Start

```bash
# Show all available commands
make help

# Start development environment
make docker-up

# Run testing loop (validates completed features)
make damonnator-test

# Run development loop (builds features)
make damonnator

# Run both loops in parallel (advanced)
make damonnator-both
```

## Architecture

```
┌──────────────────┐         ┌──────────────────┐
│  damonnator.sh   │         │damonnator_test.sh│
│  (Development)   │────────▶│    (Testing)     │
│                  │         │                  │
│ - Reads prd.json │         │ - Validates work │
│ - Builds features│         │ - Runs E2E tests │
│ - Creates PRs    │         │ - Updates status │
│ - Marks complete │         │ - Finds bugs     │
└──────────────────┘         └──────────────────┘
         │                            │
         ▼                            ▼
    prd.json ◀───────────────── test-results.json
    progress.txt                e2e-tests.json
```

## The Two Loops Explained

### damonnator.sh (Development Loop)

**Purpose:** Build features autonomously

**Process:**
1. Picks a task from `prd.json` where `passes: false`
2. Creates feature branch
3. Implements the feature
4. Validates in browser
5. Updates `prd.json` to `passes: true`
6. Creates PR and merges

**Usage:**
```bash
./damonnator.sh 100              # Run 100 iterations
make damonnator                  # Interactive
```

### damonnator_test.sh (Testing Loop)

**Purpose:** Validate completed features with E2E tests

**Process:**
1. Finds stories in `prd.json` where `passes: true` but not E2E tested
2. Runs automated E2E tests using Claude's Chrome integration
3. Updates `test-results.json` with results
4. Updates `prd.json` with test metadata
5. Creates GitHub issues for failures
6. Captures screenshots for debugging

**Usage:**
```bash
./damonnator_test.sh 50          # Run 50 test iterations
make damonnator-test             # Interactive
```

## File Structure

```
/
├── damonnator.sh                 # Development loop
├── damonnator_test.sh            # Testing loop
├── Makefile                      # Command orchestration
├── prd.json                      # Product requirements (task list)
├── progress.txt                  # Progress log
├── e2e-tests.json                # Test definitions
├── test-results.json             # Latest test results
└── e2e/
    ├── e2e_runner.py            # Test orchestrator
    ├── test_executor.py         # Claude Chrome wrapper
    ├── test_reporter.py         # Report generator
    ├── requirements.txt         # Python dependencies
    └── screenshots/             # Failure screenshots
```

## prd.json Schema Enhancement

Each story now includes test metadata:

```json
{
  "id": "FUNC-001",
  "category": "functional",
  "description": "Add GitHub repository integration",
  "steps": [...],
  "passes": true,
  "test_metadata": {
    "e2e_test_id": "test_add_git_repository",
    "last_tested": "2026-01-09T14:30:00Z",
    "test_status": "passed",
    "failure_count": 0,
    "last_failure_reason": null
  }
}
```

## Test Execution Flow

1. **Testing loop reads prd.json** - Finds completed but untested stories
2. **Loads test definition** from `e2e-tests.json`
3. **Executes test** using Claude Chrome integration:
   - Navigate to URL
   - Click buttons, fill forms
   - Verify expected outcomes
   - Take screenshots on failure
4. **Generates results** in `test-results.json`
5. **Updates prd.json** with test metadata
6. **Creates GitHub issue** if test fails

## Makefile Commands

### Development
```bash
make install          # Install all dependencies
make dev              # Start dev servers
make build            # Build Docker containers
```

### Docker
```bash
make docker-up        # Start all services
make docker-down      # Stop all services
make docker-restart   # Restart services
make docker-logs      # Follow logs
```

### Testing
```bash
make test             # Run backend unit tests
make e2e              # Run E2E tests manually
make test-report      # Show latest test results
```

### Code Quality
```bash
make lint             # Run linters
make format           # Format code
make lint-fix         # Auto-fix issues
```

### Autonomous Loops
```bash
make damonnator           # Development loop
make damonnator-test      # Testing loop
make damonnator-both      # Both loops in parallel
make damonnator-stop      # Stop all loops
```

### Monitoring
```bash
make status           # Service status + progress
make logs             # View progress.txt
make metrics          # Open Grafana + Prometheus
```

### Database
```bash
make db-shell         # PostgreSQL shell
make db-migrate       # Run migrations
make db-reset         # Reset database (WARNING!)
```

### Cleanup
```bash
make clean            # Clean temp files
make clean-all        # Deep clean (Docker + files)
```

## Running Both Loops Together

For maximum automation, run both loops in parallel:

```bash
# Terminal 1: Development loop builds features
./damonnator.sh 100

# Terminal 2 (wait 30 seconds): Testing loop validates
./damonnator_test.sh 50
```

Or use the Makefile (more advanced):
```bash
make damonnator-both
```

**How it works:**
1. Dev loop implements a feature and marks `passes: true`
2. Testing loop detects untested story
3. Testing loop validates with E2E tests
4. If tests pass: Updates test_metadata
5. If tests fail: Creates GitHub issue with details
6. Dev loop can pick up failed test issues and fix

## Test Results Example

```json
{
  "test_run_id": "run_2026-01-09_14-30-00",
  "summary": {
    "total_tests": 5,
    "passed": 4,
    "failed": 1,
    "pass_rate": 80.0
  },
  "test_results": [
    {
      "test_id": "test_add_git_repository",
      "status": "failed",
      "error": {
        "message": "Button 'GitHub' not found",
        "screenshot": "e2e/screenshots/test_add_git_repository.png"
      },
      "recommendations": [
        "Check if button text changed",
        "Verify modal rendered correctly"
      ]
    }
  ]
}
```

## Workflow Example

**Day 1: Build Feature**
```bash
make damonnator
# → Implements "GitHub Repository Integration"
# → Updates prd.json: passes: true
# → Creates PR, merges to main
```

**Day 1 Evening: Validate Feature**
```bash
make damonnator-test
# → Runs E2E test for GitHub integration
# → Tests pass ✅
# → Updates prd.json with test_metadata
```

**Day 2: Feature Has Bug**
```bash
make damonnator-test
# → Tests fail ❌
# → Creates GitHub issue #54 with:
#   - Error message
#   - Screenshot
#   - Reproduction steps
#   - Recommendations
```

**Day 2: Fix Bug**
```bash
make damonnator
# → Picks GitHub issue #54
# → Fixes the bug
# → Re-runs tests
# → Tests pass ✅
# → Closes issue
```

## Current Status

**Phase 1: Core Infrastructure** (GitHub Issue #53)
- [ ] Create `e2e/` directory structure
- [ ] Implement `e2e_runner.py`
- [ ] Implement `test_executor.py`
- [ ] Create `e2e-tests.json` with 5 critical tests
- [ ] Update `prd.json` schema with test_metadata
- [ ] Test end-to-end flow

**Next:** Run `make damonnator` and have it implement Phase 1 from GitHub issue #53

## Monitoring Progress

```bash
# Check overall status
make status

# View recent progress
make logs

# Open monitoring dashboards
make metrics

# Check test results
make test-report
```

## Tips

1. **Start with one loop first** - Get comfortable with the development loop before adding the testing loop

2. **Use the Makefile** - It handles service startup, dependency checks, etc.

3. **Monitor both loops** - Keep terminal windows open to watch progress

4. **Review test-results.json** - Rich diagnostics on what passed/failed

5. **Screenshots are gold** - Check `e2e/screenshots/` when tests fail

6. **Let it run overnight** - The loops are designed for unattended operation

## Troubleshooting

**Services won't start:**
```bash
make docker-restart
make status
```

**Tests fail to run:**
```bash
# Check if E2E infrastructure exists
ls -la e2e/

# If missing, implement Phase 1
make damonnator  # Then tell it to implement issue #53
```

**Loop gets stuck:**
```bash
make damonnator-stop
# Review progress.txt for last action
make logs
```

**Out of sync:**
```bash
git pull origin main
make docker-restart
make status
```

## See Also

- Full plan: `.claude/plans/adaptive-scribbling-dahl.md`
- Phase 1 tracking: GitHub Issue #53
- Original validation report: In conversation history
