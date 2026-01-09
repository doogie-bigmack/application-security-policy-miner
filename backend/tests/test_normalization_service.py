"""Unit tests for normalization service."""
from unittest.mock import Mock, patch

import pytest

from app.models.role_mapping import MappingStatus
from app.services.normalization_service import NormalizationService


@pytest.fixture
def normalization_service():
    """Create normalization service instance."""
    return NormalizationService()


def test_extract_roles_from_subject(normalization_service):
    """Test role extraction from policy subjects."""
    # Test basic role name
    roles = normalization_service.extract_roles_from_subject("admin")
    assert "admin" in roles

    # Test role with quotes
    roles = normalization_service.extract_roles_from_subject("role: 'administrator'")
    assert "administrator" in roles

    # Test hasRole pattern
    roles = normalization_service.extract_roles_from_subject("hasRole('manager')")
    assert "manager" in roles

    # Test isRole pattern
    roles = normalization_service.extract_roles_from_subject("isAdmin")
    assert "admin" in roles

    # Test multiple roles
    roles = normalization_service.extract_roles_from_subject("admin or manager")
    assert "admin" in roles
    assert "manager" in roles


def test_are_similar_strings(normalization_service):
    """Test string similarity detection."""
    # Test exact match
    assert normalization_service._are_similar_strings("admin", "admin")

    # Test substring
    assert normalization_service._are_similar_strings("admin", "administrator")

    # Test common root
    assert normalization_service._are_similar_strings("admin", "sysadmin")

    # Test non-similar
    assert not normalization_service._are_similar_strings("admin", "viewer")


@pytest.mark.asyncio
async def test_analyze_role_equivalence_success(normalization_service):
    """Test role equivalence analysis with Claude."""
    roles = ["admin", "administrator", "sysadmin"]
    context = {
        "admin": ["App1", "App2"],
        "administrator": ["App3"],
        "sysadmin": ["App4"],
    }

    # Mock Anthropic API response
    mock_message = Mock()
    mock_message.content = [
        Mock(text="""EQUIVALENT: yes
STANDARD_ROLE: ADMIN
CONFIDENCE: 95
REASONING: These roles represent the same administrative privileges across different applications. They all grant full system access and management capabilities.""")
    ]

    with patch.object(normalization_service.client.messages, "create", return_value=mock_message):
        result = await normalization_service.analyze_role_equivalence(roles, context)

    assert result["equivalent"] is True
    assert result["standard_role"] == "ADMIN"
    assert result["confidence"] == 95
    assert "administrative" in result["reasoning"].lower()


@pytest.mark.asyncio
async def test_analyze_role_equivalence_not_equivalent(normalization_service):
    """Test role equivalence analysis when roles are not equivalent."""
    roles = ["admin", "viewer"]
    context = {
        "admin": ["App1"],
        "viewer": ["App2"],
    }

    mock_message = Mock()
    mock_message.content = [
        Mock(text="""EQUIVALENT: no
STANDARD_ROLE: ADMIN
CONFIDENCE: 10
REASONING: These roles are not equivalent. Admin has full permissions while viewer has read-only access.""")
    ]

    with patch.object(normalization_service.client.messages, "create", return_value=mock_message):
        result = await normalization_service.analyze_role_equivalence(roles, context)

    assert result["equivalent"] is False
    assert result["confidence"] == 10


@pytest.mark.asyncio
async def test_analyze_role_equivalence_error(normalization_service):
    """Test error handling in role equivalence analysis."""
    roles = ["admin", "administrator"]
    context = {"admin": ["App1"], "administrator": ["App2"]}

    with patch.object(
        normalization_service.client.messages,
        "create",
        side_effect=Exception("API Error"),
    ):
        result = await normalization_service.analyze_role_equivalence(roles, context)

    assert result["equivalent"] is False
    assert result["confidence"] == 0
    assert "Error during analysis" in result["reasoning"]


def test_group_similar_roles(normalization_service):
    """Test grouping of similar roles."""
    role_to_apps = {
        "admin": {1, 2},
        "administrator": {3, 4},
        "sysadmin": {5},
        "viewer": {6, 7},
        "reader": {8},
    }
    app_id_to_name = {
        1: "App1",
        2: "App2",
        3: "App3",
        4: "App4",
        5: "App5",
        6: "App6",
        7: "App7",
        8: "App8",
    }

    groups = normalization_service._group_similar_roles(role_to_apps, app_id_to_name, min_applications=2)

    # Should find admin group and viewer group
    assert len(groups) >= 2

    # Check admin group
    admin_group = next((g for g in groups if "admin" in g["roles"]), None)
    assert admin_group is not None
    assert "administrator" in admin_group["roles"] or "sysadmin" in admin_group["roles"]


@pytest.mark.asyncio
async def test_create_role_mapping(normalization_service):
    """Test creating a role mapping."""
    mock_db = Mock()
    mock_db.query.return_value.filter.return_value.scalar.return_value = 10

    await normalization_service.create_role_mapping(
        db=mock_db,
        tenant_id="tenant1",
        standard_role="ADMIN",
        variant_roles=["admin", "administrator"],
        affected_applications=[1, 2, 3],
        confidence_score=90,
        reasoning="Test reasoning",
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_apply_role_mapping_success(normalization_service):
    """Test applying a role mapping to policies."""
    # Mock database
    mock_db = Mock()

    # Mock role mapping
    mock_mapping = Mock()
    mock_mapping.id = 1
    mock_mapping.tenant_id = "tenant1"
    mock_mapping.standard_role = "ADMIN"
    mock_mapping.variant_roles = ["admin", "administrator"]
    mock_mapping.affected_applications = [1, 2]
    mock_mapping.status = MappingStatus.SUGGESTED

    mock_db.query.return_value.filter.return_value.first.return_value = mock_mapping

    # Mock policies
    mock_policy1 = Mock()
    mock_policy1.subject = "User with role 'admin'"
    mock_policy2 = Mock()
    mock_policy2.subject = "User with role 'administrator'"

    mock_db.query.return_value.filter.return_value.all.return_value = [mock_policy1, mock_policy2]

    updated_count = await normalization_service.apply_role_mapping(
        db=mock_db,
        mapping_id=1,
        approved_by="test@example.com",
    )

    assert updated_count == 2
    assert mock_mapping.status == MappingStatus.APPLIED
    assert mock_mapping.approved_by == "test@example.com"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_apply_role_mapping_not_found(normalization_service):
    """Test error when applying non-existent mapping."""
    mock_db = Mock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(ValueError, match="Role mapping .* not found"):
        await normalization_service.apply_role_mapping(
            db=mock_db,
            mapping_id=999,
            approved_by="test@example.com",
        )


@pytest.mark.asyncio
async def test_apply_role_mapping_wrong_status(normalization_service):
    """Test error when applying mapping with wrong status."""
    mock_db = Mock()

    mock_mapping = Mock()
    mock_mapping.id = 1
    mock_mapping.status = MappingStatus.APPLIED

    mock_db.query.return_value.filter.return_value.first.return_value = mock_mapping

    with pytest.raises(ValueError, match="Mapping must be in SUGGESTED status"):
        await normalization_service.apply_role_mapping(
            db=mock_db,
            mapping_id=1,
            approved_by="test@example.com",
        )
