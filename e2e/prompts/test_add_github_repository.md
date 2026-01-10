# E2E Test: Add GitHub Repository

## Test ID
`test_add_github_repository`

## PRD Story
FUNC-001: GitHub Integration for Repository Management

## Description
Test the ability to add a GitHub repository to the Policy Miner application through the UI. This test verifies that users can connect a GitHub repository using a personal access token and see it appear in the repository list.

## Setup Requirements
- **Frontend Service**: http://localhost:3333 must be running
- **Backend Service**: http://localhost:7777 must be running
- **Database**: PostgreSQL must be running and accessible
- **Test Data**:
  - Environment variable `GITHUB_TEST_TOKEN` must be set (or use TEST_MODE=true for mocked responses)
  - Test repository URL: `https://github.com/doogie-bigmack/test-auth-patterns`

## MCP Tools to Use
Use the Claude Chrome MCP tools to interact with the browser:
- `mcp__MCP_DOCKER__browser_navigate` - Navigate to pages
- `mcp__MCP_DOCKER__browser_snapshot` - Get page accessibility snapshot (BETTER than screenshot for actions)
- `mcp__MCP_DOCKER__browser_click` - Click buttons and elements
- `mcp__MCP_DOCKER__browser_type` - Type text into input fields
- `mcp__MCP_DOCKER__browser_wait_for` - Wait for text to appear or time to pass
- `mcp__MCP_DOCKER__browser_take_screenshot` - Take screenshot for debugging (DO NOT use for actions)

## Test Steps

### Step 1: Navigate to Repositories Page
**Action**: Navigate to the repositories management page
```
mcp__MCP_DOCKER__browser_navigate
url: http://localhost:3333/repositories
```

**Expected Result**: Page loads successfully, shows "Repositories" heading

### Step 2: Verify Page Loaded
**Action**: Get page snapshot to verify elements are present
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**: Snapshot shows "Add Repository" button and repository list container

### Step 3: Click Add Repository Button
**Action**: Click the "Add Repository" button to open the modal
```
mcp__MCP_DOCKER__browser_click
element: "Add Repository button"
ref: [from snapshot - button with data-testid='repositories-btn-add']
```

**Expected Result**: Modal opens with integration options (GitHub, GitLab, Bitbucket, Azure DevOps)

### Step 4: Select GitHub Integration
**Action**: Click the GitHub integration button
```
mcp__MCP_DOCKER__browser_snapshot (to get updated page state)
mcp__MCP_DOCKER__browser_click
element: "GitHub integration button"
ref: [from snapshot - button with data-testid='add-repo-btn-github']
```

**Expected Result**: Form appears requesting repository details and GitHub token

### Step 5: Fill Repository Name
**Action**: Enter a name for the repository
```
mcp__MCP_DOCKER__browser_type
element: "Repository name input"
ref: [from snapshot - input with data-testid='add-repo-input-name']
text: "Test Auth Patterns"
```

**Expected Result**: Repository name field contains "Test Auth Patterns"

### Step 6: Fill Repository URL
**Action**: Enter the GitHub repository URL
```
mcp__MCP_DOCKER__browser_type
element: "Repository URL input"
ref: [from snapshot - input with data-testid='add-repo-input-url']
text: "https://github.com/doogie-bigmack/test-auth-patterns"
```

**Expected Result**: URL field contains the test repository URL

### Step 7: Fill GitHub Token
**Action**: Enter the GitHub personal access token
```
mcp__MCP_DOCKER__browser_type
element: "GitHub token input"
ref: [from snapshot - input with data-testid='add-repo-input-token']
text: [value from GITHUB_TEST_TOKEN environment variable or "test_token_12345" if TEST_MODE=true]
```

**Expected Result**: Token field is populated (displayed as masked text)

### Step 8: Click Connect Button
**Action**: Submit the form by clicking the Connect button
```
mcp__MCP_DOCKER__browser_click
element: "Connect button"
ref: [from snapshot - button with data-testid='add-repo-btn-connect']
```

**Expected Result**:
- Loading indicator appears briefly
- Backend validates the token and repository access
- Success message appears

### Step 9: Wait for Success Confirmation
**Action**: Wait for success message to appear
```
mcp__MCP_DOCKER__browser_wait_for
text: "Repository added successfully"
time: 10 (seconds)
```

**Expected Result**: Success message is visible on the page

### Step 10: Verify Repository in List
**Action**: Take snapshot to verify repository appears in the list
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Repository list container (data-testid='repositories-list') contains the new repository
- Repository row (data-testid='repository-row') exists
- Repository name "Test Auth Patterns" or "test-auth-patterns" is visible
- Repository status shows as "Connected" or "Active"

### Step 11: Take Success Screenshot
**Action**: Capture screenshot for test evidence
```
mcp__MCP_DOCKER__browser_take_screenshot
filename: "test_add_github_repository_success.png"
```

**Expected Result**: Screenshot saved showing the successfully added repository

## Expected Outcomes
✅ Repository is successfully added via the UI
✅ Success message is displayed to the user
✅ Repository appears in the repository list with correct name
✅ Repository status shows as "Connected" or "Active"
✅ No error messages are displayed

## Failure Handling

### If Navigation Fails
- Take screenshot: `test_add_github_repository_nav_failure.png`
- Check: Is frontend service running on http://localhost:3333?
- Check: Are there console errors? (use browser_console_messages)
- Report: "Navigation failed - frontend service may not be running"

### If Add Repository Button Not Found
- Take snapshot and screenshot
- Check: Is the page fully loaded?
- Check: Does the button have the correct data-testid='repositories-btn-add'?
- Report: "Add Repository button not found - UI may have changed"

### If GitHub Integration Button Not Found
- Take snapshot and screenshot
- Check: Did the modal open correctly?
- Check: Is the button labeled correctly and has data-testid='add-repo-btn-github'?
- Report: "GitHub integration option not found - modal may not have opened"

### If Form Fields Not Found
- Take snapshot and screenshot
- Check: Did GitHub integration trigger the correct form?
- Check: Are input fields present with data-testid attributes?
- Report: "Form fields not found - GitHub integration form may have UI changes"

### If Connection Fails
- Take screenshot: `test_add_github_repository_connection_failure.png`
- Check console errors: `mcp__MCP_DOCKER__browser_console_messages(onlyErrors: true)`
- Check for error message in snapshot
- Possible causes:
  - Invalid GitHub token
  - Backend service not running (http://localhost:7777)
  - Database connection issues
  - Network errors to GitHub API (if not TEST_MODE)
- Report specific error message shown in UI

### If Repository Not in List
- Take screenshot: `test_add_github_repository_list_failure.png`
- Check: Was success message shown?
- Check: Is the repository list container visible?
- Refresh page and check again
- Report: "Repository added but not visible in list - may be a refresh/state issue"

## Cleanup
After test completion (success or failure), the test should leave the repository in place for subsequent tests (e.g., test_scan_repository). Cleanup should be handled by the master test runner if needed.

## Test Mode Notes
When `TEST_MODE=true`:
- Backend returns mocked GitHub API responses from `backend/tests/fixtures/github_responses.py`
- No actual GitHub API calls are made
- Use token value: `test_token_12345` (will be accepted by mocked backend)
- Repository verification succeeds automatically
