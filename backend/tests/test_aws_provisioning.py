"""Tests for AWS Verified Permissions provisioning."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.policy import Policy, PolicyStatus, SourceType
from app.models.provisioning import PBACProvider, ProviderType, ProvisioningStatus
from app.models.repository import Base
from app.models.tenant import Tenant
from app.services.provisioning_service import ProvisioningService


@pytest.fixture
def db_session():
    """Create in-memory database for testing."""
    engine = create_engine("postgresql://test:test@localhost/test_db")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()

    # Create test tenant
    tenant = Tenant(
        tenant_id="test-tenant",
        name="Test Tenant",
        description="Test tenant for provisioning tests",
    )
    session.add(tenant)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def aws_provider(db_session):
    """Create AWS Verified Permissions provider for testing."""
    provider = PBACProvider(
        tenant_id="test-tenant",
        provider_type=ProviderType.AWS_VERIFIED_PERMISSIONS,
        name="Test AWS Provider",
        endpoint_url="us-east-1",
        api_key=None,
        configuration='{"policy_store_id": "test-policy-store-123"}',
    )
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)
    return provider


@pytest.fixture
def test_policy(db_session):
    """Create test policy."""
    policy = Policy(
        tenant_id="test-tenant",
        repository_id=1,
        subject="Manager",
        resource="Expense",
        action="approve",
        conditions="amount < 5000",
        description="Managers can approve expenses under $5000",
        source_type=SourceType.BACKEND,
        status=PolicyStatus.APPROVED,
        overall_risk_score=25.0,
        complexity_score=20.0,
        impact_score=30.0,
        confidence_score=90.0,
        historical_score=0.0,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.mark.asyncio
async def test_push_to_aws_with_explicit_credentials(db_session, aws_provider, test_policy):
    """Test pushing policy to AWS with explicit credentials."""
    # Add credentials to provider config
    aws_provider.configuration = """{
        "policy_store_id": "test-policy-store-123",
        "aws_access_key_id": "AKIATEST123",
        "aws_secret_access_key": "test-secret-key"
    }"""
    db_session.commit()

    service = ProvisioningService(db_session)

    # Mock boto3 client
    with patch("boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Mock ResourceNotFoundException for update (to trigger create path)
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})
        mock_client.update_policy.side_effect = mock_client.exceptions.ResourceNotFoundException()

        # Mock successful create
        mock_client.create_policy.return_value = {
            "policyId": "policy-1",
            "policyVersion": "v1",
        }

        # Mock translation service
        with patch.object(service.translation_service, "translate_to_cedar") as mock_translate:
            mock_translate.return_value = """permit (
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"Expense"
)
when {
    resource.amount < 5000
};"""

            # Provision policy
            operation = await service.provision_policy(
                test_policy.id, aws_provider.provider_id, "test-tenant"
            )

            # Verify boto3 was called with correct params
            mock_boto3.assert_called_once_with(
                "verifiedpermissions",
                region_name="us-east-1",
                aws_access_key_id="AKIATEST123",
                aws_secret_access_key="test-secret-key",
            )

            # Verify create_policy was called
            assert mock_client.create_policy.called
            create_call = mock_client.create_policy.call_args
            assert create_call[1]["policyStoreId"] == "test-policy-store-123"
            assert "permit" in create_call[1]["definition"]["static"]["statement"]

            # Verify operation status
            assert operation.status == ProvisioningStatus.SUCCESS
            assert operation.translated_policy is not None
            assert "permit" in operation.translated_policy


@pytest.mark.asyncio
async def test_push_to_aws_with_iam_role(db_session, aws_provider, test_policy):
    """Test pushing policy to AWS using IAM role (no explicit credentials)."""
    service = ProvisioningService(db_session)

    with patch("boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Mock successful update
        mock_client.update_policy.return_value = {
            "policyId": "policy-1",
            "policyVersion": "v2",
        }

        with patch.object(service.translation_service, "translate_to_cedar") as mock_translate:
            mock_translate.return_value = """permit (
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"Expense"
)
when {
    resource.amount < 5000
};"""

            operation = await service.provision_policy(
                test_policy.id, aws_provider.provider_id, "test-tenant"
            )

            # Verify boto3 was called without explicit credentials
            mock_boto3.assert_called_once_with(
                "verifiedpermissions",
                region_name="us-east-1",
            )

            # Verify update_policy was called
            assert mock_client.update_policy.called
            assert operation.status == ProvisioningStatus.SUCCESS


@pytest.mark.asyncio
async def test_push_to_aws_missing_policy_store_id(db_session, test_policy):
    """Test error handling when policy_store_id is missing."""
    # Create provider without policy_store_id
    bad_provider = PBACProvider(
        tenant_id="test-tenant",
        provider_type=ProviderType.AWS_VERIFIED_PERMISSIONS,
        name="Bad AWS Provider",
        endpoint_url="us-east-1",
        api_key=None,
        configuration='{}',  # Missing policy_store_id
    )
    db_session.add(bad_provider)
    db_session.commit()
    db_session.refresh(bad_provider)

    service = ProvisioningService(db_session)

    with patch.object(service.translation_service, "translate_to_cedar") as mock_translate:
        mock_translate.return_value = "permit (principal, action, resource);"

        operation = await service.provision_policy(
            test_policy.id, bad_provider.provider_id, "test-tenant"
        )

        # Verify operation failed with appropriate error
        assert operation.status == ProvisioningStatus.FAILED
        assert "policy_store_id" in operation.error_message.lower()


@pytest.mark.asyncio
async def test_push_to_aws_api_error(db_session, aws_provider, test_policy):
    """Test error handling when AWS API returns error."""
    service = ProvisioningService(db_session)

    with patch("boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Mock ResourceNotFoundException
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})
        mock_client.update_policy.side_effect = mock_client.exceptions.ResourceNotFoundException()

        # Mock API error on create
        mock_client.create_policy.side_effect = Exception("AWS API Error: Invalid policy syntax")

        with patch.object(service.translation_service, "translate_to_cedar") as mock_translate:
            mock_translate.return_value = "permit (principal, action, resource);"

            operation = await service.provision_policy(
                test_policy.id, aws_provider.provider_id, "test-tenant"
            )

            # Verify operation failed
            assert operation.status == ProvisioningStatus.FAILED
            assert "AWS" in operation.error_message
            assert "Invalid policy syntax" in operation.error_message


@pytest.mark.asyncio
async def test_cedar_validation_success(db_session):
    """Test Cedar policy validation with valid policy."""
    from app.services.translation_service import TranslationService

    service = TranslationService()

    valid_cedar = """permit (
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"Expense"
)
when {
    resource.amount < 5000
};"""

    # Should not raise exception
    service._validate_cedar_policy(valid_cedar)


@pytest.mark.asyncio
async def test_cedar_validation_missing_permit(db_session):
    """Test Cedar policy validation with missing permit/forbid."""
    from app.services.translation_service import TranslationService

    service = TranslationService()

    invalid_cedar = """(
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"Expense"
);"""

    with pytest.raises(ValueError, match="permit.*forbid"):
        service._validate_cedar_policy(invalid_cedar)


@pytest.mark.asyncio
async def test_cedar_validation_missing_principal(db_session):
    """Test Cedar policy validation with missing principal."""
    from app.services.translation_service import TranslationService

    service = TranslationService()

    invalid_cedar = """permit (
    action == Action::"approve",
    resource in ResourceType::"Expense"
);"""

    with pytest.raises(ValueError, match="principal"):
        service._validate_cedar_policy(invalid_cedar)


@pytest.mark.asyncio
async def test_cedar_validation_missing_semicolon(db_session):
    """Test Cedar policy validation with missing semicolon."""
    from app.services.translation_service import TranslationService

    service = TranslationService()

    invalid_cedar = """permit (
    principal in Role::"Manager",
    action == Action::"approve",
    resource in ResourceType::"Expense"
)"""

    with pytest.raises(ValueError, match="semicolon"):
        service._validate_cedar_policy(invalid_cedar)


@pytest.mark.asyncio
async def test_bulk_provision_to_aws(db_session, aws_provider):
    """Test bulk provisioning to AWS Verified Permissions."""
    # Create multiple policies
    policies = []
    for i in range(3):
        policy = Policy(
            tenant_id="test-tenant",
            repository_id=1,
            subject=f"User{i}",
            resource=f"Resource{i}",
            action="access",
            conditions="authenticated",
            description=f"Test policy {i}",
            source_type=SourceType.BACKEND,
            status=PolicyStatus.APPROVED,
            overall_risk_score=20.0,
            complexity_score=15.0,
            impact_score=25.0,
            confidence_score=85.0,
            historical_score=0.0,
        )
        db_session.add(policy)
        policies.append(policy)

    db_session.commit()
    for policy in policies:
        db_session.refresh(policy)

    service = ProvisioningService(db_session)

    with patch("boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        # Mock successful create
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})
        mock_client.update_policy.side_effect = mock_client.exceptions.ResourceNotFoundException()
        mock_client.create_policy.return_value = {"policyId": "test", "policyVersion": "v1"}

        with patch.object(service.translation_service, "translate_to_cedar") as mock_translate:
            mock_translate.return_value = "permit (principal, action, resource);"

            # Bulk provision
            operations = await service.bulk_provision_policies(
                [p.id for p in policies], aws_provider.provider_id, "test-tenant"
            )

            # Verify all operations successful
            assert len(operations) == 3
            assert all(op.status == ProvisioningStatus.SUCCESS for op in operations)
            assert mock_client.create_policy.call_count == 3
