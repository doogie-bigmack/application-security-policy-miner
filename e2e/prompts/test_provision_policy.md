# E2E Test: Provision Policy to PBAC

## Test ID
`test_provision_policy`

## PRD Story
PROV-002: Policy Translation and Provisioning to PBAC Systems

## Description
Test the ability to provision an extracted authorization policy to a PBAC provider. This test verifies that policies can be translated into the target PBAC format (OPA Rego, AWS Cedar, Axiomatics ALFA) and successfully pushed to the PBAC system.

## Setup Requirements
- **Frontend Service**: http://localhost:3333 must be running
- **Backend Service**: http://localhost:7777 must be running
- **Database**: PostgreSQL with policies and providers
- **Prerequisites**:
  - At least one policy must exist (from test_scan_repository)
  - At least one PBAC provider must be configured (from test_add_pbac_provider)
  - TEST_MODE=true recommended for predictable results

## MCP Tools to Use
- `mcp__MCP_DOCKER__browser_navigate` - Navigate to pages
- `mcp__MCP_DOCKER__browser_snapshot` - Get page accessibility snapshot
- `mcp__MCP_DOCKER__browser_click` - Click buttons and elements
- `mcp__MCP_DOCKER__browser_select_option` - Select dropdown options
- `mcp__MCP_DOCKER__browser_wait_for` - Wait for provisioning completion
- `mcp__MCP_DOCKER__browser_take_screenshot` - Take screenshots

## Test Steps

### Step 1: Navigate to Policies Page
**Action**: Navigate to the policies page to select a policy
```
mcp__MCP_DOCKER__browser_navigate
url: http://localhost:3333/policies
```

**Expected Result**: Policies page loads showing list of policies

### Step 2: Select a Policy for Provisioning
**Action**: Click on a policy to view details or provision
```
mcp__MCP_DOCKER__browser_snapshot
mcp__MCP_DOCKER__browser_click
element: "First policy row"
ref: [from snapshot - first element with data-testid='policy-row']
```

**Expected Result**:
- Policy detail view opens OR
- Policy is selected with action buttons visible

### Step 3: Locate Provision Button
**Action**: Find and verify the "Provision" button is available
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Provision button is visible (data-testid='policy-btn-provision' or similar)
- Button is enabled (not disabled/grayed out)

### Step 4: Click Provision Button
**Action**: Initiate the provisioning flow
```
mcp__MCP_DOCKER__browser_click
element: "Provision button"
ref: [from snapshot - button with data-testid='policy-btn-provision']
```

**Expected Result**:
- Provisioning modal/form opens
- Shows provider selection dropdown
- Shows format selection dropdown (optional, may be auto-determined)

### Step 5: Select Target Provider
**Action**: Choose the PBAC provider to provision to
```
mcp__MCP_DOCKER__browser_snapshot (to see provisioning form)
mcp__MCP_DOCKER__browser_select_option
element: "Target provider dropdown"
ref: [from snapshot - select with data-testid='provisioning-select-target-provider']
values: ["Test OPA Provider"]
```

**Expected Result**:
- "Test OPA Provider" is selected
- Form may update to show OPA-specific options
- Format may auto-select to "OPA Rego" based on provider type

### Step 6: Select Target Format (if not auto-determined)
**Action**: If format dropdown exists, select the policy format
```
mcp__MCP_DOCKER__browser_snapshot (check if format dropdown exists)
[If dropdown exists:]
mcp__MCP_DOCKER__browser_select_option
element: "Target format dropdown"
ref: [from snapshot - select with data-testid='provisioning-select-target-format']
values: ["OPA Rego"] OR ["Rego"]
```

**Expected Result**:
- Target format "OPA Rego" is selected
- Ready to provision

### Step 7: Confirm and Start Provisioning
**Action**: Click the "Provision" or "Submit" button to start
```
mcp__MCP_DOCKER__browser_click
element: "Provision/Submit button"
ref: [from snapshot - button with text "Provision" or "Submit"]
```

**Expected Result**:
- Provisioning process starts
- Loading indicator appears
- Status shows "Provisioning..." or "Translating..."

### Step 8: Wait for AI Translation
**Action**: Wait for AI to translate policy to target format (can take 30-120 seconds)
```
mcp__MCP_DOCKER__browser_wait_for
text: "Provisioned successfully" OR "Success" OR "Completed"
time: 120 (seconds - AI translation can take time)
```

**Expected Result**:
- AI translates policy into OPA Rego format
- Policy is pushed to OPA provider
- Success message appears

### Step 9: Verify Provisioning Success
**Action**: Check that success message and status are shown
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Success message visible
- Status indicator (data-testid='provisioning-status') shows "Success" or "Completed"
- Translated policy preview may be shown (Rego code)

### Step 10: Navigate to Provisioning Status
**Action**: Go to provisioning page to verify operation is recorded
```
mcp__MCP_DOCKER__browser_navigate
url: http://localhost:3333/provisioning
```

**Expected Result**: Provisioning page loads

### Step 11: Verify Provisioning History
**Action**: Check that the provisioning operation appears in recent operations
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Recent operations list or history table exists
- Shows the provisioned policy entry
- Entry includes:
  - Policy name or ID
  - Target provider: "Test OPA Provider"
  - Target format: "OPA Rego"
  - Status: "Success" or "Completed"
  - Timestamp

### Step 12: Verify Policy in Provider (Optional)
**Action**: If UI shows policies stored in provider, verify the policy appears
```
mcp__MCP_DOCKER__browser_snapshot
```

**Expected Result**:
- Provider detail view may show provisioned policies
- Policy count incremented for "Test OPA Provider"
- Provisioned policy visible in provider's policy list

### Step 13: Take Success Screenshot
**Action**: Capture final state showing successful provisioning
```
mcp__MCP_DOCKER__browser_take_screenshot
filename: "test_provision_policy_success.png"
```

**Expected Result**: Screenshot saved showing provisioning success

## Expected Outcomes
✅ Policy can be selected for provisioning
✅ Provisioning modal/form opens correctly
✅ Target provider can be selected from available providers
✅ Target format can be selected or is auto-determined
✅ Provisioning process completes successfully
✅ Success message is displayed
✅ Provisioning operation appears in history/status page
✅ Policy is visible in target PBAC provider (if UI shows this)
✅ Entire flow completes within 2 minutes

## Failure Handling

### If No Policies Available
- Take screenshot: `test_provision_policy_no_policies.png`
- Check: Did test_scan_repository complete successfully?
- Check: Are policies in database?
- Report: "No policies available for provisioning - scan may have failed"

### If No Providers Available
- Take screenshot: `test_provision_policy_no_providers.png`
- Check: Did test_add_pbac_provider complete successfully?
- Check: Are providers in database?
- Report: "No PBAC providers available - provider setup failed"

### If Provision Button Not Found
- Take snapshot and screenshot
- Check: Is policy detail view open?
- Check: Does UI have provisioning feature enabled?
- Report: "Provision button not found - UI may have changed or feature disabled"

### If Provisioning Form Doesn't Open
- Take screenshot: `test_provision_policy_form_failure.png`
- Check console errors
- Report: "Provisioning form did not open - check click handler"

### If Provider Dropdown Empty
- Take screenshot: `test_provision_policy_no_provider_options.png`
- Check: Are providers active/enabled?
- Check: Does backend return providers in API response?
- Report: "No providers available in dropdown"

### If Provisioning Fails
- Take screenshot: `test_provision_policy_failure.png`
- Check console errors
- Check: Is backend service running?
- Check: Is AI translation service available?
- Check: Is provider endpoint accessible?
- Check error message in UI
- Possible errors:
  - "Translation failed" - AI service issue
  - "Provider unreachable" - OPA endpoint down
  - "Invalid policy format" - Translation error
  - "Permission denied" - Provider authentication issue
- Report specific error: "Provisioning failed: [error message]"

### If Provisioning Times Out
- Take screenshot: `test_provision_policy_timeout.png`
- Check: Is TEST_MODE=true? (real AI translation takes longer)
- Check: Is backend responsive?
- Check: Is there a hung process?
- Report: "Provisioning did not complete within 2 minutes"

### If Success Not Reflected in UI
- Take screenshot: `test_provision_policy_status_failure.png`
- Check: Did provisioning actually complete on backend?
- Check: Is provisioning history loading correctly?
- Query backend API: GET /api/provisioning/operations
- Report: "Provisioning completed but not visible in UI"

## Cleanup
No cleanup required - provisioned policies remain for verification and audit.

## Test Mode Notes
When `TEST_MODE=true`:
- Backend returns mocked provisioning responses from `backend/tests/fixtures/pbac_responses.py`
- AI translation is simulated with pre-translated policy examples
- Provisioning completes in ~5 seconds (simulated processing time)
- No actual policy push to OPA or other PBAC systems
- Success response is automatically returned

## Example Translated Policy (OPA Rego)
For reference, an Admin-only policy translated to OPA Rego might look like:
```rego
package policy.authorization

# Admin can create users
allow {
    input.subject.role == "admin"
    input.action == "create"
    input.resource == "users"
}
```

This translation is done by AI and should be visible in the provisioning success view.
