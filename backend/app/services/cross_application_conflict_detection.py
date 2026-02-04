"""Cross-application conflict detection service for identifying contradictory policies across multiple applications."""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.conflict import ConflictType, PolicyConflict
from app.models.policy import Policy
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


class CrossApplicationConflictDetectionService:
    """Service for detecting and analyzing policy conflicts across multiple applications."""

    def __init__(self, db: Session):
        """Initialize the cross-application conflict detection service."""
        self.db = db
        self.llm_provider = get_llm_provider()

    def detect_cross_application_conflicts(
        self, tenant_id: str | None = None, application_ids: list[int] | None = None
    ) -> list[PolicyConflict]:
        """
        Detect conflicts between policies across different applications.

        Args:
            tenant_id: Optional tenant ID to limit conflict detection
            application_ids: Optional list of application IDs to compare. If None, compares all applications.

        Returns:
            List of detected cross-application conflicts
        """
        # Get all policies from different applications
        query = self.db.query(Policy).filter(Policy.application_id.isnot(None))

        if tenant_id:
            query = query.filter(Policy.tenant_id == tenant_id)

        if application_ids:
            query = query.filter(Policy.application_id.in_(application_ids))

        policies = query.all()

        if len(policies) < 2:
            logger.info(f"Not enough policies to detect cross-application conflicts (found {len(policies)})")
            return []

        # Group policies by application
        policies_by_app: dict[int, list[Policy]] = {}
        for policy in policies:
            if policy.application_id not in policies_by_app:
                policies_by_app[policy.application_id] = []
            policies_by_app[policy.application_id].append(policy)

        if len(policies_by_app) < 2:
            logger.info(f"Policies from only {len(policies_by_app)} application(s) found. Need at least 2 for cross-application conflicts.")
            return []

        logger.info(f"Detecting cross-application conflicts across {len(policies_by_app)} applications with {len(policies)} total policies")

        conflicts = []

        # Compare policies from different applications
        for i, (app_id_a, policies_a) in enumerate(list(policies_by_app.items())):
            for app_id_b, policies_b in list(policies_by_app.items())[i + 1:]:
                # Compare each policy from app A with each policy from app B
                for policy_a in policies_a:
                    for policy_b in policies_b:
                        # Check if these policies might conflict
                        if self._policies_might_conflict(policy_a, policy_b):
                            conflict = self._analyze_cross_app_conflict(policy_a, policy_b)
                            if conflict:
                                # Check if this conflict already exists
                                existing = (
                                    self.db.query(PolicyConflict)
                                    .filter(
                                        (
                                            (PolicyConflict.policy_a_id == policy_a.id)
                                            & (PolicyConflict.policy_b_id == policy_b.id)
                                        )
                                        | (
                                            (PolicyConflict.policy_a_id == policy_b.id)
                                            & (PolicyConflict.policy_b_id == policy_a.id)
                                        )
                                    )
                                    .first()
                                )

                                if not existing:
                                    self.db.add(conflict)
                                    conflicts.append(conflict)

        if conflicts:
            self.db.commit()
            logger.info(f"Detected {len(conflicts)} new cross-application conflicts")
        else:
            logger.info("No new cross-application conflicts detected")

        return conflicts

    def _policies_might_conflict(self, policy_a: Policy, policy_b: Policy) -> bool:
        """
        Quick check to see if two policies from different applications might conflict.

        This is a fast pre-filter before doing expensive AI analysis.
        """
        # Policies must be from different applications
        if policy_a.application_id == policy_b.application_id:
            return False

        # Policies must have overlapping resources to conflict
        resource_a = policy_a.resource.lower()
        resource_b = policy_b.resource.lower()

        # Check for resource overlap (e.g., "Expense Report" matches "Expense")
        resource_overlap = (
            resource_a in resource_b
            or resource_b in resource_a
            or self._semantic_overlap(resource_a, resource_b)
        )

        if not resource_overlap:
            return False

        # Check for subject overlap or action overlap
        subject_a = policy_a.subject.lower()
        subject_b = policy_b.subject.lower()

        subject_overlap = (
            subject_a in subject_b
            or subject_b in subject_a
            or self._semantic_overlap(subject_a, subject_b)
        )

        action_a = policy_a.action.lower()
        action_b = policy_b.action.lower()

        action_overlap = (
            action_a in action_b
            or action_b in action_a
            or action_a == action_b
        )

        # Policies that operate on similar resources with similar subjects or actions are candidates
        return resource_overlap and (subject_overlap or action_overlap)

    def _semantic_overlap(self, text_a: str, text_b: str) -> bool:
        """
        Check for semantic overlap between two text strings.

        Examples:
        - "manager" and "managers" -> True
        - "approve" and "approval" -> True
        - "expense" and "expenses" -> True
        """
        # Simple stem matching (remove common suffixes)
        # Order matters - try longer suffixes first
        suffixes = ['tion', 'ing', 'es', 'ed', 's', 'al', 'er', 'or']

        def stem(text: str) -> str:
            for suffix in suffixes:
                if len(text) > len(suffix) + 2 and text.endswith(suffix):
                    return text[:-len(suffix)]
            return text

        stem_a = stem(text_a)
        stem_b = stem(text_b)

        # Check if one stem is a prefix of the other
        return stem_a == stem_b or stem_a.startswith(stem_b) or stem_b.startswith(stem_a)

    def _analyze_cross_app_conflict(self, policy_a: Policy, policy_b: Policy) -> PolicyConflict | None:
        """
        Use AI to analyze if two policies from different applications conflict.

        Returns:
            PolicyConflict if a conflict is detected, None otherwise
        """
        # Get application names for context
        app_a = self.db.query(Application).filter(Application.id == policy_a.application_id).first()
        app_b = self.db.query(Application).filter(Application.id == policy_b.application_id).first()

        app_a_name = app_a.name if app_a else f"Application {policy_a.application_id}"
        app_b_name = app_b.name if app_b else f"Application {policy_b.application_id}"

        prompt = f"""Analyze these two authorization policies from DIFFERENT applications for contradictory rules:

Application A: {app_a_name}
Policy A:
- Subject (Who): {policy_a.subject}
- Resource (What): {policy_a.resource}
- Action (How): {policy_a.action}
- Conditions (When): {policy_a.conditions or "None"}
- Description: {policy_a.description or "N/A"}

Application B: {app_b_name}
Policy B:
- Subject (Who): {policy_b.subject}
- Resource (What): {policy_b.resource}
- Action (How): {policy_b.action}
- Conditions (When): {policy_b.conditions or "None"}
- Description: {policy_b.description or "N/A"}

Determine if these policies create a CROSS-APPLICATION CONFLICT. This is a HIGH-SEVERITY issue when:
1. CONTRADICTORY: Different applications have contradictory authorization rules for the same business scenario
   Example: ExpenseApp v1 says "Managers approve < $5000" but ExpenseApp v2 says "Only Directors approve"
2. INCONSISTENT: Different applications enforce inconsistent authorization for the same resource type
   Example: FinancePortal allows "Managers approve < $10000" but ExpenseApp allows "Managers approve < $5000"

These policies are from DIFFERENT APPLICATIONS, so they should ideally have CONSISTENT authorization rules for the same resources.

Respond in this exact JSON format:
{{
  "has_conflict": true or false,
  "conflict_type": "contradictory" or "inconsistent" or null,
  "severity": "low" or "medium" or "high",
  "description": "Brief description of the cross-application conflict including application names",
  "recommendation": "How to create a unified policy that resolves this conflict across both applications"
}}

Only set has_conflict to true if there is a real contradiction or inconsistency across applications."""

        try:
            # Call LLM provider (AWS Bedrock or Azure OpenAI)
            response_text = self.llm_provider.create_message(
                prompt=prompt,
                max_tokens=1500,
                temperature=0,
            )

            result = self._parse_ai_response(response_text)

            if not result.get("has_conflict"):
                return None

            # Create conflict record
            conflict = PolicyConflict(
                policy_a_id=policy_a.id,
                policy_b_id=policy_b.id,
                conflict_type=ConflictType(result["conflict_type"]),
                description=result["description"],
                severity=result["severity"],
                ai_recommendation=result["recommendation"],
            )

            logger.info(
                f"Detected cross-application {result['conflict_type']} conflict between "
                f"{app_a_name} policy {policy_a.id} and {app_b_name} policy {policy_b.id}"
            )

            return conflict

        except Exception as e:
            logger.error(f"Error analyzing cross-application conflict with AI: {e}")
            return None

    def _parse_ai_response(self, response_text: str) -> dict[str, Any]:
        """Parse AI response to extract conflict information."""
        import json

        # Find JSON in the response
        start = response_text.find("{")
        end = response_text.rfind("}") + 1

        if start == -1 or end == 0:
            logger.error(f"Could not find JSON in AI response: {response_text}")
            return {"has_conflict": False}

        try:
            result = json.loads(response_text[start:end])
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Could not parse AI response as JSON: {e}")
            return {"has_conflict": False}

    def get_cross_application_conflicts(
        self, tenant_id: str | None = None, status: str | None = None
    ) -> list[PolicyConflict]:
        """
        Get all cross-application conflicts.

        Args:
            tenant_id: Optional tenant ID to filter conflicts
            status: Optional status filter (pending, resolved)

        Returns:
            List of cross-application conflicts
        """
        query = (
            self.db.query(PolicyConflict)
            .join(Policy, PolicyConflict.policy_a_id == Policy.id)
            .filter(Policy.application_id.isnot(None))
        )

        if tenant_id:
            query = query.filter(PolicyConflict.tenant_id == tenant_id)

        if status:
            query = query.filter(PolicyConflict.status == status)

        conflicts = query.all()

        # Filter to only include cross-application conflicts
        cross_app_conflicts = []
        for conflict in conflicts:
            policy_a = self.db.query(Policy).filter(Policy.id == conflict.policy_a_id).first()
            policy_b = self.db.query(Policy).filter(Policy.id == conflict.policy_b_id).first()

            if policy_a and policy_b and policy_a.application_id != policy_b.application_id:
                cross_app_conflicts.append(conflict)

        logger.info(f"Retrieved {len(cross_app_conflicts)} cross-application conflicts")
        return cross_app_conflicts
