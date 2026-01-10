"""Risk scoring service for multi-dimensional policy risk analysis."""

import logging
import re

logger = logging.getLogger(__name__)


class RiskScoringService:
    """Service for calculating multi-dimensional risk scores for policies."""

    @staticmethod
    def calculate_complexity_score(
        subject: str,
        resource: str,
        action: str,
        conditions: str | None,
        code_snippet: str,
    ) -> float:
        """Calculate complexity score (0-100) based on policy and code complexity.

        Higher complexity = more risk due to harder to understand/maintain.

        Factors:
        - Length of conditions
        - Number of logical operators (AND, OR, NOT)
        - Nested conditions
        - Code complexity (lines, nesting depth)
        """
        score = 0.0

        # Conditions complexity (0-40 points)
        if conditions:
            # Length of conditions
            condition_length = len(conditions)
            if condition_length > 200:
                score += 15
            elif condition_length > 100:
                score += 10
            elif condition_length > 50:
                score += 5

            # Number of logical operators
            logical_operators = len(re.findall(r"\b(AND|OR|NOT|&&|\|\||!)\b", conditions, re.IGNORECASE))
            score += min(logical_operators * 3, 15)

            # Nested parentheses (nested conditions)
            max_nesting = 0
            current_nesting = 0
            for char in conditions:
                if char == "(":
                    current_nesting += 1
                    max_nesting = max(max_nesting, current_nesting)
                elif char == ")":
                    current_nesting -= 1
            score += min(max_nesting * 5, 10)

        # Code complexity (0-30 points)
        lines = code_snippet.split("\n")
        score += min(len(lines) * 2, 15)

        # Nesting depth in code
        max_indent = 0
        for line in lines:
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent // 2)  # Assume 2-space indents
        score += min(max_indent * 3, 15)

        # Subject/Resource/Action complexity (0-30 points)
        # Multiple subjects (comma-separated roles)
        if "," in subject or " or " in subject.lower():
            score += 10

        # Complex resource patterns
        if "*" in resource or "regex" in resource.lower() or "/" in resource:
            score += 10

        # Multiple actions
        if "," in action or " or " in action.lower():
            score += 10

        return min(score, 100.0)

    @staticmethod
    def calculate_impact_score(
        subject: str,
        resource: str,
        action: str,
        conditions: str | None,
    ) -> float:
        """Calculate impact score (0-100) based on potential damage.

        Higher impact = more risk if policy is wrong/exploited.

        Factors:
        - Resource sensitivity (PII, financial, admin)
        - Action destructiveness (delete, modify vs read)
        - Subject privilege level (admin, system)
        - Breadth of access (wildcards, lack of conditions)
        """
        score = 0.0

        # Resource sensitivity (0-40 points)
        sensitive_resources = [
            ("pii", 15),
            ("personal", 15),
            ("ssn", 20),
            ("credit", 20),
            ("financial", 15),
            ("payment", 15),
            ("salary", 15),
            ("admin", 15),
            ("user", 10),
            ("account", 10),
            ("database", 15),
            ("system", 15),
            ("config", 10),
        ]
        resource_lower = resource.lower()
        for keyword, points in sensitive_resources:
            if keyword in resource_lower:
                score += points
                break

        # Action destructiveness (0-30 points)
        destructive_actions = [
            ("delete", 25),
            ("drop", 30),
            ("remove", 20),
            ("destroy", 30),
            ("modify", 15),
            ("update", 15),
            ("edit", 10),
            ("change", 10),
            ("write", 10),
            ("create", 5),
        ]
        action_lower = action.lower()
        for keyword, points in destructive_actions:
            if keyword in action_lower:
                score += points
                break

        # Subject privilege (0-20 points)
        privileged_subjects = [
            ("admin", 20),
            ("superuser", 20),
            ("root", 20),
            ("system", 15),
            ("owner", 10),
            ("manager", 5),
        ]
        subject_lower = subject.lower()
        for keyword, points in privileged_subjects:
            if keyword in subject_lower:
                score += points
                break

        # Lack of conditions = broader access (0-10 points)
        if not conditions or len(conditions.strip()) < 10:
            score += 10

        return min(score, 100.0)

    @staticmethod
    def calculate_confidence_score(
        evidence_count: int,
        code_snippet: str,
        subject: str,
        resource: str,
        action: str,
    ) -> float:
        """Calculate confidence score (0-100) in the policy extraction.

        Higher confidence = lower risk of AI hallucination.

        Factors:
        - Number of evidence items
        - Quality of evidence (contains clear authorization keywords)
        - Specificity of extracted fields
        """
        score = 0.0

        # Evidence count (0-30 points)
        score += min(evidence_count * 10, 30)

        # Evidence quality - check for authorization keywords (0-40 points)
        auth_keywords = [
            "authorize",
            "permission",
            "role",
            "access",
            "allow",
            "deny",
            "grant",
            "check",
            "verify",
            "authenticate",
            "hasRole",
            "hasPermission",
            "canAccess",
            "isAllowed",
        ]
        snippet_lower = code_snippet.lower()
        keyword_matches = sum(1 for keyword in auth_keywords if keyword.lower() in snippet_lower)
        score += min(keyword_matches * 10, 40)

        # Field specificity (0-30 points)
        # Specific subjects/resources/actions = higher confidence
        if subject and subject != "Unknown" and len(subject) > 3:
            score += 10
        if resource and resource != "Unknown" and len(resource) > 3:
            score += 10
        if action and action != "Unknown" and len(action) > 3:
            score += 10

        return min(score, 100.0)

    @staticmethod
    def calculate_historical_score() -> float:
        """Calculate historical score (0-100) based on change frequency.

        Higher score = more historical changes = higher risk.

        Note: For now, returns 0 as we don't have historical data.
        Future: Track policy modifications over time.
        """
        # TODO: Implement after we have policy change tracking
        # This would query historical policy versions and count changes
        return 0.0

    @staticmethod
    def calculate_overall_risk_score(
        complexity: float,
        impact: float,
        confidence: float,
        historical: float,
    ) -> float:
        """Calculate overall risk score (0-100) from component scores.

        Weighted average:
        - Impact: 40% (most important)
        - Complexity: 30%
        - Confidence: 20% (inverse - low confidence = high risk)
        - Historical: 10%
        """
        # Invert confidence (high confidence = low risk)
        inverted_confidence = 100.0 - confidence

        overall = (
            impact * 0.4
            + complexity * 0.3
            + inverted_confidence * 0.2
            + historical * 0.1
        )

        return min(overall, 100.0)

    def calculate_risk_scores(
        self,
        subject: str,
        resource: str,
        action: str,
        conditions: str,
        code_snippet: str,
        evidence_count: int = 1,
    ) -> dict[str, float | str]:
        """Calculate all risk scores and return as dictionary.

        This is a convenience method that calls all individual scoring methods
        and returns a complete risk assessment.

        Args:
            subject: Policy subject (who)
            resource: Policy resource (what)
            action: Policy action (how)
            conditions: Policy conditions (when)
            code_snippet: Code evidence snippet
            evidence_count: Number of evidence items

        Returns:
            Dictionary with all risk scores and risk level
        """
        # Calculate individual scores
        complexity_score = self.calculate_complexity_score(
            subject=subject,
            resource=resource,
            action=action,
            conditions=conditions,
            code_snippet=code_snippet,
        )

        impact_score = self.calculate_impact_score(
            subject=subject,
            resource=resource,
            action=action,
            conditions=conditions,
        )

        confidence_score = self.calculate_confidence_score(
            evidence_count=evidence_count,
            code_snippet=code_snippet,
            subject=subject,
            resource=resource,
            action=action,
        )

        historical_score = self.calculate_historical_score()

        overall_risk_score = self.calculate_overall_risk_score(
            complexity=complexity_score,
            impact=impact_score,
            confidence=confidence_score,
            historical=historical_score,
        )

        # Determine risk level based on overall score
        if overall_risk_score >= 70:
            risk_level = "HIGH"
        elif overall_risk_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "complexity_score": complexity_score,
            "impact_score": impact_score,
            "confidence_score": confidence_score,
            "historical_score": historical_score,
            "overall_risk_score": overall_risk_score,
            "risk_level": risk_level,
        }
