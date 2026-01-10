"""Translation Verification Service - Verify semantic equivalence of translated policies."""

import re
from typing import Any

import structlog

from app.models.policy import Policy
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger(__name__)


class TranslationVerificationService:
    """Service for verifying semantic equivalence of translated policies."""

    def __init__(self):
        """Initialize the translation verification service."""
        self.llm_provider = get_llm_provider()
        logger.info("Translation verification service initialized")

    async def generate_test_cases(
        self, policy: Policy, original_code: str, translated_policy: str, format: str
    ) -> list[dict[str, Any]]:
        """
        Generate comprehensive test cases for a policy.

        Args:
            policy: The policy object
            original_code: Original authorization code
            translated_policy: Translated policy (Rego, Cedar, etc.)
            format: Target format (rego, cedar, json)

        Returns:
            List of test case dictionaries with inputs and expected outputs
        """
        logger.info(
            "Generating test cases",
            policy_id=policy.id,
            format=format,
        )

        prompt = f"""Generate comprehensive test cases for verifying semantic equivalence between original authorization code and translated policy.

Original Authorization Code:
```
{original_code}
```

Translated Policy ({format.upper()}):
```
{translated_policy}
```

Policy Details:
- Subject (Who): {policy.subject}
- Resource (What): {policy.resource}
- Action (How): {policy.action}
- Conditions (When): {policy.conditions}

Generate test cases that cover:
1. Happy path (authorized access)
2. Unauthorized access (different roles)
3. Edge cases (boundary conditions)
4. Conditional logic (all when clauses)
5. Negative cases (explicit denials)

For each test case, provide:
- Description: What is being tested
- Input: The authorization request context (user, resource, action, conditions)
- Expected Output: Whether access should be ALLOWED or DENIED
- Reasoning: Why this outcome is expected

Return ONLY a JSON array of test cases in this format:
```json
[
  {{
    "description": "Manager approves expense under limit",
    "input": {{
      "user": {{"role": "Manager", "department": "Finance"}},
      "resource": {{"type": "Expense", "amount": 4000}},
      "action": "approve"
    }},
    "expected_output": "ALLOWED",
    "reasoning": "Manager role with expense under $5000 limit"
  }},
  ...
]
```

Generate at least 10 test cases covering all decision paths."""

        try:
            # Use LLM to generate test cases
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_provider.create_message(messages=messages, max_tokens=4000)

            # Extract JSON from markdown code block
            content = response.content[0].text
            json_match = re.search(r"```json\s*(\[.*?\])\s*```", content, re.DOTALL)
            if json_match:
                import json

                test_cases = json.loads(json_match.group(1))
                logger.info("Generated test cases", count=len(test_cases))
                return test_cases
            else:
                logger.error("Failed to extract test cases JSON from response")
                return []

        except Exception as e:
            logger.error("Error generating test cases", error=str(e))
            raise

    async def execute_test_cases(
        self,
        test_cases: list[dict[str, Any]],
        original_code: str,
        translated_policy: str,
        format: str,
    ) -> dict[str, Any]:
        """
        Execute test cases against both original and translated policies.

        Args:
            test_cases: List of test cases to execute
            original_code: Original authorization code
            translated_policy: Translated policy
            format: Target format (rego, cedar, json)

        Returns:
            Dictionary with execution results and comparison
        """
        logger.info(
            "Executing test cases",
            count=len(test_cases),
            format=format,
        )

        results = {
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "test_results": [],
            "equivalence_percentage": 0.0,
            "differences": [],
        }

        for i, test_case in enumerate(test_cases):
            logger.debug(f"Executing test case {i+1}/{len(test_cases)}")

            # Execute against original code (simulated via LLM)
            original_result = await self._execute_original_code(original_code, test_case)

            # Execute against translated policy (simulated via LLM)
            translated_result = await self._execute_translated_policy(
                translated_policy, format, test_case
            )

            # Compare results
            is_match = original_result == translated_result
            test_result = {
                "test_case": test_case,
                "original_result": original_result,
                "translated_result": translated_result,
                "expected_result": test_case["expected_output"],
                "match": is_match,
                "original_correct": original_result == test_case["expected_output"],
                "translated_correct": translated_result == test_case["expected_output"],
            }

            results["test_results"].append(test_result)

            if is_match:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["differences"].append(
                    {
                        "test_case": test_case["description"],
                        "original": original_result,
                        "translated": translated_result,
                        "input": test_case["input"],
                    }
                )

        # Calculate equivalence percentage
        if results["total_tests"] > 0:
            results["equivalence_percentage"] = (
                results["passed"] / results["total_tests"]
            ) * 100

        logger.info(
            "Test execution complete",
            passed=results["passed"],
            failed=results["failed"],
            equivalence_percentage=results["equivalence_percentage"],
        )

        return results

    async def _execute_original_code(
        self, original_code: str, test_case: dict[str, Any]
    ) -> str:
        """Execute test case against original code using LLM simulation."""
        prompt = f"""Analyze the following authorization code and determine if it would ALLOW or DENY access for the given test case.

Original Authorization Code:
```
{original_code}
```

Test Case Input:
{test_case['input']}

Based on the logic in the original code, would this authorization request be ALLOWED or DENIED?

Respond with ONLY one word: ALLOWED or DENIED"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_provider.create_message(messages=messages, max_tokens=100)
            result = response.content[0].text.strip().upper()

            # Normalize response
            if "ALLOWED" in result or "ALLOW" in result:
                return "ALLOWED"
            elif "DENIED" in result or "DENY" in result:
                return "DENIED"
            else:
                logger.warning("Unexpected result from original code execution", result=result)
                return result

        except Exception as e:
            logger.error("Error executing original code", error=str(e))
            return "ERROR"

    async def _execute_translated_policy(
        self, translated_policy: str, format: str, test_case: dict[str, Any]
    ) -> str:
        """Execute test case against translated policy using LLM simulation."""
        prompt = f"""Analyze the following {format.upper()} policy and determine if it would ALLOW or DENY access for the given test case.

Translated Policy ({format.upper()}):
```
{translated_policy}
```

Test Case Input:
{test_case['input']}

Based on the policy rules, would this authorization request be ALLOWED or DENIED?

Respond with ONLY one word: ALLOWED or DENIED"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_provider.create_message(messages=messages, max_tokens=100)
            result = response.content[0].text.strip().upper()

            # Normalize response
            if "ALLOWED" in result or "ALLOW" in result:
                return "ALLOWED"
            elif "DENIED" in result or "DENY" in result:
                return "DENIED"
            else:
                logger.warning("Unexpected result from translated policy execution", result=result)
                return result

        except Exception as e:
            logger.error("Error executing translated policy", error=str(e))
            return "ERROR"

    async def verify_translation(
        self,
        policy: Policy,
        original_code: str,
        translated_policy: str,
        format: str,
    ) -> dict[str, Any]:
        """
        Complete verification workflow: generate tests, execute, and compare.

        Args:
            policy: The policy object
            original_code: Original authorization code
            translated_policy: Translated policy
            format: Target format (rego, cedar, json)

        Returns:
            Complete verification results with test cases and equivalence analysis
        """
        logger.info(
            "Starting translation verification",
            policy_id=policy.id,
            format=format,
        )

        # Generate test cases
        test_cases = await self.generate_test_cases(
            policy, original_code, translated_policy, format
        )

        if not test_cases:
            return {
                "status": "error",
                "message": "Failed to generate test cases",
                "test_cases": [],
                "results": None,
            }

        # Execute test cases
        results = await self.execute_test_cases(
            test_cases, original_code, translated_policy, format
        )

        # Determine overall status
        if results["equivalence_percentage"] == 100:
            status = "verified"
            message = "Translation is semantically equivalent (100% match)"
        elif results["equivalence_percentage"] >= 90:
            status = "mostly_equivalent"
            message = f"Translation is mostly equivalent ({results['equivalence_percentage']:.1f}% match)"
        else:
            status = "not_equivalent"
            message = f"Translation has significant differences ({results['equivalence_percentage']:.1f}% match)"

        verification_result = {
            "status": status,
            "message": message,
            "test_cases": test_cases,
            "results": results,
            "policy_id": policy.id,
            "format": format,
        }

        logger.info(
            "Translation verification complete",
            status=status,
            equivalence_percentage=results["equivalence_percentage"],
        )

        return verification_result
