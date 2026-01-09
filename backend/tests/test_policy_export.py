"""Unit tests for policy export endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from app.api.v1.endpoints.policies import (
    export_policy_cedar,
    export_policy_json,
    export_policy_rego,
)
from app.models.policy import Policy, PolicyStatus, SourceType


@pytest.fixture
def sample_policy(db: Session):
    """Create a sample policy for testing."""
    policy = Policy(
        repository_id=1,
        tenant_id=1,
        subject="user.role == 'manager'",
        resource="expense",
        action="approve",
        conditions="amount < 5000",
        description="Managers can approve expenses under $5000",
        status=PolicyStatus.APPROVED,
        source_type=SourceType.BACKEND,
        risk_score=45.0,
        complexity_score=30.0,
        impact_score=60.0,
        confidence_score=85.0,
        historical_score=0.0,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@pytest.mark.asyncio
async def test_export_policy_rego_success(db: Session, sample_policy: Policy):
    """Test successful export of policy to Rego format."""
    mock_rego = """package authz

# Allow managers to approve expenses under $5000
allow {
    input.user.role == "manager"
    input.resource.type == "expense"
    input.action == "approve"
    input.resource.amount < 5000
}"""

    with patch(
        "app.api.v1.endpoints.policies.TranslationService"
    ) as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_to_rego = AsyncMock(return_value=mock_rego)
        mock_service.return_value = mock_instance

        result = await export_policy_rego(sample_policy.id, db)

        assert result.format == "rego"
        assert result.policy == mock_rego
        assert "package authz" in result.policy
        assert "allow {" in result.policy
        mock_instance.translate_to_rego.assert_called_once()


@pytest.mark.asyncio
async def test_export_policy_rego_not_found(db: Session):
    """Test export fails when policy not found."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await export_policy_rego(999, db)

    assert exc_info.value.status_code == 404
    assert "Policy not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_export_policy_cedar_success(db: Session, sample_policy: Policy):
    """Test successful export of policy to Cedar format."""
    mock_cedar = """permit (
    principal in Role::"manager",
    action == Action::"approve",
    resource in ResourceType::"expense"
)
when {
    resource.amount < 5000
};"""

    with patch(
        "app.api.v1.endpoints.policies.TranslationService"
    ) as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_to_cedar = AsyncMock(return_value=mock_cedar)
        mock_service.return_value = mock_instance

        result = await export_policy_cedar(sample_policy.id, db)

        assert result.format == "cedar"
        assert result.policy == mock_cedar
        assert "permit" in result.policy
        assert "principal" in result.policy
        mock_instance.translate_to_cedar.assert_called_once()


@pytest.mark.asyncio
async def test_export_policy_cedar_not_found(db: Session):
    """Test Cedar export fails when policy not found."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await export_policy_cedar(999, db)

    assert exc_info.value.status_code == 404
    assert "Policy not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_export_policy_json_success(db: Session, sample_policy: Policy):
    """Test successful export of policy to JSON format."""
    with patch(
        "app.api.v1.endpoints.policies.TranslationService"
    ) as mock_service:
        mock_json = """{
  "subject": "user.role == 'manager'",
  "resource": "expense",
  "action": "approve",
  "conditions": "amount < 5000",
  "description": "Managers can approve expenses under $5000",
  "source_type": "backend"
}"""
        mock_instance = AsyncMock()
        mock_instance.translate_to_json = AsyncMock(return_value=mock_json)
        mock_service.return_value = mock_instance

        result = await export_policy_json(sample_policy.id, db)

        assert result.format == "json"
        assert result.policy == mock_json
        assert '"subject"' in result.policy
        assert '"resource"' in result.policy
        mock_instance.translate_to_json.assert_called_once()


@pytest.mark.asyncio
async def test_export_policy_json_not_found(db: Session):
    """Test JSON export fails when policy not found."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await export_policy_json(999, db)

    assert exc_info.value.status_code == 404
    assert "Policy not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_export_policy_rego_translation_error(db: Session, sample_policy: Policy):
    """Test export handles translation errors gracefully."""
    from fastapi import HTTPException

    with patch(
        "app.api.v1.endpoints.policies.TranslationService"
    ) as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_to_rego = AsyncMock(
            side_effect=Exception("Translation failed")
        )
        mock_service.return_value = mock_instance

        with pytest.raises(HTTPException) as exc_info:
            await export_policy_rego(sample_policy.id, db)

        assert exc_info.value.status_code == 500
        assert "Failed to export policy to Rego" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_export_policy_cedar_translation_error(db: Session, sample_policy: Policy):
    """Test Cedar export handles translation errors gracefully."""
    from fastapi import HTTPException

    with patch(
        "app.api.v1.endpoints.policies.TranslationService"
    ) as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_to_cedar = AsyncMock(
            side_effect=Exception("Translation failed")
        )
        mock_service.return_value = mock_instance

        with pytest.raises(HTTPException) as exc_info:
            await export_policy_cedar(sample_policy.id, db)

        assert exc_info.value.status_code == 500
        assert "Failed to export policy to Cedar" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_export_all_formats(db: Session, sample_policy: Policy):
    """Test exporting a policy to all three formats."""
    with patch(
        "app.api.v1.endpoints.policies.TranslationService"
    ) as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_to_rego = AsyncMock(return_value="package authz\nallow { true }")
        mock_instance.translate_to_cedar = AsyncMock(return_value="permit (principal, action, resource);")
        mock_instance.translate_to_json = AsyncMock(return_value='{"subject": "test"}')
        mock_service.return_value = mock_instance

        # Export to all formats
        rego_result = await export_policy_rego(sample_policy.id, db)
        cedar_result = await export_policy_cedar(sample_policy.id, db)
        json_result = await export_policy_json(sample_policy.id, db)

        # Verify all exports succeeded
        assert rego_result.format == "rego"
        assert cedar_result.format == "cedar"
        assert json_result.format == "json"

        # Verify each format has correct structure
        assert "package authz" in rego_result.policy
        assert "permit" in cedar_result.policy
        assert "subject" in json_result.policy
