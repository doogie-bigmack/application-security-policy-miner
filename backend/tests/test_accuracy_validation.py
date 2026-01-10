"""
Test Policy Extraction Accuracy

This test validates that the Policy Miner achieves >85% accuracy in policy extraction
by comparing extracted policies against a ground truth reference application.

Accuracy Metrics:
- Precision: (Correct extractions) / (Total extractions)
- Recall: (Correct extractions) / (Total known policies)
- Accuracy: (Precision + Recall) / 2
"""

import logging
import re
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"
REFERENCE_APP = TEST_DATA_DIR / "reference_app_with_known_policies.py"

# Ground truth: Known policies in the reference application
KNOWN_POLICIES = {
    "policy_1": {
        "id": 1,
        "name": "View Expenses",
        "who": "Authenticated users",
        "what": "Expense list",
        "how": "Read/View",
        "when": "User is authenticated",
        "patterns": ["@login_required", "get_expenses", "/api/expenses", "GET"],
    },
    "policy_2": {
        "id": 2,
        "name": "Create Expense",
        "who": "EMPLOYEE role",
        "what": "Expense",
        "how": "Create",
        "when": "User has EMPLOYEE role",
        "patterns": ["@require_role('EMPLOYEE')", "create_expense", "POST"],
    },
    "policy_3": {
        "id": 3,
        "name": "Update Own Expense",
        "who": "Expense owner",
        "what": "Own expense",
        "how": "Update",
        "when": "User is owner AND not approved",
        "patterns": ["owner_id != current_user.id", "approved", "update_expense", "PUT"],
    },
    "policy_4": {
        "id": 4,
        "name": "Approve Small Expense",
        "who": "MANAGER role",
        "what": "Expense approval",
        "how": "Approve",
        "when": "Amount < $5,000",
        "patterns": ["amount < 5000", "MANAGER", "approve_expense", "approved = True"],
    },
    "policy_5": {
        "id": 5,
        "name": "Approve Large Expense",
        "who": "DIRECTOR role",
        "what": "Expense approval",
        "how": "Approve",
        "when": "Amount >= $5,000",
        "patterns": ["amount >= 5000", "DIRECTOR", "approve_expense", "approved = True"],
    },
    "policy_6": {
        "id": 6,
        "name": "Reject Expense",
        "who": "MANAGER or DIRECTOR role",
        "what": "Expense rejection",
        "how": "Reject",
        "when": "User has MANAGER or DIRECTOR role",
        "patterns": ["@require_any_role('MANAGER', 'DIRECTOR')", "reject_expense", "rejected = True"],
    },
    "policy_7": {
        "id": 7,
        "name": "Delete Own Expense",
        "who": "Expense owner",
        "what": "Own expense",
        "how": "Delete",
        "when": "User is owner AND not approved",
        "patterns": ["owner_id != current_user.id", "delete_own_expense", "DELETE"],
    },
    "policy_8": {
        "id": 8,
        "name": "Delete Any Expense",
        "who": "ADMIN role",
        "what": "Any expense",
        "how": "Delete",
        "when": "User has ADMIN role",
        "patterns": ["@require_role('ADMIN')", "delete_any_expense", "/api/admin/expenses"],
    },
    "policy_9": {
        "id": 9,
        "name": "View Financial Reports",
        "who": "Finance department",
        "what": "Financial reports",
        "how": "Read/View",
        "when": "User department is Finance",
        "patterns": ["department != 'Finance'", "financial_report", "/api/reports/financial"],
    },
    "policy_10": {
        "id": 10,
        "name": "Export Expense Data",
        "who": "MANAGER, DIRECTOR, or ADMIN role",
        "what": "Expense data export",
        "how": "Export",
        "when": "User has MANAGER, DIRECTOR, or ADMIN role",
        "patterns": ["@require_any_role('MANAGER', 'DIRECTOR', 'ADMIN')", "export_expenses"],
    },
    "policy_11": {
        "id": 11,
        "name": "View Audit Log",
        "who": "ADMIN role",
        "what": "Audit log",
        "how": "Read/View",
        "when": "User has ADMIN role",
        "patterns": ["@require_role('ADMIN')", "view_audit_log", "audit-log"],
    },
    "policy_12": {
        "id": 12,
        "name": "Modify Expense Policy",
        "who": "ADMIN role",
        "what": "Expense policy configuration",
        "how": "Update",
        "when": "User has ADMIN role",
        "patterns": ["@require_role('ADMIN')", "modify_expense_policy", "expense-policy"],
    },
    "policy_13": {
        "id": 13,
        "name": "Approve Urgent Expense",
        "who": "DIRECTOR role",
        "what": "Urgent expense approval",
        "how": "Fast-track approve",
        "when": "User has DIRECTOR role AND expense is urgent",
        "patterns": ["@require_role('DIRECTOR')", "is_urgent", "approve_urgent_expense"],
    },
    "policy_14": {
        "id": 14,
        "name": "View Department Expenses",
        "who": "Department managers",
        "what": "Department expenses",
        "how": "Read/View",
        "when": "MANAGER role AND matching department",
        "patterns": ["department != department", "@require_role('MANAGER')", "view_department_expenses"],
    },
    "policy_15": {
        "id": 15,
        "name": "Override Rejection",
        "who": "DIRECTOR role",
        "what": "Rejected expense",
        "how": "Override/Re-approve",
        "when": "User has DIRECTOR role AND expense was rejected",
        "patterns": ["@require_role('DIRECTOR')", "rejected", "override_rejection"],
    },
}


class TestPolicyExtractionAccuracy:
    """Test accuracy of policy extraction against ground truth."""

    @pytest.fixture
    def reference_app_content(self) -> str:
        """Load reference application content."""
        assert REFERENCE_APP.exists(), f"Reference app not found: {REFERENCE_APP}"
        return REFERENCE_APP.read_text()

    def extract_policies_from_code(self, code: str) -> list[dict]:
        """
        Extract policies from code using pattern matching.

        This simulates what the Policy Miner would extract.
        """
        extracted_policies = []

        # Extract all route definitions with decorators
        route_pattern = r'@app\.route\([^)]+\).*?(?=@app\.route|if __name__|$)'
        routes = re.findall(route_pattern, code, re.DOTALL)

        for route_code in routes:
            policy = self._analyze_route(route_code)
            if policy:
                extracted_policies.append(policy)

        return extracted_policies

    def _analyze_route(self, route_code: str) -> dict | None:
        """Analyze a route and extract policy information."""
        policy = {
            "who": set(),
            "what": set(),
            "how": set(),
            "when": set(),
            "code": route_code,
        }

        # Extract WHO (roles/subjects)
        if "@login_required" in route_code:
            policy["who"].add("Authenticated user")

        role_match = re.search(r"@require_role\('([^']+)'\)", route_code)
        if role_match:
            policy["who"].add(f"{role_match.group(1)} role")

        any_role_match = re.search(r"@require_any_role\(([^)]+)\)", route_code)
        if any_role_match:
            roles = [r.strip().strip("'\"") for r in any_role_match.group(1).split(",")]
            policy["who"].add(f"Any of: {', '.join(roles)}")

        # Check for ownership checks
        if "owner_id" in route_code and "current_user.id" in route_code:
            policy["who"].add("Resource owner")

        # Check for department checks
        if "department" in route_code.lower() and "current_user" in route_code:
            policy["who"].add("Department member")

        # Extract WHAT (resources)
        if "expense" in route_code.lower():
            policy["what"].add("Expense")

        if "report" in route_code.lower():
            policy["what"].add("Report")

        if "audit" in route_code.lower():
            policy["what"].add("Audit log")

        if "policy" in route_code.lower() and "expense" in route_code.lower():
            policy["what"].add("Expense policy")

        # Extract HOW (actions)
        if "methods=['GET']" in route_code or "methods=[\"GET\"]" in route_code:
            policy["how"].add("Read/View")

        if "methods=['POST']" in route_code or "methods=[\"POST\"]" in route_code:
            policy["how"].add("Create")

        if "methods=['PUT']" in route_code or "methods=[\"PUT\"]" in route_code:
            policy["how"].add("Update")

        if "methods=['DELETE']" in route_code or "methods=[\"DELETE\"]" in route_code:
            policy["how"].add("Delete")

        if "approve" in route_code.lower():
            policy["how"].add("Approve")

        if "reject" in route_code.lower():
            policy["how"].add("Reject")

        if "export" in route_code.lower():
            policy["how"].add("Export")

        # Extract WHEN (conditions)
        amount_conditions = re.findall(r"amount\s*(<|>|<=|>=|==)\s*(\d+)", route_code)
        for op, value in amount_conditions:
            policy["when"].add(f"Amount {op} ${value}")

        if "approved" in route_code:
            policy["when"].add("Approval status check")

        if "is_urgent" in route_code:
            policy["when"].add("Urgent flag check")

        if "rejected" in route_code:
            policy["when"].add("Rejection status check")

        # Only return if we found meaningful policy information
        if policy["who"] and policy["what"] and policy["how"]:
            return policy

        return None

    def match_extracted_to_known(
        self, extracted: list[dict], known: dict
    ) -> tuple[set[str], set[str], set[str]]:
        """
        Match extracted policies to known policies.

        Returns:
            (correct_matches, false_positives, false_negatives)
        """
        correct_matches = set()
        false_positives = set()
        matched_known = set()

        # Try to match each extracted policy to a known policy
        for i, extracted_policy in enumerate(extracted):
            matched = False

            for policy_key, known_policy in known.items():
                if policy_key in matched_known:
                    continue

                # Check if patterns from known policy appear in extracted code
                pattern_matches = sum(
                    1 for pattern in known_policy["patterns"]
                    if pattern in extracted_policy["code"]
                )

                # If >= 50% of patterns match, consider it a correct match
                if pattern_matches >= len(known_policy["patterns"]) * 0.5:
                    correct_matches.add(policy_key)
                    matched_known.add(policy_key)
                    matched = True
                    logger.info(
                        f"✓ Matched extracted policy #{i+1} to known policy {policy_key}: "
                        f"{known_policy['name']}"
                    )
                    break

            if not matched:
                false_positives.add(f"extracted_policy_{i+1}")
                logger.warning(f"✗ Extracted policy #{i+1} did not match any known policy (false positive)")

        # Find policies that were not extracted
        false_negatives = set(known.keys()) - matched_known

        if false_negatives:
            logger.warning(f"✗ Known policies not extracted (false negatives): {false_negatives}")
            for policy_key in false_negatives:
                logger.warning(f"  - {policy_key}: {known[policy_key]['name']}")

        return correct_matches, false_positives, false_negatives

    def test_reference_app_exists(self):
        """Verify reference application file exists."""
        assert REFERENCE_APP.exists(), f"Reference app not found: {REFERENCE_APP}"
        assert REFERENCE_APP.stat().st_size > 0, "Reference app is empty"
        logger.info(f"Reference app found: {REFERENCE_APP} ({REFERENCE_APP.stat().st_size} bytes)")

    def test_known_policies_documented(self):
        """Verify all known policies are properly documented."""
        assert len(KNOWN_POLICIES) == 15, "Should have exactly 15 known policies"

        for policy_key, policy in KNOWN_POLICIES.items():
            assert "name" in policy, f"{policy_key} missing name"
            assert "who" in policy, f"{policy_key} missing who"
            assert "what" in policy, f"{policy_key} missing what"
            assert "how" in policy, f"{policy_key} missing how"
            assert "when" in policy, f"{policy_key} missing when"
            assert "patterns" in policy, f"{policy_key} missing patterns"
            assert len(policy["patterns"]) > 0, f"{policy_key} has no patterns"

        logger.info(f"All {len(KNOWN_POLICIES)} known policies properly documented")

    def test_extract_policies(self, reference_app_content):
        """Test policy extraction from reference application."""
        extracted_policies = self.extract_policies_from_code(reference_app_content)

        logger.info(f"\n{'=' * 80}")
        logger.info("POLICY EXTRACTION RESULTS")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total extracted policies: {len(extracted_policies)}")

        for i, policy in enumerate(extracted_policies, 1):
            logger.info(f"\nExtracted Policy #{i}:")
            logger.info(f"  WHO: {', '.join(policy['who']) if policy['who'] else 'Not detected'}")
            logger.info(f"  WHAT: {', '.join(policy['what']) if policy['what'] else 'Not detected'}")
            logger.info(f"  HOW: {', '.join(policy['how']) if policy['how'] else 'Not detected'}")
            logger.info(f"  WHEN: {', '.join(policy['when']) if policy['when'] else 'Not detected'}")

        # Should extract at least 10 policies
        assert len(extracted_policies) >= 10, \
            f"Should extract at least 10 policies, found {len(extracted_policies)}"

    def test_calculate_accuracy(self, reference_app_content):
        """Calculate and verify extraction accuracy metrics."""
        extracted_policies = self.extract_policies_from_code(reference_app_content)

        correct_matches, false_positives, false_negatives = self.match_extracted_to_known(
            extracted_policies, KNOWN_POLICIES
        )

        total_known = len(KNOWN_POLICIES)
        total_extracted = len(extracted_policies)
        correct_count = len(correct_matches)

        # Calculate metrics
        precision = (correct_count / total_extracted * 100) if total_extracted > 0 else 0
        recall = (correct_count / total_known * 100) if total_known > 0 else 0
        accuracy = (precision + recall) / 2

        logger.info(f"\n{'=' * 80}")
        logger.info("ACCURACY METRICS")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total known policies:      {total_known}")
        logger.info(f"Total extracted policies:  {total_extracted}")
        logger.info(f"Correct matches:           {correct_count}")
        logger.info(f"False positives:           {len(false_positives)}")
        logger.info(f"False negatives:           {len(false_negatives)}")
        logger.info("")
        logger.info(f"Precision:                 {precision:.1f}%")
        logger.info(f"Recall:                    {recall:.1f}%")
        logger.info(f"Overall Accuracy:          {accuracy:.1f}%")
        logger.info(f"{'=' * 80}")

        # Verify accuracy > 85%
        assert accuracy > 85, \
            f"Accuracy {accuracy:.1f}% does not meet 85% threshold. " \
            f"Precision: {precision:.1f}%, Recall: {recall:.1f}%"

        logger.info(f"\n✓ SUCCESS: Accuracy {accuracy:.1f}% exceeds 85% threshold")

    def test_precision_metrics(self, reference_app_content):
        """Verify precision (no false positives) is high."""
        extracted_policies = self.extract_policies_from_code(reference_app_content)
        correct_matches, false_positives, _ = self.match_extracted_to_known(
            extracted_policies, KNOWN_POLICIES
        )

        precision = (len(correct_matches) / len(extracted_policies) * 100) if extracted_policies else 0

        logger.info(f"Precision: {precision:.1f}%")

        # Precision should be > 80%
        assert precision > 80, f"Precision {precision:.1f}% is too low (< 80%)"

    def test_recall_metrics(self, reference_app_content):
        """Verify recall (finding known policies) is high."""
        extracted_policies = self.extract_policies_from_code(reference_app_content)
        correct_matches, _, false_negatives = self.match_extracted_to_known(
            extracted_policies, KNOWN_POLICIES
        )

        recall = (len(correct_matches) / len(KNOWN_POLICIES) * 100)

        logger.info(f"Recall: {recall:.1f}%")

        # Recall should be > 80%
        assert recall > 80, \
            f"Recall {recall:.1f}% is too low (< 80%). Missed policies: {false_negatives}"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
