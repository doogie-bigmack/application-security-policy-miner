"""Unit tests for conflict detection service."""
import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.conflict import ConflictType
from app.models.policy import Policy, PolicyStatus, SourceType
from app.models.repository import Base
from app.services.conflict_detection import ConflictDetectionService


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine)
    session = testing_session_local()
    yield session
    session.close()


@pytest.fixture
def service(db_session):
    """Create a conflict detection service."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "test-key")
    return ConflictDetectionService(db_session, api_key)


def test_policies_might_conflict_resource_overlap(service, db_session):
    """Test that policies with overlapping resources are flagged."""
    policy_a = Policy(
        repository_id=1,
        subject="Manager",
        resource="Expense Report",
        action="approve",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )
    policy_b = Policy(
        repository_id=1,
        subject="Admin",
        resource="Expense",
        action="reject",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )

    # Should detect resource overlap
    assert service._policies_might_conflict(policy_a, policy_b) is True


def test_policies_might_conflict_subject_overlap(service, db_session):
    """Test that policies with overlapping subjects are flagged."""
    policy_a = Policy(
        repository_id=1,
        subject="Manager",
        resource="Document",
        action="approve",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )
    policy_b = Policy(
        repository_id=1,
        subject="Senior Manager",
        resource="Invoice",
        action="reject",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )

    # Should detect subject overlap
    assert service._policies_might_conflict(policy_a, policy_b) is True


def test_policies_might_conflict_no_overlap(service, db_session):
    """Test that policies with no overlap are not flagged."""
    policy_a = Policy(
        repository_id=1,
        subject="Manager",
        resource="Expense Report",
        action="approve",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )
    policy_b = Policy(
        repository_id=1,
        subject="Developer",
        resource="Code Review",
        action="merge",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )

    # Should not detect conflict
    assert service._policies_might_conflict(policy_a, policy_b) is False


def test_parse_ai_response_valid_json(service):
    """Test parsing a valid AI response."""
    response = """Here is the analysis:
    {
      "has_conflict": true,
      "conflict_type": "contradictory",
      "severity": "high",
      "description": "These policies contradict each other",
      "recommendation": "Keep policy A"
    }
    """

    result = service._parse_ai_response(response)

    assert result["has_conflict"] is True
    assert result["conflict_type"] == "contradictory"
    assert result["severity"] == "high"
    assert "contradict" in result["description"]


def test_parse_ai_response_no_conflict(service):
    """Test parsing an AI response with no conflict."""
    response = """
    {
      "has_conflict": false,
      "conflict_type": null,
      "severity": "low",
      "description": "No conflict detected",
      "recommendation": "No action needed"
    }
    """

    result = service._parse_ai_response(response)

    assert result["has_conflict"] is False


def test_parse_ai_response_invalid_json(service):
    """Test parsing an invalid AI response."""
    response = "This is not JSON"

    result = service._parse_ai_response(response)

    assert result["has_conflict"] is False


@patch("app.services.conflict_detection.Anthropic")
def test_analyze_conflict_detects_conflict(mock_anthropic, db_session):
    """Test that analyze_conflict detects a real conflict."""
    # Mock the Anthropic API response
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text='{"has_conflict": true, "conflict_type": "contradictory", "severity": "high", "description": "Contradictory rules", "recommendation": "Merge policies"}'
        )
    ]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Create service with mock
    service = ConflictDetectionService(db_session, "test-key")

    # Create test policies
    policy_a = Policy(
        id=1,
        repository_id=1,
        subject="Manager",
        resource="Expense Report",
        action="approve",
        conditions="amount < 5000",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )
    policy_b = Policy(
        id=2,
        repository_id=1,
        subject="Manager",
        resource="Expense Report",
        action="reject",
        conditions="amount > 1000",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )

    db_session.add(policy_a)
    db_session.add(policy_b)
    db_session.commit()

    conflict = service._analyze_conflict(policy_a, policy_b)

    assert conflict is not None
    assert conflict.conflict_type == ConflictType.CONTRADICTORY
    assert conflict.severity == "high"
    assert conflict.description == "Contradictory rules"
    assert conflict.ai_recommendation == "Merge policies"


@patch("app.services.conflict_detection.Anthropic")
def test_analyze_conflict_no_conflict(mock_anthropic, db_session):
    """Test that analyze_conflict returns None when there is no conflict."""
    # Mock the Anthropic API response
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text='{"has_conflict": false, "conflict_type": null, "severity": "low", "description": "No conflict", "recommendation": "No action"}'
        )
    ]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Create service with mock
    service = ConflictDetectionService(db_session, "test-key")

    policy_a = Policy(
        id=1,
        repository_id=1,
        subject="Manager",
        resource="Expense Report",
        action="approve",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )
    policy_b = Policy(
        id=2,
        repository_id=1,
        subject="Admin",
        resource="User Account",
        action="delete",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )

    db_session.add(policy_a)
    db_session.add(policy_b)
    db_session.commit()

    conflict = service._analyze_conflict(policy_a, policy_b)

    assert conflict is None


def test_detect_conflicts_no_policies(service, db_session):
    """Test conflict detection with no policies."""
    conflicts = service.detect_conflicts()
    assert len(conflicts) == 0


def test_detect_conflicts_single_policy(service, db_session):
    """Test conflict detection with only one policy."""
    policy = Policy(
        repository_id=1,
        subject="Manager",
        resource="Expense Report",
        action="approve",
        status=PolicyStatus.PENDING,
        source_type=SourceType.BACKEND,
    )
    db_session.add(policy)
    db_session.commit()

    conflicts = service.detect_conflicts()
    assert len(conflicts) == 0
