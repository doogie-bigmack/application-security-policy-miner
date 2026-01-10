"""Tests for code advisory service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.code_advisory import AdvisoryStatus, CodeAdvisory
from app.models.policy import Evidence, Policy
from app.models.repository import Base, Repository
from app.services.code_advisory_service import CodeAdvisoryService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    yield session
    session.close()


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = Mock()
    provider.create_message = AsyncMock(return_value="""
REFACTORED_CODE:
```python
from opa_client import OPAClient

opa = OPAClient("http://opa:8181")
decision = opa.evaluate_policy("expense_approval", {
    "subject": current_user.role,
    "resource": "ExpenseReport",
    "action": "approve",
    "conditions": {"amount": expense.amount}
})

if decision["allow"]:
    approve_expense(expense)
else:
    raise PermissionError("Not authorized to approve this expense")
```

EXPLANATION:
The inline authorization check `if user.is_manager() and expense.amount < 5000` has been replaced with a call to the OPA (Open Policy Agent) platform. The refactored code:

1. **Removed inline check**: The hardcoded role and amount check is no longer in the application code
2. **Added OPA client**: Instantiates an OPA client pointing to the policy server
3. **Passes context**: Sends the subject (user role), resource (ExpenseReport), action (approve), and conditions (amount) to OPA
4. **Enforces decision**: The application now relies on OPA's decision rather than inline logic

This externalization allows:
- Policy updates without code changes
- Centralized policy management
- Audit trail of authorization decisions
- Consistent enforcement across applications
""")
    return provider


@pytest.mark.asyncio
async def test_generate_advisory_success(db_session, mock_llm_provider):
    """Test successful advisory generation."""
    # Create test data
    repo = Repository(id=1, name="test-repo", type="git", url="https://github.com/test/repo")
    policy = Policy(
        id=1,
        repository_id=1,
        subject="Manager",
        resource="ExpenseReport",
        action="approve",
        conditions="amount < 5000",
        tenant_id="test-tenant",
    )
    evidence = Evidence(
        id=1,
        policy_id=1,
        file_path="app/expense.py",
        line_start=10,
        line_end=15,
        code_snippet="if user.is_manager() and expense.amount < 5000:\n    approve_expense(expense)",
    )

    db_session.add(repo)
    db_session.add(policy)
    db_session.add(evidence)
    db_session.commit()

    # Mock source file
    source_code = """
from models import User, Expense

def process_expense(user: User, expense: Expense):
    # Check permissions
    if user.is_manager() and expense.amount < 5000:
        approve_expense(expense)
    else:
        raise PermissionError("Not authorized")

def approve_expense(expense):
    expense.status = "approved"
    expense.save()
"""

    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm_provider):
        with patch("builtins.open", Mock(return_value=Mock(__enter__=Mock(return_value=Mock(readlines=Mock(return_value=source_code.split("\n"))))))):
            with patch("pathlib.Path.exists", return_value=True):
                service = CodeAdvisoryService(db_session, "test-tenant")
                advisory = await service.generate_advisory(policy_id=1, target_platform="OPA")

    assert advisory is not None
    assert advisory.policy_id == 1
    assert advisory.tenant_id == "test-tenant"
    assert advisory.file_path == "app/expense.py"
    assert advisory.status == AdvisoryStatus.PENDING
    assert "OPA" in advisory.refactored_code or "opa" in advisory.refactored_code
    assert len(advisory.explanation) > 0
    assert advisory.line_start == 10
    assert advisory.line_end == 15


@pytest.mark.asyncio
async def test_generate_advisory_no_policy(db_session, mock_llm_provider):
    """Test advisory generation with non-existent policy."""
    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm_provider):
        service = CodeAdvisoryService(db_session, "test-tenant")
        with pytest.raises(ValueError, match="Policy 999 not found"):
            await service.generate_advisory(policy_id=999)


@pytest.mark.asyncio
async def test_generate_advisory_no_evidence(db_session, mock_llm_provider):
    """Test advisory generation with policy that has no evidence."""
    policy = Policy(
        id=1,
        repository_id=1,
        subject="Manager",
        resource="ExpenseReport",
        action="approve",
        tenant_id="test-tenant",
    )
    db_session.add(policy)
    db_session.commit()

    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm_provider):
        service = CodeAdvisoryService(db_session, "test-tenant")
        with pytest.raises(ValueError, match="Policy 1 has no evidence"):
            await service.generate_advisory(policy_id=1)


def test_detect_language(db_session):
    """Test language detection from file extension."""
    service = CodeAdvisoryService(db_session, "test-tenant")

    assert service._detect_language("app/main.py") == "python"
    assert service._detect_language("src/Main.java") == "java"
    assert service._detect_language("UserController.cs") == "csharp"
    assert service._detect_language("index.js") == "javascript"
    assert service._detect_language("app.ts") == "typescript"
    assert service._detect_language("component.tsx") == "typescript"
    assert service._detect_language("unknown.txt") == "text"


def test_parse_refactoring_response(db_session):
    """Test parsing of AI refactoring response."""
    service = CodeAdvisoryService(db_session, "test-tenant")

    response = """
REFACTORED_CODE:
```python
# New code here
from opa import client
decision = client.evaluate()
```

EXPLANATION:
This refactors the inline check to use OPA. The code now calls the policy server.
"""

    code, explanation = service._parse_refactoring_response(response)

    assert "opa" in code.lower()
    assert "client" in code
    assert "OPA" in explanation
    assert "policy server" in explanation


def test_list_advisories(db_session):
    """Test listing advisories with filtering."""
    # Create test data
    advisory1 = CodeAdvisory(
        policy_id=1,
        tenant_id="test-tenant",
        file_path="app.py",
        original_code="old code",
        refactored_code="new code",
        explanation="test",
        line_start=1,
        line_end=5,
        status=AdvisoryStatus.PENDING,
    )
    advisory2 = CodeAdvisory(
        policy_id=2,
        tenant_id="test-tenant",
        file_path="app2.py",
        original_code="old code 2",
        refactored_code="new code 2",
        explanation="test 2",
        line_start=10,
        line_end=20,
        status=AdvisoryStatus.REVIEWED,
    )

    db_session.add(advisory1)
    db_session.add(advisory2)
    db_session.commit()

    service = CodeAdvisoryService(db_session, "test-tenant")

    # Test list all
    all_advisories = service.list_advisories()
    assert len(all_advisories) == 2

    # Test filter by policy
    policy_advisories = service.list_advisories(policy_id=1)
    assert len(policy_advisories) == 1
    assert policy_advisories[0].policy_id == 1

    # Test filter by status
    pending = service.list_advisories(status=AdvisoryStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].status == AdvisoryStatus.PENDING


def test_update_advisory_status(db_session):
    """Test updating advisory status."""
    advisory = CodeAdvisory(
        policy_id=1,
        tenant_id="test-tenant",
        file_path="app.py",
        original_code="old code",
        refactored_code="new code",
        explanation="test",
        line_start=1,
        line_end=5,
        status=AdvisoryStatus.PENDING,
    )

    db_session.add(advisory)
    db_session.commit()

    service = CodeAdvisoryService(db_session, "test-tenant")

    # Update status
    updated = service.update_advisory(advisory.id, AdvisoryStatus.REVIEWED)

    assert updated is not None
    assert updated.status == AdvisoryStatus.REVIEWED
    assert updated.reviewed_at is not None


def test_delete_advisory(db_session):
    """Test deleting an advisory."""
    advisory = CodeAdvisory(
        policy_id=1,
        tenant_id="test-tenant",
        file_path="app.py",
        original_code="old code",
        refactored_code="new code",
        explanation="test",
        line_start=1,
        line_end=5,
        status=AdvisoryStatus.PENDING,
    )

    db_session.add(advisory)
    db_session.commit()
    advisory_id = advisory.id

    service = CodeAdvisoryService(db_session, "test-tenant")

    # Delete advisory
    success = service.delete_advisory(advisory_id)
    assert success is True

    # Verify deleted
    deleted = service.get_advisory(advisory_id)
    assert deleted is None


def test_tenant_isolation(db_session):
    """Test tenant isolation in advisory access."""
    advisory1 = CodeAdvisory(
        policy_id=1,
        tenant_id="tenant-a",
        file_path="app.py",
        original_code="old code",
        refactored_code="new code",
        explanation="test",
        line_start=1,
        line_end=5,
        status=AdvisoryStatus.PENDING,
    )
    advisory2 = CodeAdvisory(
        policy_id=2,
        tenant_id="tenant-b",
        file_path="app.py",
        original_code="old code",
        refactored_code="new code",
        explanation="test",
        line_start=1,
        line_end=5,
        status=AdvisoryStatus.PENDING,
    )

    db_session.add(advisory1)
    db_session.add(advisory2)
    db_session.commit()

    # Tenant A service
    service_a = CodeAdvisoryService(db_session, "tenant-a")
    advisories_a = service_a.list_advisories()
    assert len(advisories_a) == 1
    assert advisories_a[0].tenant_id == "tenant-a"

    # Tenant B service
    service_b = CodeAdvisoryService(db_session, "tenant-b")
    advisories_b = service_b.list_advisories()
    assert len(advisories_b) == 1
    assert advisories_b[0].tenant_id == "tenant-b"
