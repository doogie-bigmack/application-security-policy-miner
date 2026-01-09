# E2E Test: Add PBAC Provider

## Test ID
`test_add_pbac_provider`

## PRD Story
PROV-001: PBAC Provider Integration Management

## Description
Test the ability to add and configure a Policy-Based Access Control (PBAC) provider. This test verifies that users can connect to external PBAC systems like Open Policy Agent (OPA), AWS Verified Permissions, Axiomatics, or PlainID for policy provisioning.

## Setup Requirements
- **Frontend Service**: http://localhost:3333 must be running
- **Backend Service**: http://localhost:7777 must be running
- **Database**: PostgreSQL must be running
- **Test Data**:
  - TEST_MODE=true recommended for mocked provider responses
  - For real testing: OPA server at localhost:8181 (optional)

## MCP Tools to Use
- `mcp__MCP_DOCKER__browser_navigate` - Navigate to pages
- `mcp__MCP_DOCKER__browser_snapshot` - Get page accessibility snapshot
- `mcp__MCP_DOCKER__browser_click` - Click buttons and elements
- `mcp__MCP_DOCKER__browser_type` - Type into input fields
- `mcp__MCP_DOCKER__browser_select_option` - Select dropdown options
- `mcp__MCP_DOCKER__browser_wait_for` - Wait for updates
- `mcp__MCP_DOCKER__browser_take_screenshot` - Take screenshots

## Test Steps

### Step 1: Navigate to Provisioning Page
**Action**: Navigate to the PBAC provider management page
```
mcp__MCP_DOCKER__browser_navigate
url: http://localhost:3333/provisioning
```

**Expected Result**: Provisioning page loads showing provider management interface

### Step 2: Verify Provider List Container
**Action**: Get page snapshot to verify UI elements
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Provider list container (data-testid='provisioning-provider-list') is visible
- "Add Provider" button (data-testid='provisioning-btn-add-provider') is present
- Existing providers may or may not be shown (empty state is OK)

### Step 3: Click Add Provider Button
**Action**: Click to open the add provider form/modal
```
mcp__MCP_DOCKER__browser_click
element: "Add Provider button"
ref: [from snapshot - button with data-testid='provisioning-btn-add-provider']
```

**Expected Result**:
- Add provider form/modal opens
- Shows provider type dropdown
- Shows configuration input fields

### Step 4: Select Provider Type
**Action**: Select "Open Policy Agent (OPA)" as the provider type
```
mcp__MCP_DOCKER__browser_snapshot (to see form state)
mcp__MCP_DOCKER__browser_select_option
element: "Provider type dropdown"
ref: [from snapshot - select with data-testid='provisioning-select-provider-type']
values: ["OPA"] OR ["opa"] OR ["Open Policy Agent"]
```

**Expected Result**:
- OPA is selected in the dropdown
- Form shows OPA-specific configuration fields:
  - Provider name
  - Endpoint URL
  - API key (optional for OPA)

### Step 5: Fill Provider Name
**Action**: Enter a name for the provider
```
mcp__MCP_DOCKER__browser_type
element: "Provider name input"
ref: [from snapshot - input with data-testid='provisioning-input-name']
text: "Test OPA Provider"
```

**Expected Result**: Provider name field contains "Test OPA Provider"

### Step 6: Fill Endpoint URL
**Action**: Enter the OPA endpoint URL
```
mcp__MCP_DOCKER__browser_type
element: "Endpoint URL input"
ref: [from snapshot - input with data-testid='provisioning-input-endpoint']
text: "http://localhost:8181"
```

**Expected Result**: Endpoint field contains "http://localhost:8181"

### Step 7: Fill API Key (if required)
**Action**: Enter API key or leave blank for OPA (doesn't require auth by default)
```
mcp__MCP_DOCKER__browser_snapshot (check if API key field is present)
[If present:]
mcp__MCP_DOCKER__browser_type
element: "API key input"
ref: [from snapshot - input with data-testid='provisioning-input-api-key']
text: "test_api_key_12345"
```

**Expected Result**: API key field populated if required, or skipped if optional

### Step 8: Test Connection (if available)
**Action**: Click "Test Connection" button to verify provider is reachable
```
mcp__MCP_DOCKER__browser_snapshot (check if test connection button exists)
[If button exists:]
mcp__MCP_DOCKER__browser_click
element: "Test Connection button"
ref: [from snapshot - button with data-testid='provisioning-btn-test-connection']

mcp__MCP_DOCKER__browser_wait_for
text: "Connection successful" OR "Connected"
time: 10 (seconds)
```

**Expected Result**:
- Connection test initiates
- Success message appears: "Connection successful" or similar
- Button may change state (checkmark icon, green color)

**Note**: If test connection button doesn't exist, skip to Step 9

### Step 9: Save Provider
**Action**: Click Save/Add button to create the provider
```
mcp__MCP_DOCKER__browser_click
element: "Save or Add Provider button"
ref: [from snapshot - button with data-testid='provisioning-btn-save']
```

**Expected Result**:
- Provider is saved to database
- Success message appears
- Form/modal closes
- Returns to provider list

### Step 10: Verify Provider in List
**Action**: Check that provider appears in the provider list
```
mcp__MCP_DOCKER__browser_wait_for
text: "Test OPA Provider"
time: 5 (seconds)

mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Provider list shows "Test OPA Provider"
- Provider status shows as "Active", "Connected", or similar
- Provider type shows "OPA" or "Open Policy Agent"
- Endpoint URL visible: "http://localhost:8181"

### Step 11: Verify Provider Actions Available
**Action**: Check that provider has action buttons (edit, delete, test)
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Provider row has action buttons
- Edit button present
- Delete button present
- Test/refresh connection button present (optional)

### Step 12: Take Success Screenshot
**Action**: Capture screenshot showing successfully added provider
```
mcp__MCP_DOCKER__browser_take_screenshot
filename: "test_add_pbac_provider_success.png"
```

**Expected Result**: Screenshot saved showing provider in list

## Expected Outcomes
✅ Provisioning page loads successfully
✅ Add provider form opens correctly
✅ Provider type can be selected (OPA)
✅ Configuration fields accept input (name, endpoint, API key)
✅ Connection test succeeds (if implemented)
✅ Provider is saved successfully
✅ Provider appears in the provider list with correct details
✅ Provider status shows as "Active" or "Connected"

## Failure Handling

### If Provisioning Page Doesn't Load
- Take screenshot: `test_add_pbac_provider_nav_failure.png`
- Check: Is frontend service running?
- Check: Is the route /provisioning configured?
- Report: "Provisioning page not accessible"

### If Add Provider Button Not Found
- Take snapshot and screenshot
- Check: Is the button present with data-testid='provisioning-btn-add-provider'?
- Check: Does user have permission to add providers?
- Report: "Add Provider button not found - UI may have changed"

### If Form Doesn't Open
- Take screenshot: `test_add_pbac_provider_form_failure.png`
- Check console errors
- Check: Did button click register?
- Report: "Add provider form did not open - check click handler"

### If Provider Type Dropdown Missing Options
- Take snapshot and screenshot
- Check: Are provider types (OPA, AWS, Axiomatics, PlainID) in dropdown?
- Report: "Provider types not available in dropdown"

### If Connection Test Fails
- Take screenshot: `test_add_pbac_provider_connection_failure.png`
- Check console errors
- Check: Is OPA service running at localhost:8181? (if not TEST_MODE)
- Check: Is backend proxying connection test correctly?
- Check error message in UI
- Report specific error: "Connection test failed: [error message]"
- **Note**: In TEST_MODE, connection should succeed with mocked response

### If Provider Save Fails
- Take screenshot: `test_add_pbac_provider_save_failure.png`
- Check console errors
- Check: Is backend service running?
- Check: Is database accessible?
- Check error message in UI
- Report: "Provider save failed: [error message]"

### If Provider Not in List
- Take screenshot: `test_add_pbac_provider_list_failure.png`
- Check: Was save successful?
- Check: Did page refresh or return to list view?
- Refresh page and check again
- Query backend API: GET /api/provisioning/providers
- Report: "Provider saved but not visible in list"

## Cleanup
The provider should remain for subsequent tests (e.g., test_provision_policy). Cleanup can be handled by master test runner if needed.

## Test Mode Notes
When `TEST_MODE=true`:
- Backend returns mocked PBAC provider responses from `backend/tests/fixtures/pbac_responses.py`
- Connection tests automatically succeed with mocked data
- No actual connection to OPA or other PBAC systems is made
- Provider is stored in test database and can be used for provisioning tests

## Alternative Provider Types
This test can be extended to test other provider types:
- **AWS Verified Permissions**: Select "AWS", enter region and credentials
- **Axiomatics**: Select "Axiomatics", enter endpoint and API key
- **PlainID**: Select "PlainID", enter endpoint and credentials

For E2E testing, OPA is recommended as it's the simplest to set up locally.
