"""Service for detecting and fixing incomplete authorization logic."""

import json
from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_fix import FixSeverity, FixStatus, PolicyFix
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger(__name__)


class PolicyFixingService:
    """Service for analyzing and fixing security gaps in authorization policies."""

    def __init__(self, db: Session, tenant_id: str | None = None):
        """Initialize service."""
        self.db = db
        self.tenant_id = tenant_id or "default"
        self.llm_provider = get_llm_provider()

    async def analyze_policy(self, policy_id: int) -> PolicyFix | None:
        """Analyze a policy for security gaps and generate a fix.

        Args:
            policy_id: ID of the policy to analyze

        Returns:
            PolicyFix if security gaps found, None if policy is complete

        Raises:
            ValueError: If policy not found
        """
        # Get policy
        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        logger.info("analyzing_policy", policy_id=policy_id)

        # Analyze policy with AI
        analysis_result = await self._analyze_policy_with_ai(policy)

        # If no gaps found, return None
        if not analysis_result.get("has_gaps", False):
            logger.info("no_security_gaps_found", policy_id=policy_id)
            return None

        # Generate attack scenario for privilege escalation risks
        attack_scenario = None
        gap_type = analysis_result.get("gap_type", "incomplete_logic")
        if gap_type == "privilege_escalation":
            attack_scenario = await self._generate_attack_scenario(policy, analysis_result)

        # Create policy fix record
        policy_fix = PolicyFix(
            policy_id=policy_id,
            tenant_id=self.tenant_id,
            security_gap_type=gap_type,
            severity=self._parse_severity(analysis_result.get("severity", "medium")),
            gap_description=analysis_result.get("gap_description", "Security gaps detected"),
            missing_checks=json.dumps(analysis_result.get("missing_checks", [])),
            original_policy=json.dumps(self._policy_to_dict(policy)),
            fixed_policy=json.dumps(analysis_result.get("fixed_policy", {})),
            fix_explanation=analysis_result.get("fix_explanation", ""),
            attack_scenario=attack_scenario,
            status=FixStatus.PENDING,
        )

        self.db.add(policy_fix)
        self.db.commit()
        self.db.refresh(policy_fix)

        logger.info(
            "policy_fix_created",
            fix_id=policy_fix.id,
            policy_id=policy_id,
            severity=policy_fix.severity,
            gap_type=policy_fix.security_gap_type,
        )

        return policy_fix

    def _detect_always_true_conditions(self, policy: Policy) -> str:
        """Detect always-true conditions programmatically.

        Args:
            policy: Policy to analyze

        Returns:
            String with detection results to include in AI prompt
        """
        always_true_patterns = []

        # Check conditions field
        conditions = policy.conditions or ""
        conditions_lower = conditions.lower()

        # Pattern 1: Boolean literals with OR
        if "true ||" in conditions_lower or "|| true" in conditions_lower:
            always_true_patterns.append("Boolean literal with OR operator detected (e.g., 'true || x')")

        # Pattern 2: Common tautologies
        if "1 == 1" in conditions or "1==1" in conditions:
            always_true_patterns.append("Redundant comparison detected (1 == 1)")

        if "true ==" in conditions_lower or "== true" in conditions_lower:
            always_true_patterns.append("Redundant boolean comparison detected")

        # Pattern 3: Check evidence code for always-true patterns
        if policy.evidence:
            for evidence in policy.evidence:
                code = evidence.code_snippet or ""
                code_lower = code.lower()

                if "if (true" in code_lower or "if(true" in code_lower:
                    always_true_patterns.append(f"Always-true condition in {evidence.file_path}:{evidence.line_start}")

                if "|| true)" in code_lower or "true ||" in code_lower:
                    always_true_patterns.append(f"Boolean literal with OR in {evidence.file_path}:{evidence.line_start}")

        if always_true_patterns:
            patterns_text = "\n- ".join(always_true_patterns)
            return f"""**⚠️ ALERT: Potential Always-True Conditions Detected:**
- {patterns_text}

These patterns suggest the authorization logic may be defective and always allows access regardless of actual conditions."""
        return ""

    async def _analyze_policy_with_ai(self, policy: Policy) -> dict:
        """Analyze policy for security gaps using AI.

        Args:
            policy: Policy to analyze

        Returns:
            Dictionary with analysis results
        """
        # First, check for always-true conditions programmatically
        always_true_detection = self._detect_always_true_conditions(policy)

        # Build analysis prompt
        prompt = f"""You are a security expert analyzing authorization policies for security gaps and incomplete logic.

**Policy to Analyze:**
- Subject (Who): {policy.subject}
- Resource (What): {policy.resource}
- Action (How): {policy.action}
- Conditions (When): {policy.conditions or "None"}
- Description: {policy.description or "None"}

**Evidence Code Snippets:**
{self._format_evidence(policy)}

{always_true_detection}

**Your Task:**
Analyze this authorization policy for security gaps, incomplete logic, and missing checks. Common issues include:

1. **Incomplete Logic**: Missing important security checks (e.g., user suspension status, approval limits, department matching)
2. **Privilege Escalation Risks**: Missing role checks that could allow unauthorized access
3. **Always-True Conditions**: Logic errors that make conditions always evaluate to true (e.g., `if (true || condition)`, `if (1 == 1)`, `if (condition || !condition)`)
4. **Inconsistent Enforcement**: Missing checks that should be consistent with similar policies

**IMPORTANT: Pay special attention to always-true conditions. Look for:**
- Boolean literals in OR expressions: `true || x` is always true
- Tautologies: `x || !x` is always true
- Redundant comparisons: `1 == 1` is always true
- Conditions that cannot fail regardless of input
- Logic that makes authorization checks meaningless

**Analysis Requirements:**
1. Identify if there are any security gaps (YES or NO)
2. If YES, classify the gap type: incomplete_logic, privilege_escalation, always_true, or inconsistent_enforcement
3. Determine severity: low, medium, high, or critical
4. List all missing security checks
5. Generate a complete fixed policy with all necessary checks
6. Explain what was missing and how the fix addresses it

**Output Format:**
Return ONLY a valid JSON object with this structure:
{{
  "has_gaps": true/false,
  "gap_type": "incomplete_logic" | "privilege_escalation" | "always_true" | "inconsistent_enforcement",
  "severity": "low" | "medium" | "high" | "critical",
  "gap_description": "Clear description of what security gaps exist",
  "missing_checks": [
    "Check user suspension status",
    "Verify approval amount limits",
    "Ensure department matching"
  ],
  "fixed_policy": {{
    "subject": "Manager (active, not suspended)",
    "resource": "Expense Report",
    "action": "approve",
    "conditions": "amount < manager.approvalLimit AND user.department == request.department AND user.status == 'active'"
  }},
  "fix_explanation": "The original policy allowed any manager to approve any expense report without checking: 1) User suspension status, 2) Approval amount limits, 3) Department boundaries. The fixed policy adds all these necessary security checks."
}}

If no security gaps are found, return:
{{
  "has_gaps": false
}}

Analyze the policy and return ONLY the JSON object, no other text.
"""

        # Call LLM
        response = await self.llm_provider.create_message(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        # Parse JSON response
        try:
            # Extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                result = json.loads(json_str)
                return result
        except json.JSONDecodeError as e:
            logger.warning("failed_to_parse_ai_response", error=str(e), response=response[:500])
            # Fallback: assume no gaps if parsing fails
            return {"has_gaps": False}

        return {"has_gaps": False}

    def _format_evidence(self, policy: Policy) -> str:
        """Format evidence for AI prompt."""
        if not policy.evidence:
            return "No code evidence available"

        evidence_parts = []
        for i, evidence in enumerate(policy.evidence[:3], 1):  # Limit to first 3 evidence items
            evidence_parts.append(f"Evidence {i} ({evidence.file_path}:{evidence.line_start}-{evidence.line_end}):\n```\n{evidence.code_snippet}\n```")

        return "\n\n".join(evidence_parts)

    def _policy_to_dict(self, policy: Policy) -> dict:
        """Convert policy to dictionary."""
        return {
            "id": policy.id,
            "subject": policy.subject,
            "resource": policy.resource,
            "action": policy.action,
            "conditions": policy.conditions,
            "description": policy.description,
            "risk_level": policy.risk_level.value if policy.risk_level else None,
        }

    def _parse_severity(self, severity_str: str) -> FixSeverity:
        """Parse severity string to enum."""
        severity_map = {
            "low": FixSeverity.LOW,
            "medium": FixSeverity.MEDIUM,
            "high": FixSeverity.HIGH,
            "critical": FixSeverity.CRITICAL,
        }
        return severity_map.get(severity_str.lower(), FixSeverity.MEDIUM)

    async def generate_test_cases(self, fix_id: int) -> PolicyFix:
        """Generate test cases to prove the fix prevents security gaps.

        Args:
            fix_id: ID of the policy fix

        Returns:
            Updated policy fix with test cases

        Raises:
            ValueError: If fix not found
        """
        policy_fix = self.get_fix(fix_id)
        if not policy_fix:
            raise ValueError(f"PolicyFix {fix_id} not found")

        # Generate test cases with AI
        test_cases_json = await self._generate_test_cases_ai(policy_fix)

        # Store test cases
        policy_fix.test_cases = test_cases_json
        self.db.commit()
        self.db.refresh(policy_fix)

        logger.info("test_cases_generated", fix_id=fix_id)
        return policy_fix

    async def _generate_test_cases_ai(self, policy_fix: PolicyFix) -> str:
        """Generate test cases using AI.

        Args:
            policy_fix: PolicyFix to generate test cases for

        Returns:
            JSON string of test cases
        """
        original_policy = json.loads(policy_fix.original_policy)
        fixed_policy = json.loads(policy_fix.fixed_policy)

        prompt = f"""You are a security test engineer generating test cases to prove a policy fix prevents security gaps.

**Original Policy (with security gaps):**
- Subject: {original_policy.get('subject')}
- Resource: {original_policy.get('resource')}
- Action: {original_policy.get('action')}
- Conditions: {original_policy.get('conditions') or 'None'}

**Fixed Policy (with complete security checks):**
- Subject: {fixed_policy.get('subject')}
- Resource: {fixed_policy.get('resource')}
- Action: {fixed_policy.get('action')}
- Conditions: {fixed_policy.get('conditions') or 'None'}

**Security Gaps Addressed:**
{policy_fix.gap_description}

**Missing Checks Added:**
{policy_fix.missing_checks}

**Your Task:**
Generate comprehensive test cases that demonstrate:
1. The original policy has security vulnerabilities
2. The fixed policy prevents these vulnerabilities
3. The fix maintains correct functionality for legitimate cases

**Test Case Requirements:**
- At least 8-10 test cases
- Cover attack scenarios that exploit the security gaps
- Cover legitimate use cases that should still work
- Include edge cases and boundary conditions
- Show before/after behavior comparison

**Output Format:**
Return ONLY a valid JSON array:
[
  {{
    "name": "Test case name",
    "scenario": "Description of what is being tested",
    "input": {{
      "user": {{"role": "manager", "status": "active", "department": "finance"}},
      "resource": {{"type": "expense_report", "amount": 3000, "department": "finance"}},
      "action": "approve"
    }},
    "expected_original": "ALLOWED",
    "expected_fixed": "ALLOWED",
    "reasoning": "Legitimate case: Active manager approving expense within limits for same department"
  }},
  {{
    "name": "Suspended user exploit",
    "scenario": "Attempt by suspended user to approve expense",
    "input": {{
      "user": {{"role": "manager", "status": "suspended", "department": "finance"}},
      "resource": {{"type": "expense_report", "amount": 3000, "department": "finance"}},
      "action": "approve"
    }},
    "expected_original": "ALLOWED",
    "expected_fixed": "DENIED",
    "reasoning": "Security gap: Original policy doesn't check suspension status, fixed policy blocks suspended users"
  }}
]

Generate comprehensive test cases and return ONLY the JSON array, no other text.
"""

        # Call LLM
        response = await self.llm_provider.create_message(
            prompt=prompt,
            max_tokens=3000,
            temperature=0.3,
        )

        # Extract JSON from response
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                # Validate JSON
                test_cases = json.loads(json_str)
                if isinstance(test_cases, list):
                    return json.dumps(test_cases, indent=2)
        except json.JSONDecodeError:
            logger.warning("test_cases_json_parse_failed", response_length=len(response))

        # Fallback
        return json.dumps([{"error": "Failed to parse test cases from AI response"}])

    async def _generate_attack_scenario(self, policy: Policy, analysis_result: dict) -> str:
        """Generate detailed attack scenario for privilege escalation vulnerability.

        Args:
            policy: Policy with privilege escalation risk
            analysis_result: AI analysis result containing gap details

        Returns:
            Detailed attack scenario description
        """
        prompt = f"""You are a security researcher creating a detailed attack scenario that demonstrates a privilege escalation vulnerability.

**Vulnerable Policy:**
- Subject (Who): {policy.subject}
- Resource (What): {policy.resource}
- Action (How): {policy.action}
- Conditions (When): {policy.conditions or "None"}

**Security Gap:**
{analysis_result.get("gap_description", "Missing authorization checks")}

**Missing Checks:**
{json.dumps(analysis_result.get("missing_checks", []), indent=2)}

**Your Task:**
Create a detailed, step-by-step attack scenario that demonstrates how an attacker could exploit this privilege escalation vulnerability. Include:

1. **Attacker Profile**: Who the attacker is (role, current privileges)
2. **Attack Goal**: What unauthorized access the attacker is trying to gain
3. **Attack Steps**: Detailed step-by-step instructions
4. **Vulnerability Exploited**: Which missing check enables this attack
5. **Impact**: What damage or unauthorized actions become possible
6. **Prevention**: How the fix prevents this attack

Make it concrete and specific to this policy. Use realistic examples.

**Example Format:**
### Attack Scenario: Privilege Escalation via Missing Role Validation

**Attacker Profile:**
- Name: Alice (Standard User)
- Current Role: Employee
- Current Privileges: Can view own expense reports
- Target Privileges: Manager-level expense approval authority

**Attack Goal:**
Gain unauthorized ability to approve high-value expense reports without proper manager role.

**Attack Steps:**
1. Alice discovers the expense approval endpoint accepts requests from any authenticated user
2. She crafts a request to approve a $50,000 expense report
3. The system checks only if user is authenticated (no role check)
4. The request succeeds despite Alice not being a manager
5. Alice can now approve unlimited expense reports, including fraudulent ones

**Vulnerability Exploited:**
The policy checks if user.isAuthenticated() but never validates if user.hasRole('MANAGER'). This allows any authenticated user to perform manager-only actions.

**Impact:**
- Complete bypass of expense approval workflow
- Potential for massive financial fraud
- Insider threat: employees can self-approve fraudulent expenses
- Audit trail exists but shows unauthorized approvals as "legitimate"

**Prevention:**
The fix adds explicit role validation: user.hasRole('MANAGER') AND user.department == expense.department. This ensures only authorized managers in the correct department can approve expenses.

Now create a detailed attack scenario for the given policy. Be specific and realistic.
"""

        # Call LLM
        response = await self.llm_provider.create_message(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.5,
        )

        return response.strip()

    def get_fix(self, fix_id: int) -> PolicyFix | None:
        """Get a policy fix by ID."""
        query = self.db.query(PolicyFix).filter(PolicyFix.id == fix_id)

        if self.tenant_id != "default":
            query = query.filter(PolicyFix.tenant_id == self.tenant_id)

        return query.first()

    def list_fixes(
        self,
        policy_id: int | None = None,
        status: FixStatus | None = None,
        severity: FixSeverity | None = None,
    ) -> list[PolicyFix]:
        """List policy fixes with optional filtering."""
        query = self.db.query(PolicyFix)

        if self.tenant_id != "default":
            query = query.filter(PolicyFix.tenant_id == self.tenant_id)

        if policy_id:
            query = query.filter(PolicyFix.policy_id == policy_id)

        if status:
            query = query.filter(PolicyFix.status == status)

        if severity:
            query = query.filter(PolicyFix.severity == severity)

        return query.order_by(PolicyFix.created_at.desc()).all()

    def update_fix_status(
        self,
        fix_id: int,
        status: FixStatus,
        reviewed_by: str | None = None,
        review_comment: str | None = None,
    ) -> PolicyFix | None:
        """Update fix status after review."""
        policy_fix = self.get_fix(fix_id)
        if not policy_fix:
            return None

        policy_fix.status = status
        if reviewed_by:
            policy_fix.reviewed_by = reviewed_by
        if review_comment:
            policy_fix.review_comment = review_comment
        if status in [FixStatus.REVIEWED, FixStatus.APPLIED, FixStatus.REJECTED]:
            policy_fix.reviewed_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(policy_fix)

        logger.info("fix_status_updated", fix_id=fix_id, status=status)
        return policy_fix

    def delete_fix(self, fix_id: int) -> bool:
        """Delete a policy fix."""
        policy_fix = self.get_fix(fix_id)
        if not policy_fix:
            return False

        self.db.delete(policy_fix)
        self.db.commit()

        logger.info("fix_deleted", fix_id=fix_id)
        return True
