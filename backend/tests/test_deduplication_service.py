"""Tests for deduplication service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.duplicate_policy_group import (
    DuplicateGroupStatus,
    DuplicatePolicyGroup,
    DuplicatePolicyGroupMember,
)
from app.models.policy import Policy
from app.services.deduplication_service import DeduplicationService


@pytest.fixture
def deduplication_service():
    """Create deduplication service instance."""
    return DeduplicationService()


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def sample_policies():
    """Create sample policies for testing."""
    policies = []
    for i in range(5):
        policy = Mock(spec=Policy)
        policy.id = i + 1
        policy.subject = "Manager"
        policy.resource = "Expense Report"
        policy.action = "approve"
        policy.conditions = f"amount < ${(i + 1) * 1000}"
        policy.tenant_id = "test-tenant"
        policy.embedding = [0.1] * 1536  # Mock embedding
        policies.append(policy)
    return policies


@pytest.mark.asyncio
async def test_detect_duplicates_no_policies(deduplication_service, mock_db):
    """Test duplicate detection when no policies exist."""
    # Mock query result with no policies
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    groups = await deduplication_service.detect_duplicates(
        db=mock_db,
        tenant_id="test-tenant",
    )

    assert groups == []


@pytest.mark.asyncio
async def test_detect_duplicates_single_policy(deduplication_service, mock_db, sample_policies):
    """Test duplicate detection with a single policy."""
    # Mock query result with one policy
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = [sample_policies[0]]
    mock_db.execute.return_value = mock_result

    # Mock similarity service to return no similar policies
    deduplication_service.similarity_service.find_similar_policies = AsyncMock(return_value=[])

    groups = await deduplication_service.detect_duplicates(
        db=mock_db,
        tenant_id="test-tenant",
    )

    assert groups == []


@pytest.mark.asyncio
async def test_detect_duplicates_with_similar_policies(deduplication_service, mock_db, sample_policies):
    """Test duplicate detection with similar policies."""
    # Mock query result with policies
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = sample_policies[:3]
    mock_db.execute.return_value = mock_result

    # Mock similarity service to return similar policies
    similar_policies = [
        (sample_policies[1], 0.95),
        (sample_policies[2], 0.92),
    ]
    deduplication_service.similarity_service.find_similar_policies = AsyncMock(
        return_value=similar_policies
    )

    # Mock database operations
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = Mock()

    groups = await deduplication_service.detect_duplicates(
        db=mock_db,
        min_similarity=0.9,
        tenant_id="test-tenant",
    )

    # Should create one duplicate group
    assert len(groups) == 1
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_consolidate_duplicates_success(deduplication_service, mock_db):
    """Test successful duplicate consolidation."""
    # Mock group
    group = Mock(spec=DuplicatePolicyGroup)
    group.id = 1
    group.status = DuplicateGroupStatus.DETECTED

    # Mock member
    member = Mock(spec=DuplicatePolicyGroupMember)
    member.group_id = 1
    member.policy_id = 10

    # Mock database queries
    group_result = Mock()
    group_result.scalar_one_or_none.return_value = group
    member_result = Mock()
    member_result.scalar_one_or_none.return_value = member

    mock_db.execute.side_effect = [group_result, member_result]
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await deduplication_service.consolidate_duplicates(
        db=mock_db,
        group_id=1,
        consolidated_policy_id=10,
        notes="Test consolidation",
    )

    assert result == group
    assert group.status == DuplicateGroupStatus.CONSOLIDATED
    assert group.consolidated_policy_id == 10
    assert group.consolidation_notes == "Test consolidation"
    assert group.consolidated_at is not None


@pytest.mark.asyncio
async def test_consolidate_duplicates_group_not_found(deduplication_service, mock_db):
    """Test consolidation when group not found."""
    # Mock database query returning None
    result = Mock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result

    with pytest.raises(ValueError, match="Duplicate group .* not found"):
        await deduplication_service.consolidate_duplicates(
            db=mock_db,
            group_id=999,
            consolidated_policy_id=10,
        )


@pytest.mark.asyncio
async def test_consolidate_duplicates_policy_not_in_group(deduplication_service, mock_db):
    """Test consolidation when policy not in group."""
    # Mock group exists
    group = Mock(spec=DuplicatePolicyGroup)
    group_result = Mock()
    group_result.scalar_one_or_none.return_value = group

    # Mock member does not exist
    member_result = Mock()
    member_result.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [group_result, member_result]

    with pytest.raises(ValueError, match="Policy .* is not in duplicate group"):
        await deduplication_service.consolidate_duplicates(
            db=mock_db,
            group_id=1,
            consolidated_policy_id=999,
        )


@pytest.mark.asyncio
async def test_dismiss_duplicates_success(deduplication_service, mock_db):
    """Test successful duplicate dismissal."""
    # Mock group
    group = Mock(spec=DuplicatePolicyGroup)
    group.id = 1
    group.status = DuplicateGroupStatus.DETECTED

    # Mock database query
    result = Mock()
    result.scalar_one_or_none.return_value = group
    mock_db.execute.return_value = result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    result = await deduplication_service.dismiss_duplicates(
        db=mock_db,
        group_id=1,
        notes="False positive",
    )

    assert result == group
    assert group.status == DuplicateGroupStatus.DISMISSED
    assert group.consolidation_notes == "False positive"


@pytest.mark.asyncio
async def test_dismiss_duplicates_group_not_found(deduplication_service, mock_db):
    """Test dismissal when group not found."""
    # Mock database query returning None
    result = Mock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result

    with pytest.raises(ValueError, match="Duplicate group .* not found"):
        await deduplication_service.dismiss_duplicates(
            db=mock_db,
            group_id=999,
        )


@pytest.mark.asyncio
async def test_get_duplicate_groups(deduplication_service, mock_db):
    """Test getting duplicate groups."""
    # Mock groups
    groups = [
        Mock(spec=DuplicatePolicyGroup),
        Mock(spec=DuplicatePolicyGroup),
    ]

    # Mock database query
    result = Mock()
    result.scalars.return_value.all.return_value = groups
    mock_db.execute.return_value = result

    result = await deduplication_service.get_duplicate_groups(
        db=mock_db,
        tenant_id="test-tenant",
        status=DuplicateGroupStatus.DETECTED,
    )

    assert result == groups


@pytest.mark.asyncio
async def test_get_duplicate_group_with_policies(deduplication_service, mock_db, sample_policies):
    """Test getting duplicate group with policies."""
    # Mock group
    group = Mock(spec=DuplicatePolicyGroup)
    group.id = 1

    # Mock members with policies
    members_data = [
        (Mock(spec=DuplicatePolicyGroupMember, similarity_to_group=0.95), sample_policies[0]),
        (Mock(spec=DuplicatePolicyGroupMember, similarity_to_group=0.92), sample_policies[1]),
    ]

    # Mock database queries
    group_result = Mock()
    group_result.scalar_one_or_none.return_value = group
    members_result = Mock()
    members_result.all.return_value = members_data

    mock_db.execute.side_effect = [group_result, members_result]

    result = await deduplication_service.get_duplicate_group_with_policies(
        db=mock_db,
        group_id=1,
    )

    assert result is not None
    returned_group, policies_with_scores = result
    assert returned_group == group
    assert len(policies_with_scores) == 2
    assert policies_with_scores[0][1] == 0.95
    assert policies_with_scores[1][1] == 0.92


@pytest.mark.asyncio
async def test_get_duplicate_group_with_policies_not_found(deduplication_service, mock_db):
    """Test getting duplicate group when not found."""
    # Mock database query returning None
    result = Mock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result

    result = await deduplication_service.get_duplicate_group_with_policies(
        db=mock_db,
        group_id=999,
    )

    assert result is None
