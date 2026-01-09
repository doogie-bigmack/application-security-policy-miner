"""Change detection service for detecting policy changes between scans."""
import logging
from typing import Any

from anthropic import Anthropic
from sqlalchemy.orm import Session

from app.models import ChangeType, Policy, PolicyChange, WorkItem, WorkItemPriority, WorkItemStatus

logger = logging.getLogger(__name__)


class ChangeDetectionService:
    """Service for detecting and tracking policy changes."""

    def __init__(self, db: Session, api_key: str | None = None):
        """Initialize the change detection service."""
        self.db = db
        self.client = Anthropic(api_key=api_key) if api_key else None

    def detect_changes(self, repository_id: int, tenant_id: str | None = None) -> list[PolicyChange]:
        """
        Detect changes in policies for a repository by comparing current scan to previous scan.

        Args:
            repository_id: The repository ID
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            List of detected policy changes
        """
        logger.info(f"Detecting policy changes for repository {repository_id}")

        # Get all current policies for this repository
        current_policies_query = self.db.query(Policy).filter(Policy.repository_id == repository_id)
        if tenant_id:
            current_policies_query = current_policies_query.filter(Policy.tenant_id == tenant_id)
        current_policies = current_policies_query.all()

        # Get all previous policy changes to find the last scan state
        previous_changes_query = self.db.query(PolicyChange).filter(PolicyChange.repository_id == repository_id)
        if tenant_id:
            previous_changes_query = previous_changes_query.filter(PolicyChange.tenant_id == tenant_id)
        previous_changes = previous_changes_query.all()

        # Build a snapshot of the previous state
        previous_state: dict[str, dict[str, Any]] = {}
        for change in previous_changes:
            # Use the "after" state from previous changes as the baseline
            if change.change_type in [ChangeType.ADDED, ChangeType.MODIFIED]:
                key = self._policy_key(
                    change.after_subject, change.after_resource, change.after_action, change.after_conditions
                )
                previous_state[key] = {
                    "subject": change.after_subject,
                    "resource": change.after_resource,
                    "action": change.after_action,
                    "conditions": change.after_conditions,
                    "policy_id": change.policy_id,
                }

        # Build current state
        current_state: dict[str, dict[str, Any]] = {}
        for policy in current_policies:
            key = self._policy_key(policy.subject, policy.resource, policy.action, policy.conditions)
            current_state[key] = {
                "subject": policy.subject,
                "resource": policy.resource,
                "action": policy.action,
                "conditions": policy.conditions,
                "policy_id": policy.id,
            }

        changes: list[PolicyChange] = []

        # Detect new policies (added)
        for key, current_data in current_state.items():
            if key not in previous_state:
                change = PolicyChange(
                    repository_id=repository_id,
                    policy_id=current_data["policy_id"],
                    previous_policy_id=None,
                    change_type=ChangeType.ADDED,
                    after_subject=current_data["subject"],
                    after_resource=current_data["resource"],
                    after_action=current_data["action"],
                    after_conditions=current_data["conditions"],
                    tenant_id=tenant_id,
                )
                change.description = f"New policy added: {current_data['subject']} can {current_data['action']} {current_data['resource']}"
                change.diff_summary = f"+ {current_data['subject']} -> {current_data['action']} -> {current_data['resource']}"
                changes.append(change)

        # Detect deleted policies
        for key, previous_data in previous_state.items():
            if key not in current_state:
                change = PolicyChange(
                    repository_id=repository_id,
                    policy_id=None,
                    previous_policy_id=previous_data["policy_id"],
                    change_type=ChangeType.DELETED,
                    before_subject=previous_data["subject"],
                    before_resource=previous_data["resource"],
                    before_action=previous_data["action"],
                    before_conditions=previous_data["conditions"],
                    tenant_id=tenant_id,
                )
                change.description = f"Policy deleted: {previous_data['subject']} can {previous_data['action']} {previous_data['resource']}"
                change.diff_summary = f"- {previous_data['subject']} -> {previous_data['action']} -> {previous_data['resource']}"
                changes.append(change)

        # Detect modified policies (same key but different details)
        for key in set(current_state.keys()) & set(previous_state.keys()):
            current_data = current_state[key]
            previous_data = previous_state[key]

            # Check if any field changed
            if (
                current_data["subject"] != previous_data["subject"]
                or current_data["resource"] != previous_data["resource"]
                or current_data["action"] != previous_data["action"]
                or current_data["conditions"] != previous_data["conditions"]
            ):
                change = PolicyChange(
                    repository_id=repository_id,
                    policy_id=current_data["policy_id"],
                    previous_policy_id=previous_data["policy_id"],
                    change_type=ChangeType.MODIFIED,
                    before_subject=previous_data["subject"],
                    before_resource=previous_data["resource"],
                    before_action=previous_data["action"],
                    before_conditions=previous_data["conditions"],
                    after_subject=current_data["subject"],
                    after_resource=current_data["resource"],
                    after_action=current_data["action"],
                    after_conditions=current_data["conditions"],
                    tenant_id=tenant_id,
                )
                change.description = self._generate_change_description(previous_data, current_data)
                change.diff_summary = self._generate_diff_summary(previous_data, current_data)
                changes.append(change)

        # Save all changes
        for change in changes:
            self.db.add(change)
        self.db.commit()

        # Auto-create work items for changes
        for change in changes:
            self._create_work_item(change, tenant_id)

        logger.info(f"Detected {len(changes)} policy changes")
        return changes

    def _policy_key(self, subject: str | None, resource: str | None, action: str | None, conditions: str | None) -> str:
        """Generate a unique key for a policy."""
        return f"{subject or ''}:{resource or ''}:{action or ''}:{conditions or ''}"

    def _generate_change_description(self, before: dict[str, Any], after: dict[str, Any]) -> str:
        """Generate a human-readable description of the change."""
        changes_list = []
        if before["subject"] != after["subject"]:
            changes_list.append(f"subject changed from '{before['subject']}' to '{after['subject']}'")
        if before["resource"] != after["resource"]:
            changes_list.append(f"resource changed from '{before['resource']}' to '{after['resource']}'")
        if before["action"] != after["action"]:
            changes_list.append(f"action changed from '{before['action']}' to '{after['action']}'")
        if before["conditions"] != after["conditions"]:
            changes_list.append("conditions changed")

        return "Policy modified: " + ", ".join(changes_list)

    def _generate_diff_summary(self, before: dict[str, Any], after: dict[str, Any]) -> str:
        """Generate a diff summary."""
        lines = []
        if before["subject"] != after["subject"]:
            lines.append(f"- Subject: {before['subject']}")
            lines.append(f"+ Subject: {after['subject']}")
        if before["resource"] != after["resource"]:
            lines.append(f"- Resource: {before['resource']}")
            lines.append(f"+ Resource: {after['resource']}")
        if before["action"] != after["action"]:
            lines.append(f"- Action: {before['action']}")
            lines.append(f"+ Action: {after['action']}")
        if before["conditions"] != after["conditions"]:
            lines.append(f"- Conditions: {before['conditions'] or 'None'}")
            lines.append(f"+ Conditions: {after['conditions'] or 'None'}")

        return "\n".join(lines)

    def _create_work_item(self, change: PolicyChange, tenant_id: str | None = None) -> WorkItem:
        """Auto-create a work item for a policy change."""
        priority = WorkItemPriority.MEDIUM
        is_spaghetti = False
        refactoring_suggestion = None

        # Determine priority based on change type
        if change.change_type == ChangeType.DELETED:
            priority = WorkItemPriority.HIGH
        elif change.change_type == ChangeType.MODIFIED:
            priority = WorkItemPriority.MEDIUM
        elif change.change_type == ChangeType.ADDED:
            # Check if this is new inline authorization (spaghetti code)
            is_spaghetti = self._is_new_spaghetti_code(change)
            if is_spaghetti:
                priority = WorkItemPriority.HIGH
                refactoring_suggestion = self._generate_refactoring_suggestion(change)
            else:
                priority = WorkItemPriority.LOW

        title = f"Review {change.change_type.value} policy: {change.after_subject or change.before_subject}"
        if is_spaghetti:
            title = f"⚠️ NEW SPAGHETTI DETECTED: {change.after_subject or change.before_subject}"

        work_item = WorkItem(
            policy_change_id=change.id,
            repository_id=change.repository_id,
            title=title,
            description=change.description,
            status=WorkItemStatus.OPEN,
            priority=priority,
            is_spaghetti_detection=1 if is_spaghetti else 0,
            refactoring_suggestion=refactoring_suggestion,
            tenant_id=tenant_id,
        )

        self.db.add(work_item)
        self.db.commit()
        self.db.refresh(work_item)

        if is_spaghetti:
            logger.warning(
                f"NEW SPAGHETTI DETECTED: Created high-priority work item {work_item.id} for inline authorization in policy change {change.id}"
            )
        else:
            logger.info(f"Created work item {work_item.id} for policy change {change.id}")

        return work_item

    def _is_new_spaghetti_code(self, change: PolicyChange) -> bool:
        """
        Detect if a newly added policy represents inline authorization (spaghetti code).

        Spaghetti code indicators:
        - Policy is being ADDED (not modified or deleted)
        - Contains inline authorization logic rather than centralized PBAC calls
        """
        if change.change_type != ChangeType.ADDED:
            return False

        # Get the policy to check its evidence for inline patterns
        if not change.policy_id:
            return False

        policy = self.db.query(Policy).filter(Policy.id == change.policy_id).first()
        if not policy:
            return False

        # Check if the policy has evidence indicating inline authorization
        # Inline authorization patterns typically appear in code as:
        # - if statements with permission checks
        # - role-based conditionals embedded in business logic
        # - Direct database queries for permissions

        # For now, we'll flag any new policy as potential spaghetti
        # In a production system, you'd analyze the evidence to determine
        # if it's truly inline vs centralized PBAC

        # Check evidence for inline patterns
        if policy.evidence:
            for evidence in policy.evidence:
                # Look for inline authorization patterns in code snippets
                code_snippet = evidence.code_snippet.lower() if evidence.code_snippet else ""

                # Inline authorization indicators
                inline_patterns = [
                    "if user.role",
                    "if current_user",
                    "if request.user",
                    "if (user.",
                    "hasrole(",
                    "checkpermission(",
                    "user.has_permission",
                    "can_access",
                    "is_admin",
                    "is_superuser",
                    "@requires_role",
                    "@permission_required",
                    "authorize(",
                ]

                # Check if any inline pattern is found
                for pattern in inline_patterns:
                    if pattern in code_snippet:
                        return True

        return False

    def _generate_refactoring_suggestion(self, change: PolicyChange) -> str:
        """Generate an AI-powered refactoring suggestion using Claude Agent SDK."""
        if not self.client:
            return "AI refactoring suggestions require ANTHROPIC_API_KEY to be configured."

        # Get policy details
        policy = self.db.query(Policy).filter(Policy.id == change.policy_id).first()
        if not policy or not policy.evidence:
            return "Unable to generate refactoring suggestion: no policy evidence available."

        # Build prompt for Claude
        evidence_text = ""
        for idx, evidence in enumerate(policy.evidence[:3]):  # Limit to first 3 pieces of evidence
            evidence_text += f"\n\nEvidence {idx + 1} ({evidence.file_path}:{evidence.line_start}-{evidence.line_end}):\n"
            evidence_text += evidence.code_snippet or ""

        prompt = f"""You are a security architect helping developers migrate from inline authorization (spaghetti code) to centralized Policy-Based Access Control (PBAC).

**Current Inline Authorization Code:**
{evidence_text}

**Policy Details:**
- Subject: {policy.subject}
- Resource: {policy.resource}
- Action: {policy.action}
- Conditions: {policy.conditions or 'None'}

**Task:** Generate a concise refactoring suggestion (max 500 words) that:
1. Explains why this inline authorization is problematic
2. Shows how to externalize this policy to a PBAC platform (OPA, AWS Verified Permissions, etc.)
3. Provides example refactored code that calls the PBAC platform instead
4. Highlights the benefits (easier auditing, centralized management, separation of concerns)

**Output Format:** Plain text recommendation that a developer can immediately understand and implement.
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            suggestion = response.content[0].text
            return suggestion

        except Exception as e:
            logger.error(f"Failed to generate refactoring suggestion: {e}")
            return f"Failed to generate AI suggestion: {str(e)}"
