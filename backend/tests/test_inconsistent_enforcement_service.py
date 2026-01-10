"""Tests for InconsistentEnforcementService."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.models.application import Application
from app.models.inconsistent_enforcement import (
    InconsistentEnforcement,
    InconsistentEnforcementSeverity,
    InconsistentEnforcementStatus,
)
from app.models.policy import Policy
from app.services.inconsistent_enforcement_service import InconsistentEnforcementService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.generate = AsyncMock()
    return provider


@pytest.fixture
def service(mock_db, mock_llm_provider):
    """Create service instance."""
    with patch("app.services.inconsistent_enforcement_service.get_llm_provider", return_value=mock_llm_provider):
        service = InconsistentEnforcementService(mock_db, tenant_id="test-tenant")
        service.llm_provider = mock_llm_provider
        return service


def test_normalize_resource_name(service):
    """Test resource name normalization."""
    assert service._normalize_resource_name("Customer Data") == "customer_pii"
    assert service._normalize_resource_name("CUSTOMER INFO") == "customer_pii"
    assert service._normalize_resource_name("Personal Information") == "customer_pii"
    assert service._normalize_resource_name("Financial Data") == "financial_data"
    assert service._normalize_resource_name("Payment Information") == "financial_data"
    assert service._normalize_resource_name("Custom Resource") == "custom resource"


def test_group_policies_by_resource_empty(service, mock_db):
    """Test grouping with no policies."""
    mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = []

    result = service._group_policies_by_resource()

    assert result == {}


def test_group_policies_by_resource_single_app(service, mock_db):
    """Test grouping with policies from single app."""
    policy1 = Mock(spec=Policy)
    policy1.resource = "Customer Data"
    policy1.application_id = 1

    policy2 = Mock(spec=Policy)
    policy2.resource = "customer info"
    policy2.application_id = 1

    mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [policy1, policy2]

    result = service._group_policies_by_resource()

    assert "customer_pii" in result
    assert len(result["customer_pii"]["policies"]) == 2
    assert result["customer_pii"]["application_ids"] == [1]


def test_group_policies_by_resource_multiple_apps(service, mock_db):
    """Test grouping with policies from multiple apps."""
    policy1 = Mock(spec=Policy)
    policy1.resource = "Customer Data"
    policy1.application_id = 1

    policy2 = Mock(spec=Policy)
    policy2.resource = "customer info"
    policy2.application_id = 2

    policy3 = Mock(spec=Policy)
    policy3.resource = "Personal Information"
    policy3.application_id = 3

    mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
        policy1,
        policy2,
        policy3,
    ]

    result = service._group_policies_by_resource()

    assert "customer_pii" in result
    assert len(result["customer_pii"]["policies"]) == 3
    assert set(result["customer_pii"]["application_ids"]) == {1, 2, 3}


def test_extract_json_from_response_with_markdown(service):
    """Test JSON extraction from markdown code blocks."""
    response = """Here is the analysis:
    ```json
    {"is_inconsistent": true, "severity": "high"}
    ```
    """

    result = service._extract_json_from_response(response)

    assert result == {"is_inconsistent": True, "severity": "high"}


def test_extract_json_from_response_plain(service):
    """Test JSON extraction from plain response."""
    response = '{"is_inconsistent": false, "severity": "low"}'

    result = service._extract_json_from_response(response)

    assert result == {"is_inconsistent": False, "severity": "low"}


def test_extract_json_from_response_invalid(service):
    """Test JSON extraction with invalid JSON."""
    response = "Not valid JSON at all"

    result = service._extract_json_from_response(response)

    assert result == {}


def test_parse_severity(service):
    """Test severity parsing."""
    assert service._parse_severity("low") == InconsistentEnforcementSeverity.LOW
    assert service._parse_severity("MEDIUM") == InconsistentEnforcementSeverity.MEDIUM
    assert service._parse_severity("high") == InconsistentEnforcementSeverity.HIGH
    assert service._parse_severity("critical") == InconsistentEnforcementSeverity.CRITICAL
    assert service._parse_severity("unknown") == InconsistentEnforcementSeverity.MEDIUM  # default


@pytest.mark.asyncio
async def test_analyze_policy_consistency_no_inconsistency(service, mock_db, mock_llm_provider):
    """Test AI analysis when policies are consistent."""
    mock_llm_provider.generate.return_value = json.dumps({"is_inconsistent": False})

    policy1 = Mock(spec=Policy)
    policy1.id = 1
    policy1.subject = "ADMIN"
    policy1.resource = "Customer Data"
    policy1.action = "read"
    policy1.conditions = None
    policy1.status = Mock(value="approved")
    policy1.application_id = 1

    app1 = Mock(spec=Application)
    app1.name = "App1"

    mock_db.query.return_value.filter.return_value.first.return_value = app1

    result = await service._analyze_policy_consistency("customer_pii", [policy1], [1])

    assert result is None


@pytest.mark.asyncio
async def test_analyze_policy_consistency_with_inconsistency(service, mock_db, mock_llm_provider):
    """Test AI analysis when policies are inconsistent."""
    ai_response = {
        "is_inconsistent": True,
        "severity": "high",
        "description": "App1 requires ADMIN, App2 requires MANAGER, App3 has no check",
        "recommended_policy": {
            "subject": "ADMIN",
            "resource": "customer_pii",
            "action": "read",
            "conditions": None,
        },
        "explanation": "Standardize to ADMIN role for consistency",
    }
    mock_llm_provider.generate.return_value = json.dumps(ai_response)

    policy1 = Mock(spec=Policy)
    policy1.id = 1
    policy1.subject = "ADMIN"
    policy1.resource = "Customer Data"
    policy1.action = "read"
    policy1.conditions = None
    policy1.status = Mock(value="approved")
    policy1.application_id = 1

    policy2 = Mock(spec=Policy)
    policy2.id = 2
    policy2.subject = "MANAGER"
    policy2.resource = "customer info"
    policy2.action = "read"
    policy2.conditions = None
    policy2.status = Mock(value="approved")
    policy2.application_id = 2

    app1 = Mock(spec=Application)
    app1.name = "App1"
    app2 = Mock(spec=Application)
    app2.name = "App2"

    def mock_query_filter(model):
        if model == Application:
            mock_query = MagicMock()
            mock_query.filter.return_value.first.side_effect = [app1, app2]
            return mock_query
        return MagicMock()

    mock_db.query.side_effect = mock_query_filter

    result = await service._analyze_policy_consistency("customer_pii", [policy1, policy2], [1, 2])

    assert result is not None
    assert isinstance(result, InconsistentEnforcement)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_detect_inconsistencies_no_policies(service, mock_db):
    """Test detection with no policies."""
    mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = []

    result = await service.detect_inconsistencies()

    assert result == []


def test_get_all_inconsistencies(service, mock_db):
    """Test getting all inconsistencies."""
    inc1 = Mock(spec=InconsistentEnforcement)
    inc2 = Mock(spec=InconsistentEnforcement)

    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [inc1, inc2]
    mock_db.query.return_value = mock_query

    result = service.get_all_inconsistencies()

    assert len(result) == 2
    assert result == [inc1, inc2]


def test_get_all_inconsistencies_with_filters(service, mock_db):
    """Test getting inconsistencies with status and severity filters."""
    inc1 = Mock(spec=InconsistentEnforcement)

    mock_query = MagicMock()
    mock_query.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
        inc1
    ]
    mock_db.query.return_value = mock_query

    result = service.get_all_inconsistencies(
        status=InconsistentEnforcementStatus.PENDING, severity=InconsistentEnforcementSeverity.HIGH
    )

    assert len(result) == 1


def test_get_inconsistency(service, mock_db):
    """Test getting a specific inconsistency."""
    inc = Mock(spec=InconsistentEnforcement)

    mock_db.query.return_value.filter.return_value.first.return_value = inc

    result = service.get_inconsistency(1)

    assert result == inc


def test_update_status(service, mock_db):
    """Test updating inconsistency status."""
    inc = Mock(spec=InconsistentEnforcement)
    inc.status = InconsistentEnforcementStatus.PENDING

    mock_db.query.return_value.filter.return_value.first.return_value = inc

    result = service.update_status(
        inconsistency_id=1,
        status=InconsistentEnforcementStatus.RESOLVED,
        resolution_notes="Fixed by standardizing to ADMIN role",
        resolved_by="admin@example.com",
    )

    assert result == inc
    assert inc.status == InconsistentEnforcementStatus.RESOLVED
    assert inc.resolution_notes == "Fixed by standardizing to ADMIN role"
    assert inc.resolved_by == "admin@example.com"
    assert inc.resolved_at is not None
    mock_db.commit.assert_called_once()


def test_delete_inconsistency(service, mock_db):
    """Test deleting an inconsistency."""
    inc = Mock(spec=InconsistentEnforcement)

    mock_db.query.return_value.filter.return_value.first.return_value = inc

    result = service.delete_inconsistency(1)

    assert result is True
    mock_db.delete.assert_called_once_with(inc)
    mock_db.commit.assert_called_once()


def test_delete_inconsistency_not_found(service, mock_db):
    """Test deleting non-existent inconsistency."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = service.delete_inconsistency(999)

    assert result is False
    mock_db.delete.assert_not_called()
