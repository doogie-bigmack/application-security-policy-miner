# C# to AWS Cedar Policy Translation

## Overview

The Policy Miner supports translating authorization policies extracted from C# code to AWS Cedar format. This enables organizations to migrate from inline C# authorization logic to centralized policy-based access control using AWS Verified Permissions.

## Supported C# Authorization Patterns

### 1. ASP.NET Core [Authorize] Attributes

**C# Code:**
```csharp
[Authorize(Roles = "Manager")]
[HttpPost("approve")]
public IActionResult ApproveExpense(ExpenseRequest request)
{
    if (request.Amount >= 5000)
    {
        return Forbid("Amount exceeds manager approval limit");
    }
    return Ok("Expense approved");
}
```

**Extracted Policy:**
- **WHO (Subject):** Manager
- **WHAT (Resource):** expense
- **HOW (Action):** approve
- **WHEN (Conditions):** amount < 5000

**Translated Cedar Policy:**
```cedar
permit (
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"expense"
)
when {
    resource.amount < 5000
};
```

### 2. ASP.NET Legacy [PrincipalPermission] Attributes

**C# Code:**
```csharp
[PrincipalPermission(SecurityAction.Demand, Role = "Administrator")]
public void ModifyConfiguration(ConfigurationSettings settings)
{
    // Configuration modification logic
}
```

**Extracted Policy:**
- **WHO:** Administrator
- **WHAT:** configuration
- **HOW:** modify
- **WHEN:** user is authenticated

**Translated Cedar Policy:**
```cedar
permit (
    principal in Role::"Administrator",
    action == Action::"modify",
    resource in ResourceType::"configuration"
)
when {
    principal.isAuthenticated == true
};
```

### 3. User.IsInRole() Runtime Checks

**C# Code:**
```csharp
public IActionResult ProcessLargeExpense(ExpenseRequest request)
{
    if (User.IsInRole("Director"))
    {
        // Approve large expense
        return Ok("Large expense approved");
    }
    return Forbid();
}
```

**Extracted Policy:**
- **WHO:** Director
- **WHAT:** expense
- **HOW:** approve
- **WHEN:** no amount limit

**Translated Cedar Policy:**
```cedar
permit (
    principal in Role::"Director",
    action == Action::"approve",
    resource in ResourceType::"expense"
);
```

### 4. Claims-Based Authorization

**C# Code:**
```csharp
[Authorize(Policy = "EmployeeOnly")]
public IActionResult ViewPayroll()
{
    var employeeNumber = User.FindFirst("EmployeeNumber")?.Value;
    // Return payroll for employee
}
```

Where the `EmployeeOnly` policy is defined as:
```csharp
services.AddAuthorization(options =>
{
    options.AddPolicy("EmployeeOnly", policy =>
        policy.RequireClaim("EmployeeNumber"));
});
```

**Extracted Policy:**
- **WHO:** Employee
- **WHAT:** payroll
- **HOW:** view
- **WHEN:** has valid employee number claim

**Translated Cedar Policy:**
```cedar
permit (
    principal in Role::"Employee",
    action == Action::"view",
    resource in ResourceType::"payroll"
)
when {
    principal has employeeNumber &&
    resource.employeeId == principal.employeeNumber
};
```

## How to Use

### 1. Extract Policies from C# Code

First, scan your C# repository to extract authorization policies:

```bash
curl -X POST "http://localhost:8000/api/v1/repositories/{repository_id}/scan"
```

The scanner will automatically detect:
- `[Authorize]` attributes
- `[PrincipalPermission]` attributes
- `User.IsInRole()` calls
- `User.HasClaim()` calls
- Policy-based authorization
- Custom authorization logic

### 2. Export Policy to Cedar Format

Once policies are extracted, export them to Cedar format:

**Via API:**
```bash
curl -X GET "http://localhost:8000/api/v1/policies/{policy_id}/export/cedar"
```

**Via UI:**
1. Navigate to the Policies page
2. Click "Export" on any policy card
3. Select "AWS Cedar" as the export format
4. Copy the generated Cedar policy or download as `.cedar` file

### 3. Deploy to AWS Verified Permissions

The generated Cedar policy can be deployed directly to AWS Verified Permissions:

```bash
aws verifiedpermissions create-policy \
  --policy-store-id ps-1234567890abcdef \
  --definition file://policy.cedar
```

## Semantic Equivalence

The translation service preserves the **semantic intent** of the original C# authorization logic:

- **WHO (Subject):** C# roles → Cedar principals
- **WHAT (Resource):** C# resources → Cedar resources
- **HOW (Action):** C# actions → Cedar actions
- **WHEN (Conditions):** C# conditionals → Cedar `when` clauses

### Example Semantic Mapping

| C# Authorization | Cedar Equivalent |
|-----------------|------------------|
| `[Authorize(Roles = "Manager")]` | `principal in Role::"Manager"` |
| `if (amount < 5000)` | `when { resource.amount < 5000 }` |
| `User.IsInRole("Director")` | `principal in Role::"Director"` |
| `User.HasClaim("Dept", "Finance")` | `principal.department == "Finance"` |
| `User.IsAuthenticated` | `principal.isAuthenticated == true` |

## Validation

The translation service automatically validates generated Cedar policies:

1. **Structural Validation:**
   - Must contain `permit` or `forbid` statement
   - Must define `principal`, `action`, and `resource`
   - Must end with semicolon (`;`)

2. **Semantic Validation:**
   - Verifies WHO/WHAT/HOW/WHEN elements are preserved
   - Ensures conditions are correctly translated

3. **Syntax Validation:**
   - Checks Cedar syntax correctness
   - Validates `when` clause structure

## Benefits

### 1. Zero Code Rewrite
Translate existing C# authorization logic without rewriting application code.

### 2. Semantic Equivalence
AI understands the *intent* of your authorization logic, not just the syntax.

### 3. AWS Integration
Deploy directly to AWS Verified Permissions for centralized policy management.

### 4. Audit Trail
Full audit logging of all translations for compliance and security reviews.

### 5. Multi-Format Support
Export to Cedar, OPA Rego, or custom JSON formats from the same extracted policy.

## Architecture

```
┌─────────────────┐
│   C# Code       │
│                 │
│ [Authorize]     │
│ User.IsInRole() │
│ HasClaim()      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ C# Scanner      │
│ (tree-sitter)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Policy Model    │
│ (WHO/WHAT/HOW/  │
│  WHEN)          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Translation     │
│ Service         │
│ (Claude Agent   │
│  SDK)           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Cedar Policy    │
│ permit/forbid   │
│ when clauses    │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ AWS Verified    │
│ Permissions     │
└─────────────────┘
```

## Configuration

### LLM Provider Setup

The translation service requires an LLM provider. For production, use AWS Bedrock or Azure OpenAI:

**AWS Bedrock:**
```bash
export LLM_PROVIDER=aws_bedrock
export AWS_BEDROCK_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
```

**Azure OpenAI:**
```bash
export LLM_PROVIDER=azure_openai
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_API_KEY=your-api-key
export AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment
```

**Development (Direct Anthropic API):**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Testing

The translation service includes comprehensive tests:

```bash
cd backend
pytest tests/test_translation_service.py -v
pytest tests/test_csharp_cedar_translation_e2e.py -v
```

## Troubleshooting

### Translation Fails with "Invalid Cedar Policy"

**Cause:** Generated policy doesn't meet Cedar syntax requirements.

**Solution:** Check that:
- Policy ends with semicolon
- All required fields (principal, action, resource) are present
- `when` clauses use correct Cedar syntax

### Semantic Mismatch Between C# and Cedar

**Cause:** Complex C# logic may not translate directly to Cedar.

**Solution:**
1. Review the generated Cedar policy
2. Manually adjust `when` clauses if needed
3. Test both C# and Cedar policies produce same authorization decisions

### LLM Provider Error

**Cause:** LLM provider not configured or credentials invalid.

**Solution:**
- Verify environment variables are set correctly
- For AWS Bedrock, ensure IAM permissions for Bedrock API
- For Azure OpenAI, verify endpoint URL and deployment name

## Future Enhancements

- [ ] Behavioral equivalence testing (automated test generation)
- [ ] Support for custom authorization attributes
- [ ] Cedar policy optimization recommendations
- [ ] Integration with AWS Verified Permissions deployment pipeline
- [ ] Support for Cedar policy schemas

## Related Documentation

- [Policy Translation Service](./TRANSLATION_SERVICE.md)
- [C# Scanner Service](./CSHARP_SCANNER.md)
- [AWS Cedar Language Specification](https://docs.cedarpolicy.com/)
- [AWS Verified Permissions](https://aws.amazon.com/verified-permissions/)
