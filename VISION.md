# Policy Miner: Vision & Story

## Executive Summary

**Policy Miner** helps enterprises migrate from **"Spaghetti" to "Lasagna"** architecture - transforming authorization chaos into centralized, governed policy management at scale.

## The Problem: Authorization Spaghetti

### Enterprise Reality
BigCorp is a typical Fortune 500 enterprise with:
- **5,000 applications**
  - 1,200 legacy Java/J2EE apps
  - 800 .NET applications
  - 600 Python microservices
  - 400 mainframe COBOL programs
  - 300 JavaScript/Node.js services
  - 200 acquired applications (various tech stacks)
  - 1,500 internal tools, scripts, and utilities
- Each app has 10-100 authorization rules
- **Total: 50,000 to 250,000 policies scattered everywhere**

### The Spaghetti Problem
Authorization logic is tangled throughout:
- **Application Code**: Hardcoded `if (user.hasRole("ADMIN"))` checks in Java, C#, Python, JavaScript, COBOL
- **Database Layer**: Authorization rules buried in stored procedures, triggers, row-level security policies
- **Frontend Components**: Duplicate permission checks in React/Angular/Vue components
- **Backend APIs**: More authorization logic in REST endpoints, GraphQL resolvers
- **Legacy Mainframes**: RACF/Top Secret/ACF2 security calls in COBOL programs

### Why This is Impossible to Manage

**Scenario**: "Who can access customer PII across our organization?"

**Without Policy Miner**:
- Must review 5,000 applications manually
- Each app has different authorization patterns
- Code is scattered across repos, databases, mainframes
- **Reality**: 6-12 months, $2M+ in consulting fees, still incomplete

**Business Impact**:
- ❌ **Compliance Audits**: Take months, are always outdated
- ❌ **Security Blindspots**: Can't identify overprivileged access
- ❌ **Change Paralysis**: Risk assessment takes too long
- ❌ **Breach Exposure**: Unknown attack surface
- ❌ **Technical Debt**: Can't modernize without understanding current rules
- ❌ **Audit Failures**: "We don't know who can access what"

### The Impossibility of Manual Approaches

At 5,000 applications scale:
- **Manual documentation**: 10 apps/week = 10 years to complete (first apps outdated by then)
- **Manual review**: 100 policies/day = 3-7 years of full-time work
- **App-by-app migration**: 1 app/week = 100 years to modernize
- **Traditional consulting**: $500/hour × 40,000 hours = $20M+ (and still manual)

**Conclusion**: You can't solve this with headcount. You need AI-powered automation.

---

## The Solution: AI-Powered Migration to Lasagna Architecture

### What is "Lasagna" Architecture?

**Spaghetti** (Current State):
- Tangled, intertwined authorization code
- Can't change one rule without affecting others
- Hard to see what policies exist
- Messy to modify
- Every application is its own authorization island

**Lasagna** (Target State):
- **Top Layer**: Centralized Policy Management (OPA, AWS Verified Permissions, Axiomatics)
- **Middle Layer**: Standardized Enforcement Points (policy decision points)
- **Bottom Layer**: Applications that delegate authorization decisions
- Clear separation of concerns
- Single source of truth
- Easy to audit and modify

### Organizational Data Model

```
Organization (Enterprise Tenant)
├── Division/Business Unit
│   ├── Application 1
│   │   ├── Policy A (extracted from Java code)
│   │   ├── Policy B (extracted from stored procedure)
│   │   └── Policy C (extracted from frontend)
│   ├── Application 2
│   │   ├── Policy D (extracted from Python API)
│   │   ├── Policy E (extracted from COBOL mainframe)
│   │   └── Policy F (extracted from .NET service)
│   └── Application 3
│       ├── Policy G
│       └── Policy H
└── [Repeat for all divisions]
```

**Key Principles**:
- **One Organization** = One enterprise tenant (complete data isolation)
- **Many Applications** = All systems across the organization (5,000+)
- **Many Policies per Application** = All authorization rules in that app's code/database
- **Goal**: Extract all policies → Centralize → Govern from single source of truth

---

## How Policy Miner Works

### Phase 1: Automated Discovery (Months 1-2)

**Challenge**: Find all authorization rules across 5,000 applications

**Solution**: Parallel AI-powered scanning
- Connect to Git repositories (GitHub, GitLab, Bitbucket, Azure DevOps)
- Connect to databases (PostgreSQL, SQL Server, Oracle, MySQL)
- Connect to mainframe systems (TN3270, COBOL parsers)
- Scan 10-50 applications simultaneously using containerized workers
- Stream processing for repositories with 100K+ LOC

**AI Extraction** (Claude Opus 4.5):
- Analyzes code to extract **Who/What/How/When**
  - **Who**: Users, roles, groups, attributes (subjects)
  - **What**: Resources being protected
  - **How**: Allowed/denied actions and permissions
  - **When**: Conditional rules, constraints, context
- Provides **Evidence**: Exact code snippets with file paths and line numbers
- Prevents hallucination through evidence validation

**Output**: Complete inventory of 50K-250K policies with evidence

**Example**:
```
Policy extracted from FinanceApp/src/ExpenseService.java:145-152

Subject: user.role == "MANAGER" OR user.role == "DIRECTOR"
Resource: Expense
Action: APPROVE
Condition: expense.amount < 5000 AND expense.department == user.department

Evidence:
File: src/main/java/com/bigcorp/finance/ExpenseService.java
Lines: 145-152
Code:
  if ((user.hasRole("MANAGER") || user.hasRole("DIRECTOR")) &&
      expense.getAmount() < 5000 &&
      expense.getDepartment().equals(user.getDepartment())) {
      approveExpense(expense);
  }
```

### Phase 2: AI Translation (Months 3-4)

**Challenge**: 5,000 apps use different languages, frameworks, patterns

**Solution**: Claude Agent SDK for intelligent translation

The SDK doesn't just extract - it **translates** policies to centralized formats:

#### Translation Example

**Source: Java Code (Spaghetti)**
```java
if (user.hasRole("ADMIN") ||
    (user.hasRole("MANAGER") && resource.getDepartment().equals(user.getDepartment()))) {
    // allow access
}
```

**Target: OPA Rego (Lasagna)**
```rego
package authz

allow {
    input.user.role == "ADMIN"
}

allow {
    input.user.role == "MANAGER"
    input.resource.department == input.user.department
}
```

**Or Target: AWS Verified Permissions Cedar**
```cedar
permit(
    principal in Role::"ADMIN",
    action,
    resource
);

permit(
    principal in Role::"MANAGER",
    action,
    resource
) when {
    resource.department == principal.department
};
```

#### Cross-Application Normalization

When 5,000 apps have different conventions:
- App 1: "admin" role
- App 2: "administrator" role
- App 3: "sysadmin" role
- App 4: "system_admin" role

**Claude Agent SDK**:
- Detects semantic equivalence
- Normalizes to standard taxonomy
- Maps variations to centralized role definitions
- Creates mapping documentation

**Output**:
- 50K-250K policies translated to OPA Rego (or Cedar, or custom JSON)
- Normalized role/resource taxonomy
- Translation mapping for audit trail

### Phase 3: AI Fixing & Conflict Resolution (Months 3-4)

**Challenge**: Policies have conflicts, gaps, and errors

**Solution**: Claude Agent SDK detects and repairs broken policies

#### Conflict Detection

**Example Conflict**:
```
Policy A (from ExpenseApp v1):
  Managers can approve expenses < $5000

Policy B (from ExpenseApp v2):
  Only Directors can approve expenses

Policy C (from FinancePortal):
  Managers can approve expenses < $10000 in their department
```

**Claude Agent SDK Analysis**:
- Detects contradiction between A and B
- Identifies threshold mismatch between A and C
- Recommends resolution strategy
- Generates unified policy

**Recommended Resolution**:
```rego
# Unified expense approval policy
allow {
    input.user.role == "DIRECTOR"
    input.action == "APPROVE_EXPENSE"
}

allow {
    input.user.role == "MANAGER"
    input.action == "APPROVE_EXPENSE"
    input.expense.amount < 5000
    input.expense.department == input.user.department
}
```

#### Security Gap Detection

**Example: Incomplete Logic**
```java
// Original (broken)
if (user.isManager()) {
    approve();
}
```

**Claude Agent SDK Detects**:
- Missing suspended user check
- Missing approval limit enforcement
- No department matching
- No audit logging

**Fixed Policy**:
```java
if (user.isManager() &&
    !user.isSuspended() &&
    expense.getAmount() < user.getApprovalLimit() &&
    expense.getDepartment().equals(user.getDepartment())) {
    auditLog.record("EXPENSE_APPROVED", user, expense);
    approve();
}
```

#### Common Issues Fixed by AI

1. **Always-true conditions**: `if (true || user.hasRole("ADMIN"))`
2. **Privilege escalation risks**: Missing role checks in critical paths
3. **Inconsistent enforcement**: Same resource protected differently
4. **Missing edge cases**: Null checks, suspended users, expired credentials
5. **Overly permissive**: `if (user != null)` granting access to everyone

**Output**:
- 10-20% of policies flagged for issues (5K-50K policies)
- 80% auto-fixed by AI
- 20% require human decision (complex conflicts)
- Conflict resolution recommendations

### Phase 4: Intelligent Review (Months 5-6)

**Challenge**: 50K-250K policies need human review - impossible to review all

**Solution**: AI-powered risk scoring and auto-approval

#### Multi-Dimensional Risk Scoring

Each policy gets scored on:
1. **Complexity Score** (0-100): How complex is the logic?
2. **Impact Score** (0-100): What's protected? (PII, financial data, admin functions)
3. **Confidence Score** (0-100): How confident is the AI extraction?
4. **Historical Score** (0-100): Have similar policies been approved before?

**Overall Risk** = Weighted combination

**Auto-Approval Logic**:
- **Low Risk** (score < 30): Auto-approve (30-40% of policies)
- **Medium Risk** (score 30-70): Queue for review
- **High Risk** (score > 70): Require senior security approval

#### Focus Human Effort

**Without Risk Scoring**:
- Review all 50K policies manually
- 100 policies/day = 500 days of work
- Reviewer fatigue leads to errors
- Can't prioritize critical systems

**With AI Risk Scoring**:
- Auto-approve 20K low-risk policies (40%)
- Review 20K medium-risk policies (40%)
- Deep review 10K high-risk policies (20%)
- Focus on critical apps first (top 100 applications)
- **Result**: 30K policies reviewed in 3 months

#### ML Learning from Approvals

As humans approve/reject policies, the AI learns:
- Which patterns are always approved → auto-approve similar ones
- Which issues cause rejection → flag similar policies
- Organization-specific preferences → adapt recommendations

**Output**:
- 30-40% policies auto-approved
- Remaining policies prioritized by risk
- Human review focused on high-value decisions
- Continuous learning improves over time

### Phase 5: Centralized Provisioning (Months 7-12)

**Challenge**: Push policies to PBAC platforms for enforcement

**Solution**: Multi-platform provisioning adapters

#### Supported PBAC Platforms

1. **Open Policy Agent (OPA)**
   - Policies converted to Rego format
   - Pushed via OPA Bundle API
   - Continuous sync on policy changes

2. **AWS Verified Permissions**
   - Policies converted to Cedar format
   - Created in AWS Policy Store
   - Integrated with AWS services

3. **Axiomatics/PlainID**
   - Policies converted to XACML or platform-specific format
   - Provisioned via REST API
   - Enterprise PBAC integration

4. **Custom REST API**
   - Flexible JSON schema
   - Configurable endpoints
   - Support for proprietary PBAC systems

#### Phased Rollout Strategy

**Month 7-8: Top 100 Critical Applications**
- Focus on highest-risk, highest-value apps
- Finance, HR, customer-facing systems
- Provision policies to OPA/AVP
- Refactor apps to call centralized decision point

**Month 9-10: Next 400 Applications**
- By business unit or division
- Grouped by tech stack for efficiency
- Continuous monitoring for issues

**Month 11-12: Next 500 Applications**
- Automated rollout workflows
- Self-service for application teams
- Validation and testing automation

**Year 2+: Remaining 4,000 Applications**
- Priority-based migration
- Legacy apps on slower timeline
- Continuous governance maintained

**Output**:
- Policies provisioned to centralized PBAC platform
- Applications refactored to call PBAC for decisions
- Lasagna architecture achieved for critical systems

### Phase 6: Code Refactoring Advisory (Ongoing)

**Challenge**: Apps still have hardcoded authorization - need to refactor

**Solution**: Claude Agent SDK generates refactoring code

#### Refactoring Example

**Original Code (Spaghetti)**:
```java
public void approveExpense(Expense expense, User user) {
    if (user.hasRole("MANAGER") &&
        expense.getAmount() < 5000 &&
        expense.getDepartment().equals(user.getDepartment())) {
        expense.setStatus(APPROVED);
        save(expense);
    } else {
        throw new UnauthorizedException();
    }
}
```

**AI-Generated Refactoring (Lasagna)**:
```java
public void approveExpense(Expense expense, User user) {
    // Call centralized policy decision point
    PolicyDecision decision = opaClient.authorize(
        subject: user,
        action: "APPROVE_EXPENSE",
        resource: expense
    );

    if (decision.isAllowed()) {
        expense.setStatus(APPROVED);
        save(expense);
    } else {
        throw new UnauthorizedException(decision.getReason());
    }
}
```

**AI-Generated Test Cases**:
```java
@Test
public void testManagerCanApproveWithinLimit() {
    User manager = createManager("dept-001");
    Expense expense = createExpense(4000, "dept-001");

    // Should succeed with both old and new implementation
    approveExpense(expense, manager);
    assertEquals(APPROVED, expense.getStatus());
}

@Test
public void testManagerCannotApproveOverLimit() {
    User manager = createManager("dept-001");
    Expense expense = createExpense(6000, "dept-001");

    // Should fail with both old and new implementation
    assertThrows(UnauthorizedException.class,
        () -> approveExpense(expense, manager));
}

// ... 10+ more test cases for edge cases
```

**Validation**:
- Run tests against original code → all pass
- Apply refactoring → all tests still pass
- **Behavioral equivalence proven**

**Output**:
- Refactored code for each policy
- Comprehensive test cases
- Side-by-side diff visualization
- Explanation of changes
- Pull request ready for review

### Phase 7: Continuous Governance (Year 2+)

**Challenge**: Developers add new spaghetti code - need continuous monitoring

**Solution**: Git webhooks + incremental scanning + auto-remediation

#### Change Detection Workflow

1. **Developer commits code** with new authorization logic
2. **Git webhook triggers** Policy Miner scan
3. **Incremental scan** analyzes only changed files
4. **New policy detected**: `if (user.hasRole("SUPER_ADMIN")) { ... }`
5. **Risk assessed**: High risk (new privileged role)
6. **Work item created**: "New inline authorization detected in CommitService.java"
7. **Security team notified**: Review required
8. **Options presented**:
   - Add to centralized policy store
   - Refactor to call OPA
   - Reject (require developer to use existing policy)

#### Continuous Sync

- Policy changes in code → auto-update centralized PBAC
- Policy changes in PBAC → generate code change advisories
- Bidirectional sync keeps systems aligned
- Audit trail of all changes

**Output**:
- No regression to spaghetti
- New policies automatically discovered
- Developers guided to use centralized policies
- Continuous improvement and learning

---

## The Claude Agent SDK Role

The SDK is the **brain** of Policy Miner - not just extracting, but actively **understanding**, **translating**, and **fixing** policies.

### Key Capabilities

#### 1. Semantic Understanding
- Understands **intent** behind code, not just syntax
- "This Java if-statement is checking expense approval authority"
- Maps code patterns to authorization concepts

#### 2. Cross-Language Translation
- Java → Rego → Cedar → JSON
- Preserves semantic meaning across formats
- Adapts to platform idioms and best practices

#### 3. Intelligent Conflict Resolution
- Detects contradictions across 5,000 apps
- Recommends merge strategies
- Explains trade-offs to humans

#### 4. Security Analysis
- Identifies privilege escalation risks
- Flags overly permissive policies
- Detects missing edge cases

#### 5. Code Generation
- Generates refactored code
- Creates comprehensive test cases
- Produces production-ready pull requests

#### 6. Continuous Learning
- Learns from human approvals/rejections
- Adapts to organization-specific patterns
- Improves accuracy over time

---

## Success Metrics

### Technical Metrics
- ✅ Extract policies from 5,000+ applications
- ✅ Achieve >85% accuracy in policy extraction (validated by human review)
- ✅ Auto-approve >30% of low-risk policies using ML
- ✅ Process repositories with 100K+ LOC without timeouts
- ✅ Zero secret leakage incidents
- ✅ Full audit trail of all AI interactions

### Business Metrics
- ✅ **Time to Compliance**: Audit queries answered in minutes (vs 6-12 months)
- ✅ **Cost Reduction**: $20M+ consulting costs avoided
- ✅ **Risk Reduction**: Complete authorization visibility
- ✅ **Change Velocity**: Policy updates in hours (vs months)
- ✅ **Developer Productivity**: Auto-generated refactoring code

### Architecture Metrics
- ✅ **Spaghetti → Lasagna**: Critical apps on centralized PBAC
- ✅ **Policy Centralization**: 50K-250K policies in single source of truth
- ✅ **Continuous Governance**: New spaghetti detected and remediated automatically

---

## Why This Matters

### The Bottom Line

At **5,000 applications** with **50K-250K authorization policies**, traditional approaches are impossible:
- Manual documentation: 10+ years
- Manual migration: 100+ years
- Consulting: $20M+ and still manual

**Policy Miner makes the impossible possible** through AI-powered automation:
- Months instead of years
- Millions saved instead of millions spent
- Complete visibility instead of blindspots
- Continuous governance instead of point-in-time audits

### From Chaos to Control

**Before Policy Miner**:
- ❌ "We don't know who can access what"
- ❌ Compliance audits take 6-12 months
- ❌ Can't change policies without breaking apps
- ❌ Security team flying blind
- ❌ Every app is an authorization island

**After Policy Miner**:
- ✅ Complete authorization inventory with evidence
- ✅ Compliance queries answered instantly
- ✅ Centralized policy management
- ✅ Proactive security monitoring
- ✅ **Lasagna architecture achieved**

This isn't just a tool - it's the **only way** to achieve authorization governance at enterprise scale.

---

## The Vision

**Short-term (Year 1)**: Extract, translate, centralize authorization policies across enterprise

**Medium-term (Year 2-3)**: Achieve lasagna architecture for majority of applications

**Long-term (Year 3+)**: Continuous governance as standard practice, zero spaghetti tolerance, AI-driven policy optimization

**Ultimate Goal**: **Every enterprise application delegates authorization to centralized PBAC**, making compliance trivial, security proactive, and change rapid.

From **5,000 authorization islands** to **one governed archipelago**.

From **spaghetti chaos** to **lasagna clarity**.

From **impossible** to **automated**.

That's Policy Miner.
