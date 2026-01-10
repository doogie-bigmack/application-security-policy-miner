"""Service for detecting inconsistent policy enforcement across applications."""

import json
from collections import defaultdict

import structlog
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.inconsistent_enforcement import (
    InconsistentEnforcement,
    InconsistentEnforcementSeverity,
    InconsistentEnforcementStatus,
)
from app.models.policy import Policy
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger(__name__)


class InconsistentEnforcementService:
    """Service for detecting and standardizing inconsistent policy enforcement across applications."""

    def __init__(self, db: Session, tenant_id: str | None = None):
        """Initialize service."""
        self.db = db
        self.tenant_id = tenant_id or "default"
        self.llm_provider = get_llm_provider()

    async def detect_inconsistencies(self) -> list[InconsistentEnforcement]:
        """Detect inconsistent policy enforcement across applications.

        Returns:
            List of InconsistentEnforcement records created
        """
        logger.info("detecting_cross_app_inconsistencies", tenant_id=self.tenant_id)

        # Group policies by resource type (normalized)
        resource_groups = self._group_policies_by_resource()

        inconsistencies = []

        # Analyze each resource type that appears in multiple applications
        for resource_type, policy_data in resource_groups.items():
            if len(policy_data["application_ids"]) < 2:
                # Skip resources that only appear in one app
                continue

            logger.info(
                "analyzing_resource_type",
                resource_type=resource_type,
                application_count=len(policy_data["application_ids"]),
                policy_count=len(policy_data["policies"]),
            )

            # Use AI to analyze if policies are inconsistent
            inconsistency = await self._analyze_policy_consistency(
                resource_type, policy_data["policies"], policy_data["application_ids"]
            )

            if inconsistency:
                inconsistencies.append(inconsistency)

        logger.info(
            "inconsistency_detection_complete",
            tenant_id=self.tenant_id,
            inconsistencies_found=len(inconsistencies),
        )

        return inconsistencies

    def _group_policies_by_resource(self) -> dict:
        """Group policies by normalized resource type.

        Returns:
            Dict mapping resource_type -> {policies: [...], application_ids: [...]}
        """
        # Get all policies with applications
        query = (
            self.db.query(Policy)
            .filter(Policy.tenant_id == self.tenant_id)
            .filter(Policy.application_id.isnot(None))
        )

        policies = query.all()

        # Group by normalized resource type
        resource_groups = defaultdict(lambda: {"policies": [], "application_ids": set()})

        for policy in policies:
            # Normalize resource name (lowercase, trim whitespace)
            normalized_resource = self._normalize_resource_name(policy.resource)

            resource_groups[normalized_resource]["policies"].append(policy)
            resource_groups[normalized_resource]["application_ids"].add(policy.application_id)

        # Convert sets to lists for JSON serialization
        for resource_type in resource_groups:
            resource_groups[resource_type]["application_ids"] = list(
                resource_groups[resource_type]["application_ids"]
            )

        return dict(resource_groups)

    def _normalize_resource_name(self, resource: str) -> str:
        """Normalize resource name for grouping.

        Args:
            resource: Resource name to normalize

        Returns:
            Normalized resource name
        """
        # Convert to lowercase
        normalized = resource.lower().strip()

        # Common substitutions to group similar resources
        substitutions = {
            "customer data": "customer_pii",
            "customer info": "customer_pii",
            "customer information": "customer_pii",
            "customer pii": "customer_pii",
            "personal data": "customer_pii",
            "personal information": "customer_pii",
            "user data": "user_pii",
            "user info": "user_pii",
            "user information": "user_pii",
            "user pii": "user_pii",
            "employee data": "employee_pii",
            "employee info": "employee_pii",
            "employee information": "employee_pii",
            "financial data": "financial_data",
            "financial information": "financial_data",
            "payment data": "financial_data",
            "payment information": "financial_data",
        }

        return substitutions.get(normalized, normalized)

    async def _analyze_policy_consistency(
        self, resource_type: str, policies: list[Policy], application_ids: list[int]
    ) -> InconsistentEnforcement | None:
        """Use AI to analyze if policies for a resource are consistent across apps.

        Args:
            resource_type: Normalized resource type
            policies: List of policies protecting this resource
            application_ids: List of application IDs involved

        Returns:
            InconsistentEnforcement record if inconsistency detected, None if consistent
        """
        # Build policy summary for AI
        policy_summaries = []
        policy_ids = []

        for policy in policies:
            app = self.db.query(Application).filter(Application.id == policy.application_id).first()
            app_name = app.name if app else f"App {policy.application_id}"

            policy_summaries.append(
                {
                    "application": app_name,
                    "subject": policy.subject,
                    "resource": policy.resource,
                    "action": policy.action,
                    "conditions": policy.conditions or "None",
                    "status": policy.status.value,
                }
            )
            policy_ids.append(policy.id)

        # AI prompt to analyze consistency
        prompt = f"""Analyze the following authorization policies that protect the same resource type "{resource_type}" across different applications.

Determine if there are inconsistent authorization requirements that create security risks.

Policies:
{json.dumps(policy_summaries, indent=2)}

Analyze for:
1. **Completely missing protection**: Some apps have NO authorization checks for this resource
2. **Drastically different requirements**: Some apps require ADMIN, others require MANAGER, others require USER
3. **Missing critical checks**: Some apps check conditions, others don't
4. **Security gaps**: Apps with weaker protection create risk

Respond with JSON:
{{
  "is_inconsistent": true/false,
  "severity": "low|medium|high|critical",
  "description": "Clear explanation of the inconsistency",
  "recommended_policy": {{
    "subject": "Recommended role/permission",
    "resource": "{resource_type}",
    "action": "Recommended action",
    "conditions": "Recommended conditions or null"
  }},
  "explanation": "Why this standardized policy is recommended"
}}

If policies are consistent or variations are acceptable, set is_inconsistent to false.
"""

        try:
            response = await self.llm_provider.generate(prompt)
            result = self._extract_json_from_response(response)

            if not result.get("is_inconsistent", False):
                logger.info(
                    "policies_consistent",
                    resource_type=resource_type,
                    application_count=len(application_ids),
                )
                return None

            # Create inconsistency record
            inconsistency = InconsistentEnforcement(
                tenant_id=self.tenant_id,
                resource_type=resource_type,
                resource_description=f"Policies protecting {resource_type}",
                affected_application_ids=application_ids,
                policy_ids=policy_ids,
                inconsistency_description=result.get("description", "Inconsistent authorization requirements detected"),
                severity=self._parse_severity(result.get("severity", "medium")),
                recommended_policy=result.get("recommended_policy", {}),
                recommendation_explanation=result.get("explanation", ""),
                status=InconsistentEnforcementStatus.PENDING,
            )

            self.db.add(inconsistency)
            self.db.commit()
            self.db.refresh(inconsistency)

            logger.info(
                "inconsistency_detected",
                inconsistency_id=inconsistency.id,
                resource_type=resource_type,
                severity=inconsistency.severity.value,
                affected_apps=len(application_ids),
            )

            return inconsistency

        except Exception as e:
            logger.error("ai_analysis_failed", resource_type=resource_type, error=str(e))
            return None

    def _extract_json_from_response(self, response: str) -> dict:
        """Extract JSON from AI response.

        Args:
            response: AI response text

        Returns:
            Parsed JSON dict
        """
        # Try to find JSON in markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()
        else:
            # Try to parse the whole response
            json_str = response.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("json_parse_failed", error=str(e), response=response[:200])
            return {}

    def _parse_severity(self, severity_str: str) -> InconsistentEnforcementSeverity:
        """Parse severity string to enum.

        Args:
            severity_str: Severity string (low, medium, high, critical)

        Returns:
            InconsistentEnforcementSeverity enum
        """
        severity_map = {
            "low": InconsistentEnforcementSeverity.LOW,
            "medium": InconsistentEnforcementSeverity.MEDIUM,
            "high": InconsistentEnforcementSeverity.HIGH,
            "critical": InconsistentEnforcementSeverity.CRITICAL,
        }
        return severity_map.get(severity_str.lower(), InconsistentEnforcementSeverity.MEDIUM)

    def get_all_inconsistencies(
        self,
        status: InconsistentEnforcementStatus | None = None,
        severity: InconsistentEnforcementSeverity | None = None,
    ) -> list[InconsistentEnforcement]:
        """Get all inconsistent enforcement records.

        Args:
            status: Optional status filter
            severity: Optional severity filter

        Returns:
            List of inconsistency records
        """
        query = self.db.query(InconsistentEnforcement).filter(
            InconsistentEnforcement.tenant_id == self.tenant_id
        )

        if status:
            query = query.filter(InconsistentEnforcement.status == status)

        if severity:
            query = query.filter(InconsistentEnforcement.severity == severity)

        return query.order_by(
            InconsistentEnforcement.severity.desc(),
            InconsistentEnforcement.created_at.desc()
        ).all()

    def get_inconsistency(self, inconsistency_id: int) -> InconsistentEnforcement | None:
        """Get a specific inconsistency by ID.

        Args:
            inconsistency_id: Inconsistency ID

        Returns:
            InconsistentEnforcement or None
        """
        return (
            self.db.query(InconsistentEnforcement)
            .filter(
                InconsistentEnforcement.id == inconsistency_id,
                InconsistentEnforcement.tenant_id == self.tenant_id,
            )
            .first()
        )

    def update_status(
        self,
        inconsistency_id: int,
        status: InconsistentEnforcementStatus,
        resolution_notes: str | None = None,
        resolved_by: str | None = None,
    ) -> InconsistentEnforcement | None:
        """Update inconsistency status.

        Args:
            inconsistency_id: Inconsistency ID
            status: New status
            resolution_notes: Optional resolution notes
            resolved_by: Email of user resolving

        Returns:
            Updated InconsistentEnforcement or None
        """
        inconsistency = self.get_inconsistency(inconsistency_id)
        if not inconsistency:
            return None

        inconsistency.status = status
        if resolution_notes:
            inconsistency.resolution_notes = resolution_notes
        if resolved_by:
            inconsistency.resolved_by = resolved_by
        if status == InconsistentEnforcementStatus.RESOLVED:
            from datetime import UTC, datetime
            inconsistency.resolved_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(inconsistency)

        logger.info(
            "inconsistency_status_updated",
            inconsistency_id=inconsistency_id,
            status=status.value,
            resolved_by=resolved_by,
        )

        return inconsistency

    def delete_inconsistency(self, inconsistency_id: int) -> bool:
        """Delete an inconsistency record.

        Args:
            inconsistency_id: Inconsistency ID

        Returns:
            True if deleted, False if not found
        """
        inconsistency = self.get_inconsistency(inconsistency_id)
        if not inconsistency:
            return False

        self.db.delete(inconsistency)
        self.db.commit()

        logger.info("inconsistency_deleted", inconsistency_id=inconsistency_id)
        return True
