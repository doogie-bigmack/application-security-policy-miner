"""Unit tests for always-true condition detection in policy fixing service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.policy import Evidence, Policy
from app.services.policy_fixing_service import PolicyFixingService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def policy_fixing_service(mock_db):
    """Create PolicyFixingService instance."""
    return PolicyFixingService(db=mock_db, tenant_id="test-tenant")


def test_detect_always_true_with_boolean_or(policy_fixing_service):
    """Test detection of 'true || condition' pattern."""
    policy = Mock(spec=Policy)
    policy.conditions = "true || user.hasRole('ADMIN')"
    policy.evidence = []

    result = policy_fixing_service._detect_always_true_conditions(policy)

    assert "Boolean literal with OR operator" in result
    assert "⚠️ ALERT" in result


def test_detect_always_true_with_redundant_comparison(policy_fixing_service):
    """Test detection of '1 == 1' pattern."""
    policy = Mock(spec=Policy)
    policy.conditions = "1 == 1 && user.isActive()"
    policy.evidence = []

    result = policy_fixing_service._detect_always_true_conditions(policy)

    assert "Redundant comparison detected" in result
    assert "⚠️ ALERT" in result


def test_detect_always_true_in_evidence_code(policy_fixing_service):
    """Test detection of always-true conditions in evidence code."""
    evidence = Mock(spec=Evidence)
    evidence.file_path = "/app/auth.py"
    evidence.line_start = 42
    evidence.code_snippet = """
    if (true || user.hasRole('ADMIN')) {
        return true;
    }
    """

    policy = Mock(spec=Policy)
    policy.conditions = "Check user authorization"
    policy.evidence = [evidence]

    result = policy_fixing_service._detect_always_true_conditions(policy)

    assert "Boolean literal with OR" in result
    assert "/app/auth.py:42" in result


def test_detect_if_true_statement(policy_fixing_service):
    """Test detection of 'if (true)' statement."""
    evidence = Mock(spec=Evidence)
    evidence.file_path = "/app/controller.py"
    evidence.line_start = 100
    evidence.code_snippet = "if (true) { allow_access(); }"

    policy = Mock(spec=Policy)
    policy.conditions = None
    policy.evidence = [evidence]

    result = policy_fixing_service._detect_always_true_conditions(policy)

    assert "Always-true condition" in result
    assert "/app/controller.py:100" in result


def test_no_always_true_conditions(policy_fixing_service):
    """Test that valid conditions don't trigger false positives."""
    evidence = Mock(spec=Evidence)
    evidence.file_path = "/app/auth.py"
    evidence.line_start = 50
    evidence.code_snippet = "if (user.hasRole('ADMIN') && user.isActive()) { return true; }"

    policy = Mock(spec=Policy)
    policy.conditions = "user.role == 'ADMIN' && user.status == 'active'"
    policy.evidence = [evidence]

    result = policy_fixing_service._detect_always_true_conditions(policy)

    assert result == ""


def test_detect_multiple_patterns(policy_fixing_service):
    """Test detection of multiple always-true patterns."""
    evidence = Mock(spec=Evidence)
    evidence.file_path = "/app/security.py"
    evidence.line_start = 25
    evidence.code_snippet = "if (true || checkPermission()) { return true; }"

    policy = Mock(spec=Policy)
    policy.conditions = "1 == 1 || user.hasAccess()"
    policy.evidence = [evidence]

    result = policy_fixing_service._detect_always_true_conditions(policy)

    assert "Redundant comparison" in result
    assert "Boolean literal with OR" in result


def test_case_insensitive_detection(policy_fixing_service):
    """Test that detection is case-insensitive."""
    policy = Mock(spec=Policy)
    policy.conditions = "TRUE || user.hasRole('ADMIN')"
    policy.evidence = []

    result = policy_fixing_service._detect_always_true_conditions(policy)

    assert "Boolean literal with OR" in result


@pytest.mark.asyncio
async def test_analyze_policy_with_always_true_ai_response(mock_db):
    """Test AI analysis correctly identifies always-true conditions."""
    # Create mock policy with always-true condition
    policy = Mock(spec=Policy)
    policy.id = 1
    policy.subject = "Any User"
    policy.resource = "Admin Panel"
    policy.action = "access"
    policy.conditions = "true || user.hasRole('ADMIN')"
    policy.description = "Admin panel access"
    policy.evidence = []
    policy.risk_level = Mock()
    policy.risk_level.value = "high"

    # Mock LLM response
    mock_llm_response = """
    {
        "has_gaps": true,
        "gap_type": "always_true",
        "severity": "critical",
        "gap_description": "The condition 'true || user.hasRole('ADMIN')' is always true due to boolean literal in OR expression. This makes the role check meaningless and allows any user to access the admin panel.",
        "missing_checks": [
            "Remove 'true ||' to make role check meaningful",
            "Ensure only ADMIN role can access"
        ],
        "fixed_policy": {
            "subject": "Admin User",
            "resource": "Admin Panel",
            "action": "access",
            "conditions": "user.hasRole('ADMIN') && user.status == 'active'"
        },
        "fix_explanation": "The original condition 'true || user.hasRole('ADMIN')' always evaluates to true because of the OR operator with a boolean literal. This bypasses the role check entirely. The fix removes the always-true condition and adds an additional active status check."
    }
    """

    # Mock LLM provider
    with patch("app.services.policy_fixing_service.get_llm_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.create_message = AsyncMock(return_value=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        # Create service
        service = PolicyFixingService(db=mock_db, tenant_id="test-tenant")

        # Test the AI analysis method directly (avoids SQLAlchemy model instantiation)
        result = await service._analyze_policy_with_ai(policy)

        # Verify the AI correctly identified always_true gap
        assert result["has_gaps"] is True
        assert result["gap_type"] == "always_true"
        assert result["severity"] == "critical"
        assert "true ||" in result["gap_description"]


@pytest.mark.asyncio
async def test_always_true_detection_in_prompt(mock_db):
    """Test that always-true detection results are included in AI prompt."""
    evidence = Mock(spec=Evidence)
    evidence.file_path = "/app/auth.py"
    evidence.line_start = 42
    evidence.code_snippet = "if (true || hasPermission()) { return true; }"

    policy = Mock(spec=Policy)
    policy.id = 1
    policy.subject = "User"
    policy.resource = "Resource"
    policy.action = "access"
    policy.conditions = "true || checkAccess()"
    policy.description = "Access control"
    policy.evidence = [evidence]

    mock_llm_response = '{"has_gaps": false}'

    with patch("app.services.policy_fixing_service.get_llm_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.create_message = AsyncMock(return_value=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        service = PolicyFixingService(db=mock_db, tenant_id="test-tenant")
        mock_db.query.return_value.filter.return_value.first.return_value = policy

        await service._analyze_policy_with_ai(policy)

        # Verify the prompt included always-true detection
        call_args = mock_provider.create_message.call_args
        prompt = call_args.kwargs["prompt"]

        assert "⚠️ ALERT" in prompt
        assert "Boolean literal with OR" in prompt
        assert "/app/auth.py:42" in prompt
