"""Policy translation service for converting policies to various PBAC formats."""

import json

import structlog

from app.core.test_mode import is_test_mode
from app.models.policy import Policy

logger = structlog.get_logger(__name__)


class TranslationService:
    """Service for translating policies to PBAC platform formats."""

    def __init__(self):
        """Initialize the translation service."""
        self.test_mode = is_test_mode()
        if not self.test_mode:
            from app.services.llm_provider import get_llm_provider

            self.llm_provider = get_llm_provider()
        else:
            self.llm_provider = None
            logger.info("translation_service_initialized_in_test_mode")

    async def translate_to_rego(self, policy: Policy) -> str:
        """
        Translate a policy to OPA Rego format using Claude Agent SDK.

        Args:
            policy: The policy to translate

        Returns:
            str: The translated Rego policy

        Raises:
            ValueError: If translation fails
        """
        logger.info("translating_policy_to_rego", policy_id=policy.id, test_mode=self.test_mode)

        # Return mock data in TEST_MODE
        if self.test_mode:
            return self._get_mock_rego_policy(policy)

        # Build the prompt for Claude
        prompt = self._build_rego_translation_prompt(policy)

        try:
            # Call Claude Agent SDK via LLM provider
            response_text = self.llm_provider.create_message(
                prompt=prompt,
                max_tokens=2000,
                temperature=0,
            )

            # Extract the Rego policy from the response
            rego_policy = self._extract_rego_from_response(response_text)

            logger.info(
                "translation_successful",
                policy_id=policy.id,
                rego_length=len(rego_policy),
            )

            return rego_policy

        except Exception as e:
            logger.error(
                "translation_failed",
                policy_id=policy.id,
                error=str(e),
            )
            raise ValueError(f"Failed to translate policy to Rego: {e}") from e

    async def translate_to_cedar(self, policy: Policy) -> str:
        """
        Translate a policy to AWS Cedar format using Claude Agent SDK.

        Args:
            policy: The policy to translate

        Returns:
            str: The translated Cedar policy

        Raises:
            ValueError: If translation fails
        """
        logger.info("translating_policy_to_cedar", policy_id=policy.id, test_mode=self.test_mode)

        # Return mock data in TEST_MODE
        if self.test_mode:
            return self._get_mock_cedar_policy(policy)

        prompt = self._build_cedar_translation_prompt(policy)

        try:
            response_text = self.llm_provider.create_message(
                prompt=prompt,
                max_tokens=2000,
                temperature=0,
            )

            cedar_policy = self._extract_cedar_from_response(response_text)

            # Validate the Cedar policy structure
            self._validate_cedar_policy(cedar_policy)

            logger.info(
                "translation_successful",
                policy_id=policy.id,
                cedar_length=len(cedar_policy),
            )

            return cedar_policy

        except Exception as e:
            logger.error(
                "translation_failed",
                policy_id=policy.id,
                error=str(e),
            )
            raise ValueError(f"Failed to translate policy to Cedar: {e}") from e

    async def translate_to_json(self, policy: Policy) -> str:
        """
        Translate a policy to custom JSON format.

        Args:
            policy: The policy to translate

        Returns:
            str: The translated JSON policy

        Raises:
            ValueError: If translation fails
        """
        logger.info("translating_policy_to_json", policy_id=policy.id)

        # For JSON, we can use a simple structured format
        json_policy = {
            "subject": policy.subject,
            "resource": policy.resource,
            "action": policy.action,
            "conditions": policy.conditions,
            "description": policy.description,
            "source_type": policy.source_type.value if policy.source_type else "unknown",
        }

        return json.dumps(json_policy, indent=2)

    def _build_rego_translation_prompt(self, policy: Policy) -> str:
        """Build the prompt for Rego translation."""
        return f"""You are an expert in translating authorization policies to OPA Rego format.

Given the following authorization policy extracted from code:

**Subject (Who):** {policy.subject}
**Resource (What):** {policy.resource}
**Action (How):** {policy.action}
**Conditions (When):** {policy.conditions}
**Description:** {policy.description}

**Task:** Translate this policy into a valid OPA Rego policy.

**Requirements:**
1. Use package name: `package authz`
2. Create an `allow` rule that grants access when all conditions are met
3. Include comments explaining the policy logic
4. Use semantic intent - preserve the WHO/WHAT/HOW/WHEN logic
5. Return ONLY the Rego policy code, no explanations before or after

**Example Rego Format:**
```rego
package authz

# Allow managers to approve expenses under $5000
allow {{
    input.user.role == "manager"
    input.resource.type == "expense"
    input.action == "approve"
    input.resource.amount < 5000
}}
```

Translate the policy above to Rego format:
"""

    def _build_cedar_translation_prompt(self, policy: Policy) -> str:
        """Build the prompt for Cedar translation."""
        return f"""You are an expert in translating authorization policies to AWS Cedar format.

Given the following authorization policy extracted from code:

**Subject (Who):** {policy.subject}
**Resource (What):** {policy.resource}
**Action (How):** {policy.action}
**Conditions (When):** {policy.conditions}
**Description:** {policy.description}

**Task:** Translate this policy into a valid AWS Cedar policy.

**Requirements:**
1. Use permit/forbid statements
2. Define principal, action, and resource
3. Include when clauses for conditions
4. Preserve the WHO/WHAT/HOW/WHEN logic
5. Return ONLY the Cedar policy code, no explanations before or after

**Example Cedar Format:**
```cedar
permit (
    principal in Role::"manager",
    action == Action::"approve",
    resource in ResourceType::"expense"
)
when {{
    resource.amount < 5000
}};
```

Translate the policy above to Cedar format:
"""

    def _extract_rego_from_response(self, response_text: str) -> str:
        """Extract Rego policy from Claude's response."""
        # Remove markdown code blocks if present
        text = response_text.strip()

        # Find code block
        if "```rego" in text:
            start = text.find("```rego") + len("```rego")
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        # If no code blocks, return the whole response (assuming it's pure Rego)
        return text

    def _extract_cedar_from_response(self, response_text: str) -> str:
        """Extract Cedar policy from Claude's response."""
        text = response_text.strip()

        # Find code block
        if "```cedar" in text:
            start = text.find("```cedar") + len("```cedar")
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        return text

    def _validate_cedar_policy(self, cedar_policy: str) -> None:
        """
        Validate that the Cedar policy has basic structural correctness.

        Args:
            cedar_policy: The Cedar policy to validate

        Raises:
            ValueError: If policy is invalid
        """
        policy_lower = cedar_policy.lower()

        # Check for permit or forbid statement
        if "permit" not in policy_lower and "forbid" not in policy_lower:
            raise ValueError("Cedar policy must contain 'permit' or 'forbid' statement")

        # Check for principal
        if "principal" not in policy_lower:
            raise ValueError("Cedar policy must define 'principal'")

        # Check for action
        if "action" not in policy_lower:
            raise ValueError("Cedar policy must define 'action'")

        # Check for resource
        if "resource" not in policy_lower:
            raise ValueError("Cedar policy must define 'resource'")

        # Check for statement terminator (semicolon)
        if not cedar_policy.rstrip().endswith(";"):
            raise ValueError("Cedar policy must end with semicolon")

        logger.debug("cedar_policy_validation_passed", policy_length=len(cedar_policy))

    def _get_mock_rego_policy(self, policy: Policy) -> str:
        """
        Generate a mock OPA Rego policy for TEST_MODE.

        Args:
            policy: The policy to translate

        Returns:
            str: A mock Rego policy
        """
        # Generate a realistic Rego policy based on the input policy
        subject_check = f'input.user.role == "{policy.subject}"'
        resource_check = f'input.resource.type == "{policy.resource}"'
        action_check = f'input.action == "{policy.action}"'

        # Add conditions if present
        conditions_check = ""
        if policy.conditions:
            # Simple conversion - in real scenario would parse the conditions
            conditions_check = f"\n    # Conditions: {policy.conditions}"

        rego_policy = f"""package authz

# {policy.description or "Auto-generated policy"}
# Subject: {policy.subject}
# Resource: {policy.resource}
# Action: {policy.action}
allow {{
    {subject_check}
    {resource_check}
    {action_check}{conditions_check}
}}"""
        return rego_policy

    def _get_mock_cedar_policy(self, policy: Policy) -> str:
        """
        Generate a mock AWS Cedar policy for TEST_MODE.

        Args:
            policy: The policy to translate

        Returns:
            str: A mock Cedar policy
        """
        # Generate a realistic Cedar policy based on the input policy
        principal = f'principal in Role::"{policy.subject}"'
        action_str = f'action == Action::"{policy.action}"'
        resource = f'resource in ResourceType::"{policy.resource}"'

        # Add conditions if present
        when_clause = ""
        if policy.conditions:
            when_clause = f"""
when {{
    // {policy.conditions}
    context.conditions == true
}}"""

        cedar_policy = f"""// {policy.description or "Auto-generated policy"}
// Subject: {policy.subject}
// Resource: {policy.resource}
// Action: {policy.action}
permit (
    {principal},
    {action_str},
    {resource}
){when_clause};"""
        return cedar_policy
