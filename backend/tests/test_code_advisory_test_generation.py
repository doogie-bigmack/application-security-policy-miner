"""Tests for code advisory test case generation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.code_advisory import AdvisoryStatus, CodeAdvisory
from app.models.policy import Policy, SourceType
from app.models.repository import Base, Repository
from app.models.tenant import Tenant
from app.services.code_advisory_service import CodeAdvisoryService


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("postgresql://policy_miner:dev_password@postgres:5432/policy_miner")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()

    # Create test tenant if not exists
    tenant = session.query(Tenant).filter_by(tenant_id="test-tenant").first()
    if not tenant:
        tenant = Tenant(tenant_id="test-tenant", name="Test Tenant")
        session.add(tenant)
        session.commit()

    yield session

    session.close()


@pytest.fixture
def test_repository(db_session: Session):
    """Create a test repository."""
    repo = Repository(
        name="Test Repo",
        type="git",
        tenant_id="test-tenant",
        url="https://github.com/test/repo.git",
        status="connected",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    return repo


@pytest.fixture
def test_policy(db_session: Session, test_repository: Repository):
    """Create a test policy."""
    policy = Policy(
        repository_id=test_repository.id,
        tenant_id="test-tenant",
        subject="Manager",
        resource="expense_report",
        action="approve",
        conditions="amount < 5000",
        description="Managers can approve expense reports under $5000",
        risk_score=50,
        complexity_score=30,
        impact_score=60,
        confidence_score=80,
        historical_score=0,
        source_type=SourceType.BACKEND,
        status="pending",
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def test_advisory(db_session: Session, test_policy: Policy):
    """Create a test code advisory."""
    advisory = CodeAdvisory(
        policy_id=test_policy.id,
        tenant_id="test-tenant",
        file_path="src/services/expense_service.py",
        original_code='if user.role == "Manager" and expense.amount < 5000:\n    return True\nreturn False',
        line_start=10,
        line_end=12,
        refactored_code='decision = opa.check_policy("expense_approval", {"user": user, "expense": expense})\nreturn decision',
        explanation="Replaced inline role check with OPA policy call",
        status=AdvisoryStatus.PENDING,
    )
    db_session.add(advisory)
    db_session.commit()
    db_session.refresh(advisory)
    return advisory


@pytest.mark.asyncio
async def test_generate_test_cases_success(db_session: Session, test_advisory: CodeAdvisory):
    """Test successful test case generation."""
    mock_llm = MagicMock()
    mock_llm.create_message = AsyncMock(
        return_value=json.dumps([
            {
                "name": "Allow access for authorized manager",
                "scenario": "Manager approving expense under limit",
                "setup": "User with role='Manager', Expense with amount=3000",
                "input": {"user": {"role": "Manager"}, "expense": {"amount": 3000}},
                "expected_original": "true",
                "expected_refactored": "true",
                "assertion": "Both should return true",
            },
            {
                "name": "Deny access for over-limit expense",
                "scenario": "Manager approving expense over limit",
                "setup": "User with role='Manager', Expense with amount=6000",
                "input": {"user": {"role": "Manager"}, "expense": {"amount": 6000}},
                "expected_original": "false",
                "expected_refactored": "false",
                "assertion": "Both should return false",
            },
        ])
    )

    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm):
        service = CodeAdvisoryService(db_session, "test-tenant")
        result = await service.generate_test_cases(test_advisory.id)

        assert result.test_cases is not None
        test_cases = json.loads(result.test_cases)
        assert isinstance(test_cases, list)
        assert len(test_cases) == 2
        assert test_cases[0]["name"] == "Allow access for authorized manager"
        assert test_cases[1]["name"] == "Deny access for over-limit expense"


@pytest.mark.asyncio
async def test_generate_test_cases_advisory_not_found(db_session: Session):
    """Test test case generation for non-existent advisory."""
    mock_llm = MagicMock()

    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm):
        service = CodeAdvisoryService(db_session, "test-tenant")
        with pytest.raises(ValueError, match="Advisory 99999 not found"):
            await service.generate_test_cases(99999)


@pytest.mark.asyncio
async def test_generate_test_cases_with_json_extraction(db_session: Session, test_advisory: CodeAdvisory):
    """Test test case generation with JSON extraction from text response."""
    mock_llm = MagicMock()
    # LLM returns JSON wrapped in markdown
    mock_llm.create_message = AsyncMock(
        return_value='Here are the test cases:\n\n[{"name": "Test case 1", "scenario": "Scenario 1", "setup": "Setup", "input": {}, "expected_original": "true", "expected_refactored": "true", "assertion": "Should match"}]\n\nThese test cases cover the main scenarios.'
    )

    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm):
        service = CodeAdvisoryService(db_session, "test-tenant")
        result = await service.generate_test_cases(test_advisory.id)

        assert result.test_cases is not None
        test_cases = json.loads(result.test_cases)
        assert isinstance(test_cases, list)
        assert len(test_cases) == 1
        assert test_cases[0]["name"] == "Test case 1"


@pytest.mark.asyncio
async def test_generate_test_cases_invalid_json(db_session: Session, test_advisory: CodeAdvisory):
    """Test test case generation with invalid JSON response."""
    mock_llm = MagicMock()
    mock_llm.create_message = AsyncMock(return_value="This is not valid JSON")

    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm):
        service = CodeAdvisoryService(db_session, "test-tenant")
        result = await service.generate_test_cases(test_advisory.id)

        assert result.test_cases is not None
        test_cases = json.loads(result.test_cases)
        assert isinstance(test_cases, list)
        assert len(test_cases) == 1
        assert "error" in test_cases[0]
        assert "Failed to parse test cases" in test_cases[0]["error"]


@pytest.mark.asyncio
async def test_generate_test_cases_language_detection(db_session: Session, test_policy: Policy):
    """Test language detection in test case generation."""
    # Create advisories for different languages
    languages = [
        ("app.py", "python"),
        ("Controller.java", "java"),
        ("Service.cs", "csharp"),
        ("index.ts", "typescript"),
    ]

    for file_path, expected_lang in languages:
        advisory = CodeAdvisory(
            policy_id=test_policy.id,
            tenant_id="test-tenant",
            file_path=file_path,
            original_code="if (authorized) { return true; }",
            line_start=1,
            line_end=1,
            refactored_code="return pbac.check();",
            explanation="Refactored",
            status=AdvisoryStatus.PENDING,
        )
        db_session.add(advisory)
    db_session.commit()

    mock_llm = MagicMock()
    mock_llm.create_message = AsyncMock(
        return_value='[{"name": "Test", "scenario": "S", "setup": "S", "input": {}, "expected_original": "true", "expected_refactored": "true", "assertion": "A"}]'
    )

    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm):
        service = CodeAdvisoryService(db_session, "test-tenant")

        # Verify language detection happens (check that prompt includes the right language)
        advisories = db_session.query(CodeAdvisory).filter(CodeAdvisory.policy_id == test_policy.id).all()
        for advisory in advisories:
            result = await service.generate_test_cases(advisory.id)
            assert result.test_cases is not None

            # Check that the correct language was detected
            call_args = mock_llm.create_message.call_args
            prompt = call_args.kwargs["prompt"]
            detected_lang = service._detect_language(advisory.file_path)
            assert f"**Original Code ({detected_lang}):**" in prompt


@pytest.mark.asyncio
async def test_generate_test_cases_comprehensive_coverage(db_session: Session, test_advisory: CodeAdvisory):
    """Test that generated test cases cover multiple scenarios."""
    mock_llm = MagicMock()
    mock_llm.create_message = AsyncMock(
        return_value=json.dumps([
            {"name": "Authorized user", "scenario": "User has correct role", "setup": "Manager user", "input": {}, "expected_original": "true", "expected_refactored": "true", "assertion": "Allow"},
            {"name": "Unauthorized user", "scenario": "User lacks role", "setup": "Employee user", "input": {}, "expected_original": "false", "expected_refactored": "false", "assertion": "Deny"},
            {"name": "Boundary case - exact limit", "scenario": "Amount equals limit", "setup": "Amount = 5000", "input": {}, "expected_original": "false", "expected_refactored": "false", "assertion": "Deny at boundary"},
            {"name": "Edge case - just under limit", "scenario": "Amount just under", "setup": "Amount = 4999", "input": {}, "expected_original": "true", "expected_refactored": "true", "assertion": "Allow under limit"},
            {"name": "Edge case - just over limit", "scenario": "Amount just over", "setup": "Amount = 5001", "input": {}, "expected_original": "false", "expected_refactored": "false", "assertion": "Deny over limit"},
        ])
    )

    with patch("app.services.code_advisory_service.get_llm_provider", return_value=mock_llm):
        service = CodeAdvisoryService(db_session, "test-tenant")
        result = await service.generate_test_cases(test_advisory.id)

        test_cases = json.loads(result.test_cases)
        assert len(test_cases) >= 5  # Should have multiple test cases
        # Verify test cases cover different scenarios
        scenarios = [tc["scenario"] for tc in test_cases]
        assert any("correct role" in s.lower() for s in scenarios)
        assert any("lacks role" in s.lower() or "unauthorized" in s.lower() for s in scenarios)
