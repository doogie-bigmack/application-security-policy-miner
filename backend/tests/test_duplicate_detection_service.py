"""Tests for duplicate detection service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.duplicate_detection_service import DuplicateDetectionService


@pytest.fixture
def service():
    """Create duplicate detection service instance."""
    return DuplicateDetectionService()


@pytest.mark.asyncio
async def test_find_duplicates_empty_database(service):
    """Test finding duplicates with no policies."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))))

    result = await service.find_duplicates_across_applications(
        db=db,
        tenant_id="test-tenant",
    )

    assert result == []


@pytest.mark.asyncio
async def test_find_duplicates_no_matches(service):
    """Test finding duplicates with no similar policies."""
    db = AsyncMock()

    # Create mock policies with different embeddings (not similar)
    policy1 = Mock(id=1, application_id=1, embedding=[0.1] * 1536)
    policy2 = Mock(id=2, application_id=2, embedding=[0.9] * 1536)

    db.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[policy1, policy2])))))

    # Mock similarity service to return no similar policies
    with patch.object(service.similarity_service, 'find_similar_policies', return_value=[]):
        result = await service.find_duplicates_across_applications(
            db=db,
            tenant_id="test-tenant",
        )

    assert result == []


@pytest.mark.asyncio
async def test_find_duplicates_with_matches(service):
    """Test finding duplicates with similar policies."""
    db = AsyncMock()

    # Create mock policies
    policy1 = Mock(
        id=1,
        application_id=1,
        embedding=[0.5] * 1536,
        subject="Manager",
        resource="Expense",
        action="Approve",
        conditions="amount < 5000",
    )
    policy2 = Mock(
        id=2,
        application_id=2,
        embedding=[0.5] * 1536,
        subject="Manager",
        resource="Expense",
        action="Approve",
        conditions="amount < 5000",
    )
    policy3 = Mock(
        id=3,
        application_id=3,
        embedding=[0.5] * 1536,
        subject="Manager",
        resource="Expense",
        action="Approve",
        conditions="amount < 5000",
    )

    # Mock applications
    app1 = Mock(id=1, name="App1")
    app2 = Mock(id=2, name="App2")
    app3 = Mock(id=3, name="App3")

    # Mock database responses
    execute_calls = [
        # Initial query for all policies
        Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[policy1, policy2, policy3])))),
        # Application query
        Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[app1, app2, app3])))),
    ]
    db.execute = AsyncMock(side_effect=execute_calls)

    # Mock similarity service to return similar policies
    with patch.object(
        service.similarity_service,
        'find_similar_policies',
        return_value=[(policy2, 0.98), (policy3, 0.97)],
    ):
        result = await service.find_duplicates_across_applications(
            db=db,
            tenant_id="test-tenant",
            min_similarity=0.95,
        )

    assert len(result) == 1
    assert result[0]["policy_ids"] == [1, 2, 3]
    assert result[0]["application_count"] == 3
    assert result[0]["potential_savings"] == 2
    assert 0.97 <= result[0]["similarity_score"] <= 0.98


@pytest.mark.asyncio
async def test_find_duplicates_filters_same_application(service):
    """Test that duplicates are only found across different applications."""
    db = AsyncMock()

    policy1 = Mock(id=1, application_id=1, embedding=[0.5] * 1536)
    policy2 = Mock(id=2, application_id=1, embedding=[0.5] * 1536)  # Same app!

    db.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[policy1, policy2])))))

    # Mock similarity service returns policy from same app
    with patch.object(
        service.similarity_service,
        'find_similar_policies',
        return_value=[(policy2, 0.98)],
    ):
        result = await service.find_duplicates_across_applications(
            db=db,
            tenant_id="test-tenant",
        )

    # Should not create duplicate group because policies are from same app
    assert result == []


@pytest.mark.asyncio
async def test_get_duplicate_statistics(service):
    """Test getting duplicate statistics."""
    db = AsyncMock()

    # Mock total count
    db.execute = AsyncMock(
        side_effect=[
            Mock(scalar=Mock(return_value=100)),  # Total policies
        ]
    )

    # Mock find_duplicates_across_applications
    mock_groups = [
        {"policies": [Mock(), Mock(), Mock()], "potential_savings": 2},  # 3 policies, save 2
        {"policies": [Mock(), Mock()], "potential_savings": 1},  # 2 policies, save 1
    ]

    with patch.object(
        service,
        'find_duplicates_across_applications',
        return_value=mock_groups,
    ):
        stats = await service.get_duplicate_statistics(
            db=db,
            tenant_id="test-tenant",
        )

    assert stats["total_policies"] == 100
    assert stats["total_duplicates"] == 5  # 3 + 2
    assert stats["duplicate_groups"] == 2
    assert stats["potential_savings_count"] == 3  # 2 + 1
    assert stats["potential_savings_percentage"] == 3.0  # 3/100 * 100


@pytest.mark.asyncio
async def test_consolidate_duplicate_group(service):
    """Test consolidating a duplicate group."""
    db = AsyncMock()

    policy1 = Mock(id=1, spec=["id"])
    policy2 = Mock(id=2, spec=["id"])
    policy3 = Mock(id=3, spec=["id"])

    # Mock database execute to return policies
    execute_calls = [
        Mock(scalar_one_or_none=Mock(return_value=policy1)),  # Keep policy
        Mock(scalar_one_or_none=Mock(return_value=policy2)),  # Remove
        Mock(scalar_one_or_none=Mock(return_value=policy3)),  # Remove
    ]
    db.execute = AsyncMock(side_effect=execute_calls)
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    result = await service.consolidate_duplicate_group(
        db=db,
        policy_ids=[1, 2, 3],
        keep_policy_id=1,
    )

    assert result["kept_policy_id"] == 1
    assert result["removed_policy_ids"] == [2, 3]
    assert result["removed_count"] == 2
    assert db.delete.call_count == 2
    assert db.commit.called


@pytest.mark.asyncio
async def test_consolidate_invalid_keep_policy(service):
    """Test consolidating with invalid keep_policy_id."""
    db = AsyncMock()

    with pytest.raises(ValueError, match="keep_policy_id.*not in policy_ids"):
        await service.consolidate_duplicate_group(
            db=db,
            policy_ids=[1, 2, 3],
            keep_policy_id=999,  # Not in list
        )


@pytest.mark.asyncio
async def test_consolidate_nonexistent_policy(service):
    """Test consolidating when keep policy doesn't exist."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

    with pytest.raises(ValueError, match="Policy.*not found"):
        await service.consolidate_duplicate_group(
            db=db,
            policy_ids=[1, 2, 3],
            keep_policy_id=1,
        )


@pytest.mark.asyncio
async def test_find_duplicates_sorts_by_savings(service):
    """Test that duplicate groups are sorted by potential savings."""
    db = AsyncMock()

    # Create policies
    policies = [Mock(id=i, application_id=i, embedding=[0.5] * 1536) for i in range(1, 11)]

    db.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=policies)))))

    # Mock two groups with different savings
    group1_policies = [(policies[1], 0.96), (policies[2], 0.96)]  # 2 duplicates
    group2_policies = [(policies[4], 0.97), (policies[5], 0.97), (policies[6], 0.97), (policies[7], 0.97)]  # 4 duplicates

    calls_remaining = [group1_policies, group2_policies] + [[] for _ in range(8)]

    async def mock_find_similar(*args, **kwargs):
        if calls_remaining:
            return calls_remaining.pop(0)
        return []

    # Mock applications
    apps_execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[Mock(id=i, name=f"App{i}") for i in range(1, 11)])))))

    original_execute = db.execute

    async def execute_wrapper(*args, **kwargs):
        # Second call is for applications
        if hasattr(execute_wrapper, 'call_count'):
            execute_wrapper.call_count += 1
            if execute_wrapper.call_count > 1:
                return await apps_execute(*args, **kwargs)
        else:
            execute_wrapper.call_count = 1
        return await original_execute(*args, **kwargs)

    db.execute = execute_wrapper

    with patch.object(service.similarity_service, 'find_similar_policies', side_effect=mock_find_similar):
        result = await service.find_duplicates_across_applications(
            db=db,
            tenant_id="test-tenant",
        )

    # Should be sorted by savings descending
    assert len(result) == 2
    assert result[0]["potential_savings"] >= result[1]["potential_savings"]
