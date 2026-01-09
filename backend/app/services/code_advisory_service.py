"""Service for generating code change advisories."""

from datetime import UTC
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.code_advisory import AdvisoryStatus, CodeAdvisory
from app.models.policy import Policy
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger(__name__)


class CodeAdvisoryService:
    """Service for generating code refactoring advisories using AI."""

    def __init__(self, db: Session, tenant_id: str | None = None):
        """Initialize service."""
        self.db = db
        self.tenant_id = tenant_id or "default"
        self.llm_provider = get_llm_provider()

    async def generate_advisory(self, policy_id: int, target_platform: str = "OPA") -> CodeAdvisory:
        """Generate code refactoring advisory for a policy.

        Args:
            policy_id: ID of the policy to refactor
            target_platform: Target PBAC platform (OPA, AWS, Axiomatics, PlainID)

        Returns:
            Generated code advisory

        Raises:
            ValueError: If policy not found or has no evidence
        """
        # Get policy with evidence
        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        if not policy.evidence:
            raise ValueError(f"Policy {policy_id} has no evidence")

        # Get the first evidence item (most representative)
        evidence = policy.evidence[0]

        # Read the original source file
        repo_path = Path(settings.REPO_CLONE_DIR) / str(policy.repository_id)
        source_file = repo_path / evidence.file_path

        if not source_file.exists():
            raise ValueError(f"Source file not found: {evidence.file_path}. Repository may need rescanning.")

        with open(source_file, encoding="utf-8") as f:
            lines = f.readlines()

        # Extract the original code
        original_code = "".join(lines[evidence.line_start - 1 : evidence.line_end])

        # Extract surrounding context for better understanding
        context_start = max(0, evidence.line_start - 10)
        context_end = min(len(lines), evidence.line_end + 10)
        context_code = "".join(lines[context_start:context_end])

        # Generate refactoring using AI
        refactored_code, explanation = await self._generate_refactoring(
            policy=policy,
            original_code=original_code,
            context_code=context_code,
            file_path=evidence.file_path,
            target_platform=target_platform,
        )

        # Create advisory
        advisory = CodeAdvisory(
            policy_id=policy_id,
            tenant_id=self.tenant_id,
            file_path=evidence.file_path,
            original_code=original_code,
            line_start=evidence.line_start,
            line_end=evidence.line_end,
            refactored_code=refactored_code,
            explanation=explanation,
            status=AdvisoryStatus.PENDING,
        )

        self.db.add(advisory)
        self.db.commit()
        self.db.refresh(advisory)

        logger.info(
            "code_advisory_generated",
            advisory_id=advisory.id,
            policy_id=policy_id,
            target_platform=target_platform,
        )

        return advisory

    async def _generate_refactoring(
        self,
        policy: Policy,
        original_code: str,
        context_code: str,
        file_path: str,
        target_platform: str,
    ) -> tuple[str, str]:
        """Generate refactored code using AI.

        Args:
            policy: Policy to refactor
            original_code: Original inline authorization code
            context_code: Surrounding code context
            file_path: Path to the source file
            target_platform: Target PBAC platform

        Returns:
            Tuple of (refactored_code, explanation)
        """
        # Determine language from file extension
        language = self._detect_language(file_path)

        # Build prompt for code refactoring
        prompt = f"""You are a security expert helping externalize inline authorization logic to a Policy-Based Access Control (PBAC) platform.

**Policy to Externalize:**
- Subject (Who): {policy.subject}
- Resource (What): {policy.resource}
- Action (How): {policy.action}
- Conditions (When): {policy.conditions or "None"}

**Original Inline Code ({language}):**
```{language}
{original_code}
```

**Surrounding Context:**
```{language}
{context_code}
```

**Target PBAC Platform:** {target_platform}

**Your Task:**
Generate refactored code that:
1. Removes the inline authorization check
2. Calls the {target_platform} PBAC platform instead
3. Passes the necessary context (subject, resource, action, conditions) to the PBAC platform
4. Maintains the same authorization decision logic
5. Preserves error handling and business logic

**Output Format:**
Provide two sections:

REFACTORED_CODE:
```{language}
[Your refactored code here]
```

EXPLANATION:
[Clear explanation of:
- What was removed (inline auth check)
- What was added (PBAC call)
- How the authorization decision is now made
- What context is passed to {target_platform}
- Any important considerations]
"""

        # Call LLM
        response = await self.llm_provider.create_message(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        # Parse response
        refactored_code, explanation = self._parse_refactoring_response(response)

        return refactored_code, explanation

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        language_map = {
            ".py": "python",
            ".java": "java",
            ".cs": "csharp",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php",
        }
        return language_map.get(ext, "text")

    def _parse_refactoring_response(self, response: str) -> tuple[str, str]:
        """Parse AI response into refactored code and explanation.

        Args:
            response: Raw AI response

        Returns:
            Tuple of (refactored_code, explanation)
        """
        # Extract refactored code
        refactored_code = ""
        if "REFACTORED_CODE:" in response:
            start = response.find("REFACTORED_CODE:")
            end = response.find("EXPLANATION:", start)
            if end == -1:
                end = len(response)
            code_block = response[start:end]

            # Extract from code fence
            lines = code_block.split("\n")
            in_code = False
            code_lines = []
            for line in lines:
                if line.strip().startswith("```"):
                    if in_code:
                        break
                    in_code = True
                    continue
                if in_code:
                    code_lines.append(line)
            refactored_code = "\n".join(code_lines)

        # Extract explanation
        explanation = ""
        if "EXPLANATION:" in response:
            start = response.find("EXPLANATION:")
            explanation = response[start + len("EXPLANATION:") :].strip()

        # Fallback if parsing failed
        if not refactored_code or not explanation:
            logger.warning("refactoring_parse_failed", response_length=len(response))
            refactored_code = refactored_code or response
            explanation = explanation or "Failed to parse explanation from AI response."

        return refactored_code.strip(), explanation.strip()

    def get_advisory(self, advisory_id: int) -> CodeAdvisory | None:
        """Get a code advisory by ID."""
        query = self.db.query(CodeAdvisory).filter(CodeAdvisory.id == advisory_id)

        if self.tenant_id != "default":
            query = query.filter(CodeAdvisory.tenant_id == self.tenant_id)

        return query.first()

    def list_advisories(self, policy_id: int | None = None, status: AdvisoryStatus | None = None) -> list[CodeAdvisory]:
        """List code advisories with optional filtering."""
        query = self.db.query(CodeAdvisory)

        if self.tenant_id != "default":
            query = query.filter(CodeAdvisory.tenant_id == self.tenant_id)

        if policy_id:
            query = query.filter(CodeAdvisory.policy_id == policy_id)

        if status:
            query = query.filter(CodeAdvisory.status == status)

        return query.order_by(CodeAdvisory.created_at.desc()).all()

    def update_advisory(self, advisory_id: int, status: AdvisoryStatus) -> CodeAdvisory | None:
        """Update advisory status."""
        advisory = self.get_advisory(advisory_id)
        if not advisory:
            return None

        advisory.status = status
        if status in [AdvisoryStatus.REVIEWED, AdvisoryStatus.APPLIED, AdvisoryStatus.REJECTED]:
            from datetime import datetime
            advisory.reviewed_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(advisory)

        logger.info("advisory_updated", advisory_id=advisory_id, status=status)
        return advisory

    def delete_advisory(self, advisory_id: int) -> bool:
        """Delete a code advisory."""
        advisory = self.get_advisory(advisory_id)
        if not advisory:
            return False

        self.db.delete(advisory)
        self.db.commit()

        logger.info("advisory_deleted", advisory_id=advisory_id)
        return True
