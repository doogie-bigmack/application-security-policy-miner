# PRD Story Analysis: Vision Alignment

## Executive Summary

Analyzed 56 stories in prd.json against the VISION.md to identify gaps and misalignments. The current stories cover **basic functionality well** but are **missing critical enterprise-scale and AI translation capabilities** that are central to the vision.

**Overall Assessment**: 60% aligned with vision, 40% gaps

---

## ✅ What's Well Covered (Strengths)

### 1. Core Discovery & Extraction
- ✅ Git repository integration (GitHub, GitLab, Bitbucket, Azure DevOps)
- ✅ Database connection support (PostgreSQL, SQL Server, Oracle, MySQL)
- ✅ Mainframe COBOL support
- ✅ Language parsers (Java, C#, Python, JavaScript)
- ✅ Evidence-based extraction with code snippets

### 2. Security Requirements
- ✅ Secret detection and redaction
- ✅ Private LLM endpoints (AWS Bedrock/Azure OpenAI)
- ✅ Encryption at rest and in transit
- ✅ Full audit logging
- ✅ Evidence validation to prevent hallucination

### 3. Policy Review & Risk Scoring
- ✅ Multi-dimensional risk scoring
- ✅ Policy review UI with Monaco editor
- ✅ Auto-approval based on historical patterns
- ✅ Risk visualization dashboard

### 4. Provisioning
- ✅ OPA provisioning with Rego format
- ✅ AWS Verified Permissions with Cedar format
- ✅ Axiomatics/PlainID integration
- ✅ Custom REST API support

### 5. Technical Infrastructure
- ✅ Docker containerization
- ✅ Cloud and on-premises deployment
- ✅ Streaming for large repositories
- ✅ Incremental scanning with git diff
- ✅ Multi-tenancy with isolation

---

## ❌ Critical Gaps (Missing Stories)

### 1. **Enterprise-Scale Organization Structure** 🔴 HIGH PRIORITY

**Gap**: Stories assume simple tenant → repository model, but vision requires **Organization → Many Applications → Many Policies** hierarchy.

**Missing Stories**:

```json
{
  "category": "functional",
  "description": "Organization Management - Create organization with divisions and business units",
  "steps": [
    "Login as system administrator",
    "Create new organization (BigCorp)",
    "Add divisions (Finance, Manufacturing, IT, Regional)",
    "Add business units within divisions",
    "Configure organizational hierarchy",
    "Verify hierarchy is displayed",
    "Assign users to divisions with appropriate roles"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Application Management - Register 5,000+ applications across organization",
  "steps": [
    "Navigate to Applications page",
    "Import application inventory from CSV (5,000+ apps)",
    "Assign applications to business units",
    "Set application metadata (criticality, tech stack, owner)",
    "Tag critical applications (top 100)",
    "Filter applications by division, tech stack, criticality",
    "Verify all 5,000 applications are registered",
    "View application hierarchy by organization"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Application-Policy Relationship - View policies grouped by application",
  "steps": [
    "Navigate to Applications page",
    "Select an application (e.g., ExpenseApp)",
    "View all policies belonging to this application",
    "Verify policies are grouped by source (code, database, frontend)",
    "Filter policies by risk level within application",
    "Export application-specific policy report",
    "Compare policies across multiple applications"
  ],
  "passes": false
}
```

**Impact**: Without these stories, the system can't demonstrate the Org → App → Policy structure that's central to managing 5,000 applications.

---

### 2. **Claude Agent SDK for Policy Translation** 🔴 HIGH PRIORITY

**Gap**: Current stories mention "conversion" generically. Vision emphasizes Claude Agent SDK **actively translating** policies with semantic understanding.

**Missing Stories**:

```json
{
  "category": "functional",
  "description": "Policy Translation - Claude Agent SDK translates Java code to OPA Rego",
  "steps": [
    "Extract policy from Java code (inline if-statement)",
    "Navigate to Policy Translation",
    "Select target format: OPA Rego",
    "Click 'Translate with Claude Agent SDK'",
    "Verify Claude Agent SDK analyzes semantic intent",
    "Review generated Rego policy",
    "Verify translation preserves logic (Who/What/How/When)",
    "Confirm package declaration and allow/deny rules are correct",
    "Test both original Java and translated Rego have same behavior"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Policy Translation - Claude Agent SDK translates C# to Cedar format",
  "steps": [
    "Extract policy from C# ASP.NET authorization attribute",
    "Select target format: AWS Cedar",
    "Click 'Translate with Claude Agent SDK'",
    "Verify Claude Agent SDK understands C# authorization semantics",
    "Review generated Cedar policy",
    "Confirm permit/forbid statements match original logic",
    "Validate Cedar policy syntax",
    "Test behavioral equivalence"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Policy Translation - Multi-format translation for single policy",
  "steps": [
    "Extract policy from Python Flask decorator",
    "Translate to OPA Rego",
    "Translate same policy to Cedar",
    "Translate same policy to custom JSON",
    "Verify all three translations are semantically equivalent",
    "Test all three formats produce same authorization decisions",
    "Document translation mappings for audit"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Cross-Application Normalization - Detect and normalize equivalent roles",
  "steps": [
    "Scan 10 applications with different role naming conventions",
    "Identify App1 uses 'admin', App2 uses 'administrator', App3 uses 'sysadmin'",
    "Claude Agent SDK detects semantic equivalence",
    "Navigate to Normalization Dashboard",
    "Review AI-suggested role mapping (admin ↔ administrator ↔ sysadmin)",
    "Approve normalization to standard taxonomy (ADMIN)",
    "Verify all policies are updated to use standard role names",
    "Confirm mapping is documented in audit trail"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Translation Quality - Verify semantic equivalence of translated policies",
  "steps": [
    "Extract complex policy with nested conditions from Java",
    "Translate to OPA Rego using Claude Agent SDK",
    "Generate test cases covering all decision paths",
    "Run test cases against original Java code",
    "Run same test cases against translated Rego policy",
    "Verify 100% match in authorization decisions",
    "Document any edge cases where translation differs",
    "Mark translation as semantically verified"
  ],
  "passes": false
}
```

**Impact**: Translation is the **core value proposition** of moving from spaghetti to lasagna. Without these stories, the AI translation capabilities aren't validated.

---

### 3. **Claude Agent SDK for Fixing Broken Policies** 🔴 HIGH PRIORITY

**Gap**: Vision emphasizes AI **actively fixing** broken, incomplete, or insecure policies. Current stories don't test this.

**Missing Stories**:

```json
{
  "category": "functional",
  "description": "Policy Fixing - Detect and fix incomplete authorization logic",
  "steps": [
    "Extract policy with incomplete logic (e.g., if (user.isManager()) { approve(); })",
    "Claude Agent SDK analyzes policy for gaps",
    "Identify missing checks (suspended user, approval limits, department matching)",
    "Review AI-generated fix with complete logic",
    "Compare original vs fixed policy side-by-side",
    "Approve AI fix",
    "Verify fixed policy includes all necessary checks",
    "Generate test cases to prove fix prevents security gaps"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Policy Fixing - Detect and flag privilege escalation risks",
  "steps": [
    "Extract policy with privilege escalation vulnerability",
    "Claude Agent SDK performs security analysis",
    "Detect missing role check in critical operation",
    "Flag policy as HIGH RISK with explanation",
    "Review AI recommendation to add authorization check",
    "Apply suggested fix",
    "Verify vulnerability is closed",
    "Add to security audit report"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Policy Fixing - Detect always-true conditions and overly permissive policies",
  "steps": [
    "Extract policy with always-true condition (e.g., if (true || user.hasRole('ADMIN')))",
    "Claude Agent SDK detects logical error",
    "Flag policy as defective",
    "Review AI explanation of issue",
    "Review AI-suggested fix (remove always-true condition)",
    "Apply fix",
    "Verify policy now has meaningful authorization check",
    "Log fix in audit trail"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Policy Fixing - Detect and fix inconsistent enforcement across applications",
  "steps": [
    "Scan 5 applications that protect same resource type (e.g., customer PII)",
    "Claude Agent SDK detects inconsistent authorization rules",
    "App1: Requires ADMIN role",
    "App2: Requires MANAGER role",
    "App3: No authorization check (security gap!)",
    "Flag inconsistency as HIGH RISK",
    "Review AI recommendation to standardize",
    "Apply standardized policy across all 5 apps",
    "Verify consistent enforcement"
  ],
  "passes": false
}
```

**Impact**: Fixing broken policies is what makes this system **intelligent** vs just extracting data. Without these stories, the AI's value-add isn't demonstrated.

---

### 4. **Parallel Scanning at Enterprise Scale** 🔴 HIGH PRIORITY

**Gap**: Current stories test single repository scanning. Vision requires scanning **10-50 applications in parallel** to handle 5,000 apps.

**Missing Stories**:

```json
{
  "category": "performance",
  "description": "Parallel Scanning - Scan 50 applications simultaneously",
  "steps": [
    "Register 50 applications across different tech stacks",
    "Navigate to Bulk Scan interface",
    "Select all 50 applications",
    "Click 'Start Parallel Scan'",
    "Verify 50 containerized workers are spawned",
    "Monitor parallel scan progress dashboard",
    "Verify scans complete in parallel (not sequential)",
    "Confirm total time < 2x single app scan time",
    "Review resource usage (CPU, memory, network)"
  ],
  "passes": false
}
```

```json
{
  "category": "performance",
  "description": "Enterprise-Scale Scanning - Process 1,000 applications in batches",
  "steps": [
    "Register 1,000 applications",
    "Configure scan orchestrator for batch processing",
    "Start bulk scan",
    "Verify applications are scanned in batches of 50",
    "Monitor queue depth and worker utilization",
    "Confirm all 1,000 apps are scanned",
    "Review total scan duration (target: < 1 week)",
    "Verify no timeouts or worker crashes"
  ],
  "passes": false
}
```

```json
{
  "category": "performance",
  "description": "Distributed Worker Management - Scale workers based on load",
  "steps": [
    "Start with 10 worker containers",
    "Submit 100 application scans",
    "Verify auto-scaling triggers when queue depth > threshold",
    "Confirm workers scale to 50 containers",
    "Monitor worker health and task distribution",
    "Verify failed workers are automatically restarted",
    "Confirm queue drains efficiently",
    "Verify workers scale down when queue empties"
  ],
  "passes": false
}
```

**Impact**: Without parallel scanning stories, the system can't prove it can handle 5,000 applications (would take years sequentially).

---

### 5. **Cross-Application Conflict Detection** 🟡 MEDIUM PRIORITY

**Gap**: Current conflict stories assume conflicts within one app. Vision requires **cross-application** conflict detection.

**Missing Stories**:

```json
{
  "category": "functional",
  "description": "Cross-Application Conflicts - Detect contradictory policies across apps",
  "steps": [
    "Scan ExpenseApp v1 (extracted policy: Managers approve < $5000)",
    "Scan ExpenseApp v2 (extracted policy: Only Directors approve)",
    "Scan FinancePortal (extracted policy: Managers approve < $10000)",
    "Navigate to Cross-Application Conflicts",
    "Verify conflict is detected across all 3 applications",
    "Review AI analysis explaining contradiction",
    "Review AI-recommended unified policy",
    "Apply unified policy to all 3 applications",
    "Verify conflict is resolved organization-wide"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Cross-Application Duplication - Detect duplicate policies across apps",
  "steps": [
    "Scan 20 applications",
    "Claude Agent SDK detects 5 applications have identical expense approval logic",
    "Navigate to Duplicate Policies Dashboard",
    "Review list of duplicate policies",
    "Select duplicates to consolidate",
    "Create single centralized policy",
    "Link all 5 applications to centralized policy",
    "Verify deduplication reduces policy count by 80%"
  ],
  "passes": false
}
```

**Impact**: Cross-application analysis is key to centralizing policies from 5,000 apps. Without it, each app is still an island.

---

### 6. **Spaghetti to Lasagna Architecture Verification** 🟡 MEDIUM PRIORITY

**Gap**: No stories explicitly test the **architectural migration** from spaghetti to lasagna.

**Missing Stories**:

```json
{
  "category": "functional",
  "description": "Lasagna Architecture - Verify application calls centralized PBAC",
  "steps": [
    "Identify application with inline authorization checks (spaghetti)",
    "Extract policies and provision to OPA",
    "Refactor application to call OPA decision point",
    "Deploy refactored application",
    "Trigger authorization check in application",
    "Verify application calls OPA (not inline code)",
    "Confirm OPA returns authorization decision",
    "Verify application enforces OPA decision",
    "Measure latency of centralized check vs inline check"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Spaghetti Reduction Metrics - Measure inline authorization elimination",
  "steps": [
    "Scan application before migration (count inline auth checks)",
    "Record baseline: 150 inline authorization checks",
    "Centralize policies to OPA",
    "Refactor application to call OPA",
    "Rescan application after migration",
    "Verify inline checks reduced to 0",
    "Calculate spaghetti reduction: 100%",
    "Display reduction metrics on dashboard"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Continuous Governance - Detect new spaghetti code being added",
  "steps": [
    "Developer commits new code with inline authorization check",
    "Git webhook triggers Policy Miner scan",
    "Incremental scan detects new inline authorization",
    "System flags as 'NEW SPAGHETTI DETECTED'",
    "Create work item for security team review",
    "Notify developer: 'Use centralized PBAC instead'",
    "Provide refactoring suggestion",
    "Track spaghetti prevention metrics"
  ],
  "passes": false
}
```

**Impact**: The spaghetti → lasagna transformation is the **core value proposition**. Without stories proving this works, the vision isn't validated.

---

### 7. **Phased Rollout Strategy** 🟡 MEDIUM PRIORITY

**Gap**: No stories for prioritizing critical apps or managing migration in phases.

**Missing Stories**:

```json
{
  "category": "functional",
  "description": "Phased Rollout - Prioritize top 100 critical applications",
  "steps": [
    "Navigate to Applications page (5,000 apps registered)",
    "Filter by criticality: HIGH",
    "Review top 100 critical applications (Finance, HR, customer-facing)",
    "Create migration wave: 'Phase 1 - Critical Apps'",
    "Add top 100 apps to Phase 1",
    "Start bulk scan for Phase 1 apps only",
    "Monitor Phase 1 progress dashboard",
    "Provision Phase 1 policies to OPA",
    "Track Phase 1 completion: 100/100 apps migrated"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Phased Rollout - Group applications by business unit",
  "steps": [
    "Create migration wave: 'Phase 2 - Finance Division'",
    "Add all Finance Division applications (200 apps)",
    "Start bulk scan for Phase 2",
    "Provision Finance policies to OPA",
    "Validate policies with Finance team",
    "Approve for production rollout",
    "Track Phase 2 completion",
    "Create Phase 3 for Manufacturing Division"
  ],
  "passes": false
}
```

**Impact**: Phased rollout is essential for managing 5,000 apps. Without it, migration is all-or-nothing (impossible at scale).

---

### 8. **Policy Translation Format Support** 🟢 LOW PRIORITY

**Gap**: Stories mention Cedar for AWS Verified Permissions, but should be more explicit about translation vs just provisioning.

**Enhancement Needed**: Existing AWS Verified Permissions story (line 198-208) should emphasize **Cedar translation by Claude Agent SDK**, not just provisioning.

**Current**:
```json
"Verify policies are converted to Cedar format"
```

**Should Be**:
```json
"Click 'Translate to Cedar using Claude Agent SDK'",
"Verify Claude Agent SDK translates policy semantics to Cedar",
"Review generated Cedar permit/forbid statements",
"Confirm translation preserves original authorization logic",
"Validate Cedar syntax and semantics"
```

---

### 9. **Bulk Operations at Scale** 🟡 MEDIUM PRIORITY

**Gap**: Most stories test single-item operations. At 5,000 apps with 250K policies, bulk operations are critical.

**Missing Stories**:

```json
{
  "category": "functional",
  "description": "Bulk Policy Approval - Approve 10,000 low-risk policies at once",
  "steps": [
    "Navigate to Policy Review page",
    "Filter by risk level: LOW (showing 10,000 policies)",
    "Select all low-risk policies",
    "Click 'Bulk Approve'",
    "Confirm bulk approval operation",
    "Monitor progress (10,000 policies being approved)",
    "Verify all 10,000 policies status = APPROVED",
    "Review bulk approval audit log"
  ],
  "passes": false
}
```

```json
{
  "category": "functional",
  "description": "Bulk Provisioning - Provision 5,000 policies to OPA in batch",
  "steps": [
    "Select 5,000 approved policies",
    "Click 'Bulk Provision to OPA'",
    "Verify policies are translated in parallel batches",
    "Monitor provisioning progress",
    "Confirm all 5,000 policies pushed to OPA",
    "Verify OPA policy bundle updated",
    "Test sample policies in OPA for correctness"
  ],
  "passes": false
}
```

**Impact**: Without bulk operations, managing 250K policies is impractical (would take months of clicking).

---

### 10. **Vector Similarity Search for Policy Comparison** 🟢 LOW PRIORITY

**Gap**: Vision mentions pgvector for finding similar policies, but no stories test this.

**Missing Stories**:

```json
{
  "category": "functional",
  "description": "Similar Policy Detection - Find policies semantically similar to current policy",
  "steps": [
    "Select a policy to review",
    "Click 'Find Similar Policies'",
    "System uses pgvector embeddings to search",
    "Review list of similar policies across all applications",
    "Verify similarity scores are displayed",
    "Compare similar policies side-by-side",
    "Identify candidates for consolidation",
    "Mark policies as duplicates for deduplication"
  ],
  "passes": false
}
```

**Impact**: Helps consolidate duplicate policies across 5,000 apps, reducing policy sprawl.

---

## 📊 Summary of Gaps

| Category | Current Stories | Missing Stories | Priority |
|----------|----------------|----------------|----------|
| Organization Structure | 0 | 3 | 🔴 HIGH |
| Claude SDK Translation | 0 | 5 | 🔴 HIGH |
| Claude SDK Policy Fixing | 0 | 4 | 🔴 HIGH |
| Parallel Scanning | 0 | 3 | 🔴 HIGH |
| Cross-App Conflicts | 1 | 2 | 🟡 MEDIUM |
| Spaghetti→Lasagna Verification | 0 | 3 | 🟡 MEDIUM |
| Phased Rollout | 0 | 2 | 🟡 MEDIUM |
| Bulk Operations | 0 | 2 | 🟡 MEDIUM |
| Vector Similarity | 0 | 1 | 🟢 LOW |
| **TOTAL** | **56** | **25** | **81 Total** |

---

## 🎯 Recommended Actions

### Immediate (Before Development Starts)

1. **Add 12 HIGH PRIORITY stories** (Organization Structure, Translation, Fixing, Parallel Scanning)
   - These are **core to the vision** and must be validated

2. **Enhance existing AWS Verified Permissions story** to emphasize Cedar translation by Claude Agent SDK

3. **Update conflict resolution story** (line 110-120) to include cross-application conflict example

### Short-term (During MVP Development)

4. **Add 9 MEDIUM PRIORITY stories** (Cross-app conflicts, Lasagna verification, Phased rollout, Bulk ops)
   - These prove the system works at enterprise scale

### Long-term (Post-MVP)

5. **Add 1 LOW PRIORITY story** (Vector similarity)
   - Nice to have for policy consolidation

---

## 📝 Story Template for New Stories

When adding missing stories, use this format:

```json
{
  "category": "functional|performance|integration|quality",
  "description": "Brief description emphasizing Claude Agent SDK role",
  "steps": [
    "Step 1 - Action verb + clear outcome",
    "Step 2 - Verify AI behavior, not just UI",
    "Step 3 - Confirm semantic correctness",
    "...",
    "Final step - Verify end-to-end behavior"
  ],
  "passes": false
}
```

**Key Principles**:
- Emphasize **Claude Agent SDK intelligence** (translation, fixing, analysis)
- Test **semantic equivalence**, not just syntax
- Verify **cross-application** capabilities at scale
- Prove **spaghetti → lasagna** transformation
- Validate **enterprise scale** (1000s of apps, 100Ks of policies)

---

## ✅ Conclusion

**Current PRD**: Good coverage of basic functionality (discovery, extraction, provisioning, UI)

**Critical Gaps**: Missing enterprise-scale operations, Claude Agent SDK translation/fixing capabilities, cross-application analysis, and spaghetti→lasagna architectural verification

**Recommendation**: Add 25 new stories focusing on:
1. **Claude Agent SDK as the intelligent core** (not just data extraction)
2. **Enterprise scale** (5,000 apps, parallel processing, bulk operations)
3. **Architectural transformation** (spaghetti → lasagna verification)
4. **Cross-application governance** (conflicts, normalization, consolidation)

**Impact of Adding These Stories**:
- Validates the complete vision
- Proves AI translation/fixing capabilities
- Demonstrates enterprise-scale feasibility
- Ensures spaghetti→lasagna transformation works

Without these stories, the system risks being **just a policy extractor** instead of an **intelligent enterprise policy migration platform**.
