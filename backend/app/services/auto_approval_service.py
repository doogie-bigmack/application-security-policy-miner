"""Auto-approval service for AI-powered policy approval."""
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.auto_approval import AutoApprovalDecision, AutoApprovalSettings
from app.models.policy import Policy, PolicyStatus
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


class AutoApprovalService:
    """Service for managing auto-approval of policies."""

    def __init__(self, db: Session):
        """Initialize service."""
        self.db = db
        self.llm_provider = get_llm_provider()

    def get_or_create_settings(self, tenant_id: str | None) -> AutoApprovalSettings:
        """Get or create auto-approval settings for tenant."""
        # Use default tenant if none provided
        effective_tenant_id = tenant_id or "default-tenant"

        settings = self.db.query(AutoApprovalSettings).filter(
            AutoApprovalSettings.tenant_id == effective_tenant_id
        ).first()

        if not settings:
            settings = AutoApprovalSettings(tenant_id=effective_tenant_id)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
            logger.info(f"Created auto-approval settings for tenant {effective_tenant_id}")

        return settings

    def update_settings(
        self,
        tenant_id: str | None,
        enabled: bool | None = None,
        risk_threshold: float | None = None,
        min_historical_approvals: int | None = None,
    ) -> AutoApprovalSettings:
        """Update auto-approval settings."""
        settings = self.get_or_create_settings(tenant_id)

        if enabled is not None:
            settings.enabled = enabled
        if risk_threshold is not None:
            settings.risk_threshold = risk_threshold
        if min_historical_approvals is not None:
            settings.min_historical_approvals = min_historical_approvals

        self.db.commit()
        self.db.refresh(settings)
        logger.info(f"Updated auto-approval settings for tenant {tenant_id}")

        return settings

    def get_historical_approvals(self, tenant_id: str | None, policy: Policy) -> list[Policy]:
        """Get historically approved policies similar to the given policy."""
        effective_tenant_id = tenant_id or "default-tenant"

        # Find approved policies with similar characteristics
        similar_policies = (
            self.db.query(Policy)
            .filter(
                Policy.tenant_id == effective_tenant_id,
                Policy.status == PolicyStatus.APPROVED,
                Policy.id != policy.id,
            )
            .all()
        )

        # Filter by similarity (simple heuristic: same subject or same action/resource combo)
        matches = []
        for p in similar_policies:
            if (
                p.subject.lower() == policy.subject.lower() or
                (p.action.lower() == policy.action.lower() and
                 p.resource.lower() == policy.resource.lower())
            ):
                matches.append(p)

        return matches

    def analyze_with_ai(self, policy: Policy, historical_policies: list[Policy]) -> dict[str, Any]:
        """Use AI to analyze if policy should be auto-approved."""
        # Build context about the policy
        policy_context = f"""Policy to analyze:
- Subject (Who): {policy.subject}
- Resource (What): {policy.resource}
- Action (How): {policy.action}
- Conditions (When): {policy.conditions or 'None'}
- Risk Score: {policy.risk_score}
- Risk Level: {policy.risk_level}
- Source Type: {policy.source_type}
"""

        # Build historical context
        historical_context = "Historical approved policies:\n"
        for i, hp in enumerate(historical_policies[:10], 1):  # Limit to 10 for context
            historical_context += f"{i}. Subject: {hp.subject}, Resource: {hp.resource}, Action: {hp.action}, Risk: {hp.risk_level}\n"

        if not historical_policies:
            historical_context = "No historical approved policies found matching this pattern."

        # Build prompt
        prompt = f"""You are analyzing whether a security policy should be auto-approved based on historical patterns.

{policy_context}

{historical_context}

Analyze this policy and determine:
1. Should it be auto-approved? (yes/no)
2. What patterns match from historical data?
3. What is your confidence level?
4. Provide a clear reasoning.

Respond in JSON format:
{{
    "should_auto_approve": true/false,
    "matched_patterns": ["pattern1", "pattern2"],
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation"
}}
"""

        try:
            response = self.llm_provider.generate(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3,
            )

            # Extract JSON from response
            response_text = response.strip()

            # Find JSON in response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)
            logger.info(f"AI analysis complete for policy {policy.id}: {result.get('should_auto_approve')}")
            return result

        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return {
                "should_auto_approve": False,
                "matched_patterns": [],
                "confidence": 0.0,
                "reasoning": f"Error during AI analysis: {str(e)}",
            }

    def evaluate_policy(self, tenant_id: str | None, policy: Policy) -> tuple[bool, str]:
        """
        Evaluate if a policy should be auto-approved.

        Returns:
            Tuple of (should_approve, reasoning)
        """
        effective_tenant_id = tenant_id or "default-tenant"
        settings = self.get_or_create_settings(effective_tenant_id)

        # Check if auto-approval is enabled
        if not settings.enabled:
            return False, "Auto-approval is disabled"

        # Check risk threshold
        if policy.risk_score is None or policy.risk_score > settings.risk_threshold:
            return False, f"Risk score ({policy.risk_score}) exceeds threshold ({settings.risk_threshold})"

        # Get historical approvals
        historical = self.get_historical_approvals(effective_tenant_id, policy)

        # Check if we have enough historical data
        if len(historical) < settings.min_historical_approvals:
            return False, f"Insufficient historical approvals ({len(historical)} < {settings.min_historical_approvals})"

        # Use AI to analyze
        ai_result = self.analyze_with_ai(policy, historical)

        # Record decision
        decision = AutoApprovalDecision(
            tenant_id=effective_tenant_id,
            policy_id=policy.id,
            auto_approved=ai_result.get("should_auto_approve", False),
            reasoning=ai_result.get("reasoning", "No reasoning provided"),
            risk_score=policy.risk_score or 0.0,
            similar_policies_count=len(historical),
            matched_patterns=json.dumps(ai_result.get("matched_patterns", [])),
        )
        self.db.add(decision)

        # Update metrics
        settings.total_policies_scanned += 1
        if ai_result.get("should_auto_approve", False):
            settings.total_auto_approvals += 1

        # Calculate rate
        if settings.total_policies_scanned > 0:
            settings.auto_approval_rate = (
                settings.total_auto_approvals / settings.total_policies_scanned * 100
            )

        self.db.commit()

        logger.info(
            f"Policy {policy.id} evaluation: auto_approve={ai_result.get('should_auto_approve')} "
            f"(historical={len(historical)}, confidence={ai_result.get('confidence')})"
        )

        return ai_result.get("should_auto_approve", False), ai_result.get("reasoning", "")

    def get_metrics(self, tenant_id: str | None) -> dict[str, Any]:
        """Get auto-approval metrics for tenant."""
        effective_tenant_id = tenant_id or "default-tenant"
        settings = self.get_or_create_settings(effective_tenant_id)

        return {
            "total_auto_approvals": settings.total_auto_approvals,
            "total_policies_scanned": settings.total_policies_scanned,
            "auto_approval_rate": settings.auto_approval_rate,
            "enabled": settings.enabled,
            "risk_threshold": settings.risk_threshold,
            "min_historical_approvals": settings.min_historical_approvals,
        }

    def get_decisions(self, tenant_id: str | None, limit: int = 100) -> list[AutoApprovalDecision]:
        """Get recent auto-approval decisions."""
        effective_tenant_id = tenant_id or "default-tenant"

        return (
            self.db.query(AutoApprovalDecision)
            .filter(AutoApprovalDecision.tenant_id == effective_tenant_id)
            .order_by(AutoApprovalDecision.created_at.desc())
            .limit(limit)
            .all()
        )
