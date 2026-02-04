"""Policy translation service for converting policies to various PBAC formats."""

import json

import structlog

from app.models.policy import Policy
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger(__name__)


class TranslationService:
    """Service for translating policies to PBAC platform formats."""

    def __init__(self):
        """Initialize the translation service."""
        self.llm_provider = get_llm_provider()

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
        logger.info("translating_policy_to_rego", policy_id=policy.id)

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
        logger.info("translating_policy_to_cedar", policy_id=policy.id)

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

    async def translate_to_all_formats(
        self, policy: Policy
    ) -> dict[str, str]:
        """
        Translate a policy to all supported formats (Rego, Cedar, JSON).

        Args:
            policy: The policy to translate

        Returns:
            dict: Dictionary with format names as keys and translated policies as values
                 Format: {"rego": "...", "cedar": "...", "json": "..."}

        Raises:
            ValueError: If any translation fails
        """
        logger.info(
            "translating_policy_to_all_formats",
            policy_id=policy.id,
        )

        translations = {}

        try:
            # Translate to all formats
            translations["rego"] = await self.translate_to_rego(policy)
            translations["cedar"] = await self.translate_to_cedar(policy)
            translations["json"] = await self.translate_to_json(policy)

            logger.info(
                "multi_format_translation_successful",
                policy_id=policy.id,
                formats=list(translations.keys()),
            )

            return translations

        except Exception as e:
            logger.error(
                "multi_format_translation_failed",
                policy_id=policy.id,
                error=str(e),
            )
            raise ValueError(f"Failed to translate policy to all formats: {e}") from e

    async def verify_semantic_equivalence(
        self, policy: Policy, translations: dict[str, str]
    ) -> dict[str, bool]:
        """
        Verify that all translations are semantically equivalent.

        Uses Claude to analyze whether the translations preserve the same
        authorization logic as the original policy.

        Args:
            policy: The original policy
            translations: Dictionary of format -> translated policy

        Returns:
            dict: Dictionary with format names as keys and boolean equivalence as values
                 Format: {"rego": True, "cedar": True, "json": True}
        """
        logger.info(
            "verifying_semantic_equivalence",
            policy_id=policy.id,
            formats=list(translations.keys()),
        )

        equivalence_results = {}

        # Build verification prompt
        prompt = self._build_equivalence_verification_prompt(policy, translations)

        try:
            # Call Claude to verify equivalence
            response_text = self.llm_provider.create_message(
                prompt=prompt,
                max_tokens=1500,
                temperature=0,
            )

            # Parse the response to extract equivalence results
            equivalence_results = self._parse_equivalence_response(response_text)

            logger.info(
                "semantic_equivalence_verification_complete",
                policy_id=policy.id,
                results=equivalence_results,
            )

            return equivalence_results

        except Exception as e:
            logger.error(
                "semantic_equivalence_verification_failed",
                policy_id=policy.id,
                error=str(e),
            )
            # Default to False for all formats if verification fails
            return {fmt: False for fmt in translations.keys()}

    def _build_equivalence_verification_prompt(
        self, policy: Policy, translations: dict[str, str]
    ) -> str:
        """Build prompt for semantic equivalence verification."""
        return f"""You are an expert in authorization policies and semantic analysis.

**Original Policy:**
- Subject (Who): {policy.subject}
- Resource (What): {policy.resource}
- Action (How): {policy.action}
- Conditions (When): {policy.conditions}
- Description: {policy.description}

**Translations:**

**OPA Rego:**
```rego
{translations.get('rego', 'N/A')}
```

**AWS Cedar:**
```cedar
{translations.get('cedar', 'N/A')}
```

**Custom JSON:**
```json
{translations.get('json', 'N/A')}
```

**Task:** Analyze whether each translation preserves the exact same authorization logic as the original policy.

For each format (Rego, Cedar, JSON), determine if it would produce the SAME authorization decisions as the original policy for ALL possible inputs.

**Response Format (JSON only):**
```json
{{
    "rego": true/false,
    "cedar": true/false,
    "json": true/false,
    "explanation": "Brief explanation of your analysis"
}}
```

Provide ONLY the JSON response above, no other text."""

    def _parse_equivalence_response(self, response_text: str) -> dict[str, bool]:
        """Parse the equivalence verification response from Claude."""
        text = response_text.strip()

        # Extract JSON from response
        if "```json" in text:
            start = text.find("```json") + len("```json")
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()

        # Parse JSON
        try:
            result = json.loads(text)
            return {
                "rego": result.get("rego", False),
                "cedar": result.get("cedar", False),
                "json": result.get("json", False),
            }
        except json.JSONDecodeError:
            logger.error(
                "failed_to_parse_equivalence_response",
                response_text=text,
            )
            return {"rego": False, "cedar": False, "json": False}
