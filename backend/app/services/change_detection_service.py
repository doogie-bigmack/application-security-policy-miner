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

        # Determine priority based on change type
        if change.change_type == ChangeType.DELETED:
            priority = WorkItemPriority.HIGH
        elif change.change_type == ChangeType.MODIFIED:
            priority = WorkItemPriority.MEDIUM
        elif change.change_type == ChangeType.ADDED:
            priority = WorkItemPriority.LOW

        title = f"Review {change.change_type.value} policy: {change.after_subject or change.before_subject}"

        work_item = WorkItem(
            policy_change_id=change.id,
            repository_id=change.repository_id,
            title=title,
            description=change.description,
            status=WorkItemStatus.OPEN,
            priority=priority,
            tenant_id=tenant_id,
        )

        self.db.add(work_item)
        self.db.commit()
        self.db.refresh(work_item)

        logger.info(f"Created work item {work_item.id} for policy change {change.id}")
        return work_item
