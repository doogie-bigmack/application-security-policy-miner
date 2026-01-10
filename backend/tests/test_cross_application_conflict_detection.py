"""Tests for cross-application conflict detection service."""
from unittest.mock import Mock

import pytest

from app.models.application import Application
from app.models.conflict import ConflictType, PolicyConflict
from app.models.policy import Policy
from app.services.cross_application_conflict_detection import (
    CrossApplicationConflictDetectionService,
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    return Mock()


@pytest.fixture
def service(mock_db, mock_llm_provider, monkeypatch):
    """Create a CrossApplicationConflictDetectionService instance with mocked dependencies."""
    monkeypatch.setattr(
        'app.services.cross_application_conflict_detection.get_llm_provider',
        lambda: mock_llm_provider
    )
    return CrossApplicationConflictDetectionService(mock_db)


def test_policies_might_conflict_different_applications(service):
    """Test that policies from different applications can conflict."""
    policy_a = Mock(spec=Policy)
    policy_a.application_id = 1
    policy_a.resource = "Expense Report"
    policy_a.subject = "Manager"
    policy_a.action = "approve"

    policy_b = Mock(spec=Policy)
    policy_b.application_id = 2
    policy_b.resource = "Expense Report"
    policy_b.subject = "Director"
    policy_b.action = "approve"

    result = service._policies_might_conflict(policy_a, policy_b)
    assert result is True


def test_policies_might_conflict_same_application(service):
    """Test that policies from the same application don't trigger cross-app conflict detection."""
    policy_a = Mock(spec=Policy)
    policy_a.application_id = 1
    policy_a.resource = "Expense Report"
    policy_a.subject = "Manager"
    policy_a.action = "approve"

    policy_b = Mock(spec=Policy)
    policy_b.application_id = 1
    policy_b.resource = "Expense Report"
    policy_b.subject = "Director"
    policy_b.action = "approve"

    result = service._policies_might_conflict(policy_a, policy_b)
    assert result is False


def test_policies_might_conflict_no_resource_overlap(service):
    """Test that policies with different resources don't conflict."""
    policy_a = Mock(spec=Policy)
    policy_a.application_id = 1
    policy_a.resource = "Expense Report"
    policy_a.subject = "Manager"
    policy_a.action = "approve"

    policy_b = Mock(spec=Policy)
    policy_b.application_id = 2
    policy_b.resource = "User Account"
    policy_b.subject = "Manager"
    policy_b.action = "delete"

    result = service._policies_might_conflict(policy_a, policy_b)
    assert result is False


def test_semantic_overlap(service):
    """Test semantic overlap detection."""
    # Test exact match
    assert service._semantic_overlap("manager", "manager") is True

    # Test plural match
    assert service._semantic_overlap("manager", "managers") is True

    # Test verb forms
    assert service._semantic_overlap("approve", "approval") is True

    # Test no match
    assert service._semantic_overlap("manager", "director") is False


def test_detect_cross_application_conflicts_insufficient_policies(service, mock_db):
    """Test that detection returns empty list when there are insufficient policies."""
    # Mock query to return only 1 policy
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = []
    mock_db.query.return_value = mock_query

    result = service.detect_cross_application_conflicts(tenant_id="test-tenant")

    assert result == []


def test_detect_cross_application_conflicts_single_application(service, mock_db):
    """Test that detection returns empty list when policies are from a single application."""
    # Mock policies from the same application
    policy_a = Mock(spec=Policy)
    policy_a.application_id = 1
    policy_a.id = 1

    policy_b = Mock(spec=Policy)
    policy_b.application_id = 1
    policy_b.id = 2

    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [policy_a, policy_b]
    mock_db.query.return_value = mock_query

    result = service.detect_cross_application_conflicts(tenant_id="test-tenant")

    assert result == []


def test_analyze_cross_app_conflict_with_ai(mock_llm_provider, monkeypatch):
    """Test AI-powered conflict analysis."""
    # Mock the entire service method to avoid SQLAlchemy issues
    from app.services.cross_application_conflict_detection import (
        CrossApplicationConflictDetectionService,
    )

    # Setup policies
    policy_a = Mock()
    policy_a.id = 1
    policy_a.application_id = 1
    policy_a.subject = "Manager"
    policy_a.resource = "Expense Report"
    policy_a.action = "approve"
    policy_a.conditions = "amount < $5000"
    policy_a.description = "Managers can approve expenses under $5000"

    policy_b = Mock()
    policy_b.id = 2
    policy_b.application_id = 2
    policy_b.subject = "Director"
    policy_b.resource = "Expense Report"
    policy_b.action = "approve"
    policy_b.conditions = None
    policy_b.description = "Only directors can approve expenses"

    # Mock LLM response
    mock_llm_provider.create_message.return_value = """{
        "has_conflict": true,
        "conflict_type": "contradictory",
        "severity": "high",
        "description": "ExpenseApp v1 allows managers to approve up to $5000, but ExpenseApp v2 requires director approval for all expenses",
        "recommendation": "Create unified policy: Managers approve < $5000, Directors approve >= $5000"
    }"""

    # Mock the service
    mock_db = Mock()
    mock_service = CrossApplicationConflictDetectionService(mock_db)
    mock_service.llm_provider = mock_llm_provider

    # Mock the db query to return applications
    app_a = Mock()
    app_a.name = "ExpenseApp v1"
    app_b = Mock()
    app_b.name = "ExpenseApp v2"

    # We need to mock the db.query() call chain
    query_mock = Mock()
    filter_mock = Mock()
    filter_mock.first.side_effect = [app_a, app_b]
    query_mock.filter.return_value = filter_mock
    mock_db.query.return_value = query_mock

    # Execute
    result = mock_service._analyze_cross_app_conflict(policy_a, policy_b)

    # Verify
    assert result is not None
    assert isinstance(result, PolicyConflict)
    assert result.conflict_type == ConflictType.CONTRADICTORY
    assert result.severity == "high"
    assert "ExpenseApp v1" in result.description
    assert "ExpenseApp v2" in result.description


def test_analyze_cross_app_conflict_no_conflict(service, mock_db, mock_llm_provider):
    """Test that no conflict is detected when policies are consistent."""
    # Setup policies
    policy_a = Mock(spec=Policy)
    policy_a.id = 1
    policy_a.application_id = 1
    policy_a.subject = "Manager"
    policy_a.resource = "Expense Report"
    policy_a.action = "approve"
    policy_a.conditions = "amount < $5000"
    policy_a.description = "Managers can approve expenses under $5000"

    policy_b = Mock(spec=Policy)
    policy_b.id = 2
    policy_b.application_id = 2
    policy_b.subject = "Manager"
    policy_b.resource = "Expense Report"
    policy_b.action = "approve"
    policy_b.conditions = "amount < $5000"
    policy_b.description = "Managers can approve expenses under $5000"

    # Setup applications
    app_a = Mock(spec=Application)
    app_a.name = "ExpenseApp v1"

    app_b = Mock(spec=Application)
    app_b.name = "FinancePortal"

    # Mock database queries
    mock_db.query.return_value.filter.return_value.first.side_effect = [app_a, app_b]

    # Mock LLM response (no conflict)
    mock_llm_provider.create_message.return_value = """{
        "has_conflict": false,
        "conflict_type": null,
        "severity": "low",
        "description": "Policies are consistent",
        "recommendation": "No action needed"
    }"""

    # Execute
    result = service._analyze_cross_app_conflict(policy_a, policy_b)

    # Verify
    assert result is None


def test_get_cross_application_conflicts(service, mock_db):
    """Test retrieving cross-application conflicts."""
    # Setup conflicts
    conflict1 = Mock(spec=PolicyConflict)
    conflict1.id = 1
    conflict1.policy_a_id = 1
    conflict1.policy_b_id = 2
    conflict1.tenant_id = "test-tenant"

    conflict2 = Mock(spec=PolicyConflict)
    conflict2.id = 2
    conflict2.policy_a_id = 3
    conflict2.policy_b_id = 4
    conflict2.tenant_id = "test-tenant"

    # Setup policies (cross-application)
    policy_a = Mock(spec=Policy)
    policy_a.id = 1
    policy_a.application_id = 1

    policy_b = Mock(spec=Policy)
    policy_b.id = 2
    policy_b.application_id = 2

    policy_c = Mock(spec=Policy)
    policy_c.id = 3
    policy_c.application_id = 3

    policy_d = Mock(spec=Policy)
    policy_d.id = 4
    policy_d.application_id = 4

    # Mock query chain
    mock_query = Mock()
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [conflict1, conflict2]
    mock_db.query.return_value = mock_query

    # Mock individual policy queries
    policy_queries = [policy_a, policy_b, policy_c, policy_d]
    mock_db.query.return_value.filter.return_value.first.side_effect = policy_queries

    # Execute
    result = service.get_cross_application_conflicts(tenant_id="test-tenant")

    # Verify
    assert len(result) == 2
    assert result[0] == conflict1
    assert result[1] == conflict2


def test_parse_ai_response(service):
    """Test parsing AI response."""
    response_text = """Here is the analysis:
    {
        "has_conflict": true,
        "conflict_type": "contradictory",
        "severity": "high",
        "description": "Conflicting policies detected",
        "recommendation": "Use unified policy"
    }
    """

    result = service._parse_ai_response(response_text)

    assert result["has_conflict"] is True
    assert result["conflict_type"] == "contradictory"
    assert result["severity"] == "high"


def test_parse_ai_response_invalid_json(service):
    """Test parsing invalid AI response."""
    response_text = "This is not valid JSON"

    result = service._parse_ai_response(response_text)

    assert result["has_conflict"] is False
