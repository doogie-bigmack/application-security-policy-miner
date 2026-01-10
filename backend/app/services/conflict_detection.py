"""Conflict detection service for identifying policy conflicts."""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.conflict import ConflictType, PolicyConflict
from app.models.policy import Policy
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


class ConflictDetectionService:
    """Service for detecting and analyzing policy conflicts."""

    def __init__(self, db: Session):
        """Initialize the conflict detection service."""
        self.db = db
        self.llm_provider = get_llm_provider()

    def detect_conflicts(self, repository_id: int | None = None) -> list[PolicyConflict]:
        """
        Detect conflicts between policies.

        Args:
            repository_id: Optional repository ID to limit conflict detection

        Returns:
            List of detected conflicts
        """
        # Get all policies
        query = self.db.query(Policy)
        if repository_id:
            query = query.filter(Policy.repository_id == repository_id)

        policies = query.all()

        if len(policies) < 2:
            logger.info(f"Not enough policies to detect conflicts (found {len(policies)})")
            return []

        logger.info(f"Detecting conflicts among {len(policies)} policies")

        conflicts = []

        # Compare each pair of policies
        for i in range(len(policies)):
            for j in range(i + 1, len(policies)):
                policy_a = policies[i]
                policy_b = policies[j]

                # Check if these policies might conflict
                if self._policies_might_conflict(policy_a, policy_b):
                    conflict = self._analyze_conflict(policy_a, policy_b)
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
            logger.info(f"Detected {len(conflicts)} new conflicts")
        else:
            logger.info("No new conflicts detected")

        return conflicts

    def _policies_might_conflict(self, policy_a: Policy, policy_b: Policy) -> bool:
        """
        Quick check to see if two policies might conflict.

        This is a fast pre-filter before doing expensive AI analysis.
        """
        # Policies must have overlapping resources or subjects to conflict
        resource_overlap = (
            policy_a.resource.lower() in policy_b.resource.lower()
            or policy_b.resource.lower() in policy_a.resource.lower()
        )

        subject_overlap = (
            policy_a.subject.lower() in policy_b.subject.lower()
            or policy_b.subject.lower() in policy_a.subject.lower()
        )

        # Policies that operate on similar resources and subjects are candidates
        return resource_overlap or subject_overlap

    def _analyze_conflict(self, policy_a: Policy, policy_b: Policy) -> PolicyConflict | None:
        """
        Use AI to analyze if two policies conflict and generate recommendations.

        Returns:
            PolicyConflict if a conflict is detected, None otherwise
        """
        prompt = f"""Analyze these two authorization policies for conflicts:

Policy A:
- Subject (Who): {policy_a.subject}
- Resource (What): {policy_a.resource}
- Action (How): {policy_a.action}
- Conditions (When): {policy_a.conditions or "None"}
- Description: {policy_a.description or "N/A"}

Policy B:
- Subject (Who): {policy_b.subject}
- Resource (What): {policy_b.resource}
- Action (How): {policy_b.action}
- Conditions (When): {policy_b.conditions or "None"}
- Description: {policy_b.description or "N/A"}

Determine if these policies conflict. A conflict exists if:
1. CONTRADICTORY: They have contradictory authorization rules for the same scenario
2. OVERLAPPING: They have overlapping scope but different authorization logic
3. INCONSISTENT: They enforce inconsistent authorization for similar resources

Respond in this exact JSON format:
{{
  "has_conflict": true or false,
  "conflict_type": "contradictory" or "overlapping" or "inconsistent" or null,
  "severity": "low" or "medium" or "high",
  "description": "Brief description of the conflict",
  "recommendation": "How to resolve this conflict"
}}

Only set has_conflict to true if there is a real conflict. Similar policies are not conflicts."""

        try:
            # Call LLM provider (AWS Bedrock or Azure OpenAI)
            response_text = self.llm_provider.create_message(
                prompt=prompt,
                max_tokens=1000,
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
                f"Detected {result['conflict_type']} conflict between policy {policy_a.id} and {policy_b.id}"
            )

            return conflict

        except Exception as e:
            logger.error(f"Error analyzing conflict with AI: {e}")
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
