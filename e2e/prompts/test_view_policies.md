# E2E Test: View and Filter Policies

## Test ID
`test_view_policies`

## PRD Story
UI-001: Policy Viewing and Management Interface

## Description
Test the ability to view, filter, and sort extracted authorization policies. This test verifies that users can browse the policy catalog, apply filters, and view detailed policy information including code evidence.

## Setup Requirements
- **Frontend Service**: http://localhost:3333 must be running
- **Backend Service**: http://localhost:7777 must be running
- **Database**: PostgreSQL with extracted policies from test_scan_repository
- **Prerequisites**:
  - Policies must exist in database (from test_scan_repository)
  - At least 5 policies should be available

## MCP Tools to Use
- `mcp__MCP_DOCKER__browser_navigate` - Navigate to pages
- `mcp__MCP_DOCKER__browser_snapshot` - Get page accessibility snapshot
- `mcp__MCP_DOCKER__browser_click` - Click buttons and elements
- `mcp__MCP_DOCKER__browser_type` - Type into filter fields
- `mcp__MCP_DOCKER__browser_wait_for` - Wait for updates
- `mcp__MCP_DOCKER__browser_take_screenshot` - Take screenshots

## Test Steps

### Step 1: Navigate to Policies Page
**Action**: Navigate to the policies management page
```
mcp__MCP_DOCKER__browser_navigate
url: http://localhost:3333/policies
```

**Expected Result**: Policies page loads successfully

### Step 2: Verify Policies Table Visible
**Action**: Get page snapshot to verify policies are displayed
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Policies table/list container (data-testid='policies-table') is visible
- Multiple policy rows (data-testid='policy-row') are present
- Table shows columns: Subject (Who), Resource (What), Action (How), Conditions (When), Evidence

### Step 3: Count Total Policies
**Action**: Count visible policies in the table
- From snapshot, count elements with data-testid='policy-row'

**Expected Result**: At least 5 policies are visible

### Step 4: Verify Policy Data Structure
**Action**: Examine first few policy rows to verify data
- Each row should have:
  - policy-subject: Role or user type (e.g., "Admin", "Manager", "User")
  - policy-resource: Resource being protected (e.g., "User Management", "Reports", "Audit Logs")
  - policy-action: Action being controlled (e.g., "create", "update", "delete", "view")
  - policy-conditions: Conditions if any (e.g., "requires permission", "ownership check")
  - policy-evidence: Link or indicator for code evidence

**Expected Result**: Policies have complete data in all fields

### Step 5: Test Filter by Subject (Who)
**Action**: Filter policies by subject role
```
mcp__MCP_DOCKER__browser_snapshot (to find filter input)
mcp__MCP_DOCKER__browser_type
element: "Subject filter input"
ref: [from snapshot - input with data-testid='policies-filter-subject' OR data-testid='policies-filter-source']
text: "Admin"
```

**Expected Result**:
- Filter updates the policy list
- Only policies with "Admin" in subject field are shown
- Policy count decreases (unless all policies are admin-related)

### Step 6: Clear Subject Filter
**Action**: Clear the filter to show all policies again
```
mcp__MCP_DOCKER__browser_type
element: "Subject filter input"
ref: [same as above]
text: ""
```

**Expected Result**: All policies are visible again

### Step 7: Test Filter by Resource (What)
**Action**: Filter policies by resource type
```
mcp__MCP_DOCKER__browser_type
element: "Resource filter input"
ref: [from snapshot - input with data-testid='policies-filter-resource']
text: "User"
```

**Expected Result**:
- Filter updates the policy list
- Only policies related to "User" resources are shown (e.g., "User Management", "User Data")

### Step 8: Test Sort Functionality
**Action**: Click on a column header to sort policies
```
mcp__MCP_DOCKER__browser_snapshot
mcp__MCP_DOCKER__browser_click
element: "Sort by dropdown or column header"
ref: [from snapshot - element with data-testid='policies-sort-by' OR clickable column header]
```

**Expected Result**:
- Policies reorder based on selected column
- Sort indicator (arrow up/down) appears on column header

### Step 9: View Policy Details
**Action**: Click on a policy row to view full details
```
mcp__MCP_DOCKER__browser_snapshot (to select a policy)
mcp__MCP_DOCKER__browser_click
element: "First policy row"
ref: [from snapshot - first element with data-testid='policy-row']
```

**Expected Result**:
- Policy detail view/modal opens (data-testid='policy-detail-view')
- Shows complete policy information:
  - Subject (Who)
  - Resource (What)
  - Action (How)
  - Conditions (When)
  - Evidence section with code snippets

### Step 10: Verify Code Evidence
**Action**: Verify evidence section shows actual code
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Evidence section (data-testid='policy-evidence') is visible
- Shows code snippets from source files
- Includes file path and line numbers
- Code snippet shows the authorization pattern (e.g., @require_role('admin'))

### Step 11: Close Policy Details
**Action**: Close the detail view
```
mcp__MCP_DOCKER__browser_click
element: "Close button or X"
ref: [from snapshot - close button in modal]
```

**Expected Result**: Detail view closes, returns to policies list

### Step 12: Test Export Functionality (if available)
**Action**: Click export button to download policies
```
mcp__MCP_DOCKER__browser_snapshot
mcp__MCP_DOCKER__browser_click
element: "Export button"
ref: [from snapshot - button with data-testid='policies-btn-export']
```

**Expected Result**:
- Export dialog appears or download initiates
- Format options shown (CSV, JSON, PDF, etc.)

### Step 13: Take Success Screenshot
**Action**: Capture final state showing policies interface
```
mcp__MCP_DOCKER__browser_take_screenshot
filename: "test_view_policies_success.png"
fullPage: true
```

**Expected Result**: Screenshot saved showing policies list and functionality

## Expected Outcomes
✅ Policies page loads and displays policy table
✅ All required columns are visible (Subject, Resource, Action, Conditions, Evidence)
✅ Filter by subject works correctly
✅ Filter by resource works correctly
✅ Sort functionality works (if implemented)
✅ Policy detail view shows complete information
✅ Code evidence is visible with file paths and snippets
✅ Export functionality works (if implemented)

## Failure Handling

### If Policies Page Empty
- Take screenshot: `test_view_policies_empty.png`
- Check: Did test_scan_repository complete successfully?
- Check: Are policies in database? (query backend API at /api/policies)
- Check console errors
- Report: "Policies page empty - scan may have failed or data not loaded"

### If Table Columns Missing
- Take snapshot and screenshot
- Check: Is the table structure correct?
- Check: Are data-testid attributes present on column elements?
- Report: "Table structure incomplete - UI may have changed"

### If Filters Don't Work
- Take screenshot: `test_view_policies_filter_failure.png`
- Check console errors
- Check: Are filter inputs present and editable?
- Check: Does typing update the filter state?
- Report: "Filter functionality not working - check frontend logic"

### If Policy Details Don't Open
- Take screenshot: `test_view_policies_detail_failure.png`
- Check: Is the policy row clickable?
- Check: Is there a detail view component in the UI?
- Check console errors for JavaScript issues
- Report: "Policy details not opening - click handler may be missing"

### If Evidence Not Visible
- Take screenshot: `test_view_policies_no_evidence.png`
- Check: Does the policy have evidence data in database?
- Check: Is the evidence section (data-testid='policy-evidence') present?
- Report: "Code evidence not visible - data may be missing or UI component issue"

## Cleanup
No cleanup required - policies remain for subsequent tests.

## Test Mode Notes
When `TEST_MODE=true`:
- Policies come from mocked scan results (15 policies)
- Evidence includes realistic code snippets from test-auth-patterns patterns
- All filtering and sorting should work with mocked data
