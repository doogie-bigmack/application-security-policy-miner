"""Tests for change detection service."""
import pytest
from sqlalchemy.orm import Session

from app.models import ChangeType, Policy, PolicyChange, Repository, WorkItem, WorkItemStatus
from app.services.change_detection_service import ChangeDetectionService


@pytest.fixture
def sample_repository(db: Session) -> Repository:
    """Create a sample repository for testing."""
    repo = Repository(
        name="Test Repository",
        repository_type="git",
        source_url="https://github.com/test/repo.git",
        status="connected",
        tenant_id="test-tenant",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


@pytest.fixture
def sample_policies(db: Session, sample_repository: Repository) -> list[Policy]:
    """Create sample policies for testing."""
    policies = [
        Policy(
            repository_id=sample_repository.id,
            subject="Manager",
            resource="Expense Report",
            action="approve",
            conditions="amount < 5000",
            tenant_id="test-tenant",
        ),
        Policy(
            repository_id=sample_repository.id,
            subject="Admin",
            resource="User Account",
            action="delete",
            conditions=None,
            tenant_id="test-tenant",
        ),
    ]
    for policy in policies:
        db.add(policy)
    db.commit()
    for policy in policies:
        db.refresh(policy)
    return policies


def test_detect_no_changes_on_first_scan(db: Session, sample_repository: Repository, sample_policies: list[Policy]):
    """Test that no changes are detected on first scan (no baseline)."""
    service = ChangeDetectionService(db)
    changes = service.detect_changes(sample_repository.id, "test-tenant")

    # First scan should have no changes since there's no previous state
    assert len(changes) == 0


def test_detect_added_policy(db: Session, sample_repository: Repository, sample_policies: list[Policy]):
    """Test detecting a newly added policy."""
    service = ChangeDetectionService(db)

    # Create baseline by recording initial state as changes
    for policy in sample_policies:
        change = PolicyChange(
            repository_id=sample_repository.id,
            policy_id=policy.id,
            change_type=ChangeType.ADDED,
            after_subject=policy.subject,
            after_resource=policy.resource,
            after_action=policy.action,
            after_conditions=policy.conditions,
            tenant_id="test-tenant",
        )
        db.add(change)
    db.commit()

    # Add a new policy
    new_policy = Policy(
        repository_id=sample_repository.id,
        subject="Director",
        resource="Budget",
        action="approve",
        conditions="amount < 100000",
        tenant_id="test-tenant",
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)

    # Detect changes
    changes = service.detect_changes(sample_repository.id, "test-tenant")

    # Should detect 1 new added policy
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.ADDED
    assert changes[0].after_subject == "Director"
    assert changes[0].after_resource == "Budget"
    assert changes[0].after_action == "approve"


def test_detect_deleted_policy(db: Session, sample_repository: Repository, sample_policies: list[Policy]):
    """Test detecting a deleted policy."""
    service = ChangeDetectionService(db)

    # Create baseline
    for policy in sample_policies:
        change = PolicyChange(
            repository_id=sample_repository.id,
            policy_id=policy.id,
            change_type=ChangeType.ADDED,
            after_subject=policy.subject,
            after_resource=policy.resource,
            after_action=policy.action,
            after_conditions=policy.conditions,
            tenant_id="test-tenant",
        )
        db.add(change)
    db.commit()

    # Delete one policy
    policy_to_delete = sample_policies[0]
    db.delete(policy_to_delete)
    db.commit()

    # Detect changes
    changes = service.detect_changes(sample_repository.id, "test-tenant")

    # Should detect 1 deleted policy
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.DELETED
    assert changes[0].before_subject == "Manager"
    assert changes[0].before_resource == "Expense Report"


def test_detect_modified_policy(db: Session, sample_repository: Repository, sample_policies: list[Policy]):
    """Test detecting a modified policy."""
    service = ChangeDetectionService(db)

    # Create baseline
    for policy in sample_policies:
        change = PolicyChange(
            repository_id=sample_repository.id,
            policy_id=policy.id,
            change_type=ChangeType.ADDED,
            after_subject=policy.subject,
            after_resource=policy.resource,
            after_action=policy.action,
            after_conditions=policy.conditions,
            tenant_id="test-tenant",
        )
        db.add(change)
    db.commit()

    # Modify a policy
    policy_to_modify = sample_policies[0]
    policy_to_modify.conditions = "amount < 10000"  # Changed from 5000 to 10000
    db.commit()

    # Detect changes
    changes = service.detect_changes(sample_repository.id, "test-tenant")

    # Should detect 1 modified policy
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.MODIFIED
    assert changes[0].before_conditions == "amount < 5000"
    assert changes[0].after_conditions == "amount < 10000"
    assert "conditions changed" in changes[0].description


def test_work_item_auto_creation(db: Session, sample_repository: Repository, sample_policies: list[Policy]):
    """Test that work items are automatically created for changes."""
    service = ChangeDetectionService(db)

    # Create baseline
    for policy in sample_policies:
        change = PolicyChange(
            repository_id=sample_repository.id,
            policy_id=policy.id,
            change_type=ChangeType.ADDED,
            after_subject=policy.subject,
            after_resource=policy.resource,
            after_action=policy.action,
            after_conditions=policy.conditions,
            tenant_id="test-tenant",
        )
        db.add(change)
    db.commit()

    # Add a new policy to trigger change detection
    new_policy = Policy(
        repository_id=sample_repository.id,
        subject="CEO",
        resource="Company Policy",
        action="modify",
        conditions=None,
        tenant_id="test-tenant",
    )
    db.add(new_policy)
    db.commit()

    # Detect changes
    changes = service.detect_changes(sample_repository.id, "test-tenant")

    # Verify work item was created
    work_items = db.query(WorkItem).filter(WorkItem.policy_change_id == changes[0].id).all()
    assert len(work_items) == 1
    assert work_items[0].status == WorkItemStatus.OPEN
    assert "CEO" in work_items[0].title


def test_tenant_isolation(db: Session, sample_repository: Repository):
    """Test that change detection respects tenant isolation."""
    service = ChangeDetectionService(db)

    # Create policies for tenant A
    policy_a = Policy(
        repository_id=sample_repository.id,
        subject="Tenant A Manager",
        resource="Tenant A Resource",
        action="access",
        conditions=None,
        tenant_id="tenant-a",
    )
    db.add(policy_a)
    db.commit()

    # Create baseline for tenant A
    change_a = PolicyChange(
        repository_id=sample_repository.id,
        policy_id=policy_a.id,
        change_type=ChangeType.ADDED,
        after_subject=policy_a.subject,
        after_resource=policy_a.resource,
        after_action=policy_a.action,
        tenant_id="tenant-a",
    )
    db.add(change_a)
    db.commit()

    # Create policy for tenant B
    policy_b = Policy(
        repository_id=sample_repository.id,
        subject="Tenant B Manager",
        resource="Tenant B Resource",
        action="access",
        conditions=None,
        tenant_id="tenant-b",
    )
    db.add(policy_b)
    db.commit()

    # Detect changes for tenant B only
    changes = service.detect_changes(sample_repository.id, "tenant-b")

    # Should detect 1 added policy for tenant B
    assert len(changes) == 1
    assert changes[0].after_subject == "Tenant B Manager"

    # Tenant A's policy should not be detected
    assert "Tenant A" not in changes[0].after_subject


def test_multiple_changes(db: Session, sample_repository: Repository, sample_policies: list[Policy]):
    """Test detecting multiple types of changes at once."""
    service = ChangeDetectionService(db)

    # Create baseline
    for policy in sample_policies:
        change = PolicyChange(
            repository_id=sample_repository.id,
            policy_id=policy.id,
            change_type=ChangeType.ADDED,
            after_subject=policy.subject,
            after_resource=policy.resource,
            after_action=policy.action,
            after_conditions=policy.conditions,
            tenant_id="test-tenant",
        )
        db.add(change)
    db.commit()

    # Add a new policy
    new_policy = Policy(
        repository_id=sample_repository.id,
        subject="VP",
        resource="Strategic Plan",
        action="review",
        conditions=None,
        tenant_id="test-tenant",
    )
    db.add(new_policy)

    # Modify an existing policy
    sample_policies[0].subject = "Senior Manager"  # Changed from Manager

    # Delete another policy
    db.delete(sample_policies[1])

    db.commit()

    # Detect changes
    changes = service.detect_changes(sample_repository.id, "test-tenant")

    # Should detect 3 changes: 1 added, 1 modified, 1 deleted
    assert len(changes) == 3

    change_types = {change.change_type for change in changes}
    assert ChangeType.ADDED in change_types
    assert ChangeType.MODIFIED in change_types
    assert ChangeType.DELETED in change_types
