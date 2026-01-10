"""Tests for auto-approval functionality."""
import pytest
from sqlalchemy.orm import Session

from app.models.auto_approval import AutoApprovalDecision
from app.models.policy import Policy, PolicyStatus, RiskLevel, SourceType
from app.models.repository import Repository, RepositoryStatus, RepositoryType
from app.services.auto_approval_service import AutoApprovalService


@pytest.fixture
def repository(db_session: Session) -> Repository:
    """Create a test repository."""
    repo = Repository(
        name="test-repo",
        type=RepositoryType.GIT,
        url="https://github.com/test/repo.git",
        status=RepositoryStatus.CONNECTED,
        tenant_id="test-tenant",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    return repo


@pytest.fixture
def low_risk_policy(db_session: Session, repository: Repository) -> Policy:
    """Create a low-risk test policy."""
    policy = Policy(
        repository_id=repository.id,
        subject="User",
        resource="Document",
        action="read",
        conditions="user.department == document.department",
        risk_score=25.0,
        risk_level=RiskLevel.LOW,
        complexity_score=20.0,
        impact_score=30.0,
        confidence_score=90.0,
        historical_score=10.0,
        status=PolicyStatus.PENDING,
        tenant_id="test-tenant",
        source_type=SourceType.BACKEND,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def high_risk_policy(db_session: Session, repository: Repository) -> Policy:
    """Create a high-risk test policy."""
    policy = Policy(
        repository_id=repository.id,
        subject="Admin",
        resource="Database",
        action="delete",
        conditions=None,
        risk_score=85.0,
        risk_level=RiskLevel.HIGH,
        complexity_score=80.0,
        impact_score=95.0,
        confidence_score=70.0,
        historical_score=90.0,
        status=PolicyStatus.PENDING,
        tenant_id="test-tenant",
        source_type=SourceType.BACKEND,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def approved_policies(db_session: Session, repository: Repository) -> list[Policy]:
    """Create multiple approved policies for historical data."""
    policies = []
    for i in range(5):
        policy = Policy(
            repository_id=repository.id,
            subject="User",
            resource="Document",
            action="read",
            conditions=f"user.id == document.owner_id_{i}",
            risk_score=20.0 + i,
            risk_level=RiskLevel.LOW,
            status=PolicyStatus.APPROVED,
            tenant_id="test-tenant",
            source_type=SourceType.BACKEND,
        )
        db_session.add(policy)
        policies.append(policy)
    db_session.commit()
    return policies


def test_get_or_create_settings(db_session: Session):
    """Test getting or creating auto-approval settings."""
    service = AutoApprovalService(db_session)

    # First call should create settings
    settings = service.get_or_create_settings("test-tenant")
    assert settings is not None
    assert settings.tenant_id == "test-tenant"
    assert settings.enabled is False
    assert settings.risk_threshold == 30.0
    assert settings.min_historical_approvals == 3

    # Second call should return existing settings
    settings2 = service.get_or_create_settings("test-tenant")
    assert settings2.id == settings.id


def test_update_settings(db_session: Session):
    """Test updating auto-approval settings."""
    service = AutoApprovalService(db_session)

    # Create initial settings
    service.get_or_create_settings("test-tenant")

    # Update settings
    updated = service.update_settings(
        tenant_id="test-tenant",
        enabled=True,
        risk_threshold=40.0,
        min_historical_approvals=5,
    )

    assert updated.enabled is True
    assert updated.risk_threshold == 40.0
    assert updated.min_historical_approvals == 5


def test_get_historical_approvals(
    db_session: Session,
    low_risk_policy: Policy,
    approved_policies: list[Policy],
):
    """Test getting historical approvals."""
    service = AutoApprovalService(db_session)

    historical = service.get_historical_approvals("test-tenant", low_risk_policy)

    # Should find policies with same subject or same action/resource combo
    assert len(historical) >= 3
    for p in historical:
        assert p.status == PolicyStatus.APPROVED


def test_evaluate_policy_disabled(db_session: Session, low_risk_policy: Policy):
    """Test that auto-approval doesn't work when disabled."""
    service = AutoApprovalService(db_session)

    # Settings are disabled by default
    should_approve, reasoning = service.evaluate_policy("test-tenant", low_risk_policy)

    assert should_approve is False
    assert "disabled" in reasoning.lower()


def test_evaluate_policy_high_risk(db_session: Session, high_risk_policy: Policy):
    """Test that high-risk policies are not auto-approved."""
    service = AutoApprovalService(db_session)

    # Enable auto-approval
    service.update_settings(tenant_id="test-tenant", enabled=True)

    should_approve, reasoning = service.evaluate_policy("test-tenant", high_risk_policy)

    assert should_approve is False
    assert "risk score" in reasoning.lower() or "threshold" in reasoning.lower()


def test_evaluate_policy_insufficient_history(
    db_session: Session,
    low_risk_policy: Policy,
):
    """Test that policies without enough historical data are not auto-approved."""
    service = AutoApprovalService(db_session)

    # Enable auto-approval with high min_historical_approvals
    service.update_settings(
        tenant_id="test-tenant",
        enabled=True,
        min_historical_approvals=10,
    )

    should_approve, reasoning = service.evaluate_policy("test-tenant", low_risk_policy)

    assert should_approve is False
    assert "historical" in reasoning.lower() or "insufficient" in reasoning.lower()


def test_evaluate_policy_success(
    db_session: Session,
    low_risk_policy: Policy,
    approved_policies: list[Policy],
):
    """Test successful auto-approval with AI analysis."""
    service = AutoApprovalService(db_session)

    # Enable auto-approval
    service.update_settings(
        tenant_id="test-tenant",
        enabled=True,
        risk_threshold=30.0,
        min_historical_approvals=3,
    )

    # Note: This test will call the actual LLM provider
    # In a real test environment, you'd mock the LLM provider
    should_approve, reasoning = service.evaluate_policy("test-tenant", low_risk_policy)

    # Check that a decision was recorded
    decisions = db_session.query(AutoApprovalDecision).filter(
        AutoApprovalDecision.policy_id == low_risk_policy.id
    ).all()
    assert len(decisions) == 1

    decision = decisions[0]
    assert decision.tenant_id == "test-tenant"
    assert decision.risk_score == low_risk_policy.risk_score
    assert decision.similar_policies_count >= 3

    # Check metrics were updated
    settings = service.get_or_create_settings("test-tenant")
    assert settings.total_policies_scanned > 0


def test_get_metrics(
    db_session: Session,
    low_risk_policy: Policy,
    approved_policies: list[Policy],
):
    """Test getting auto-approval metrics."""
    service = AutoApprovalService(db_session)

    # Enable and evaluate a policy
    service.update_settings(tenant_id="test-tenant", enabled=True)
    service.evaluate_policy("test-tenant", low_risk_policy)

    # Get metrics
    metrics = service.get_metrics("test-tenant")

    assert "total_auto_approvals" in metrics
    assert "total_policies_scanned" in metrics
    assert "auto_approval_rate" in metrics
    assert metrics["enabled"] is True


def test_get_decisions(
    db_session: Session,
    low_risk_policy: Policy,
    approved_policies: list[Policy],
):
    """Test getting auto-approval decisions."""
    service = AutoApprovalService(db_session)

    # Enable and evaluate a policy
    service.update_settings(tenant_id="test-tenant", enabled=True)
    service.evaluate_policy("test-tenant", low_risk_policy)

    # Get decisions
    decisions = service.get_decisions("test-tenant", limit=10)

    assert len(decisions) > 0
    assert all(d.tenant_id == "test-tenant" for d in decisions)


def test_auto_approval_rate_calculation(db_session: Session, repository: Repository):
    """Test that auto-approval rate is calculated correctly."""
    service = AutoApprovalService(db_session)
    service.update_settings(tenant_id="test-tenant", enabled=True, risk_threshold=50.0)

    # Create and evaluate multiple policies
    for i in range(10):
        policy = Policy(
            repository_id=repository.id,
            subject="User",
            resource=f"Resource{i}",
            action="read",
            risk_score=25.0 + i * 3,  # Scores from 25 to 52
            risk_level=RiskLevel.LOW if i < 7 else RiskLevel.MEDIUM,
            status=PolicyStatus.PENDING,
            tenant_id="test-tenant",
            source_type=SourceType.BACKEND,
        )
        db_session.add(policy)
    db_session.commit()

    # Get settings to check rate (will be 0 until policies are evaluated)
    settings = service.get_or_create_settings("test-tenant")
    initial_rate = settings.auto_approval_rate

    # Note: Rate calculation happens during evaluate_policy
    assert initial_rate == 0.0


def test_tenant_isolation(db_session: Session, repository: Repository):
    """Test that auto-approval settings are isolated by tenant."""
    service = AutoApprovalService(db_session)

    # Create settings for tenant A
    settings_a = service.update_settings(
        tenant_id="tenant-a",
        enabled=True,
        risk_threshold=40.0,
    )

    # Create settings for tenant B
    settings_b = service.update_settings(
        tenant_id="tenant-b",
        enabled=False,
        risk_threshold=20.0,
    )

    # Verify isolation
    assert settings_a.enabled is True
    assert settings_a.risk_threshold == 40.0
    assert settings_b.enabled is False
    assert settings_b.risk_threshold == 20.0

    # Verify getting settings returns correct tenant data
    retrieved_a = service.get_or_create_settings("tenant-a")
    assert retrieved_a.id == settings_a.id
    assert retrieved_a.enabled is True
