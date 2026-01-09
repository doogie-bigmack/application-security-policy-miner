"""Tests for the provisioning service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.policy import Policy, PolicyStatus, RiskLevel, SourceType
from app.models.provisioning import (
    ProviderType,
    ProvisioningStatus,
)
from app.models.repository import Base
from app.schemas.provisioning import PBACProviderCreate, PBACProviderUpdate
from app.services.provisioning_service import ProvisioningService

# Use PostgreSQL for testing (SQLite has issues with JSONB)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5434/test_db"


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_local()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_policy(db_session):
    """Create a sample policy for testing."""
    policy = Policy(
        policy_id=1,
        tenant_id="test-tenant",
        repository_id=1,
        subject="Manager",
        resource="expense",
        action="approve",
        conditions="amount < 5000",
        description="Managers can approve expenses under $5000",
        status=PolicyStatus.APPROVED,
        risk_score=30,
        complexity_score=20,
        impact_score=40,
        confidence_score=90,
        historical_score=0,
        risk_level=RiskLevel.LOW,
        source_type=SourceType.BACKEND,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.mark.asyncio
async def test_create_provider(db_session):
    """Test creating a PBAC provider."""
    service = ProvisioningService(db_session)

    provider_data = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="Test OPA",
        endpoint_url="http://localhost:8181",
        api_key="test-key",
        configuration='{"setting": "value"}',
    )

    provider = await service.create_provider(provider_data, "test-tenant")

    assert provider.provider_id is not None
    assert provider.tenant_id == "test-tenant"
    assert provider.provider_type == ProviderType.OPA
    assert provider.name == "Test OPA"
    assert provider.endpoint_url == "http://localhost:8181"


@pytest.mark.asyncio
async def test_get_providers(db_session):
    """Test getting all providers for a tenant."""
    service = ProvisioningService(db_session)

    # Create multiple providers
    provider_data_1 = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="OPA 1",
        endpoint_url="http://localhost:8181",
    )
    provider_data_2 = PBACProviderCreate(
        provider_type=ProviderType.AWS_VERIFIED_PERMISSIONS,
        name="AWS VP",
        endpoint_url="us-east-1",
    )

    await service.create_provider(provider_data_1, "test-tenant")
    await service.create_provider(provider_data_2, "test-tenant")

    # Different tenant
    await service.create_provider(provider_data_1, "other-tenant")

    providers = await service.get_providers("test-tenant")

    assert len(providers) == 2
    assert all(p.tenant_id == "test-tenant" for p in providers)


@pytest.mark.asyncio
async def test_update_provider(db_session):
    """Test updating a provider."""
    service = ProvisioningService(db_session)

    # Create provider
    provider_data = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="Original Name",
        endpoint_url="http://localhost:8181",
    )
    provider = await service.create_provider(provider_data, "test-tenant")

    # Update provider
    update_data = PBACProviderUpdate(
        name="Updated Name",
        endpoint_url="http://localhost:9999",
    )
    updated = await service.update_provider(provider.provider_id, update_data, "test-tenant")

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.endpoint_url == "http://localhost:9999"


@pytest.mark.asyncio
async def test_delete_provider(db_session):
    """Test deleting a provider."""
    service = ProvisioningService(db_session)

    # Create provider
    provider_data = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="Test OPA",
        endpoint_url="http://localhost:8181",
    )
    provider = await service.create_provider(provider_data, "test-tenant")

    # Delete provider
    deleted = await service.delete_provider(provider.provider_id, "test-tenant")
    assert deleted is True

    # Verify deletion
    providers = await service.get_providers("test-tenant")
    assert len(providers) == 0


@pytest.mark.asyncio
async def test_provision_policy_to_opa(db_session, sample_policy):
    """Test provisioning a policy to OPA."""
    service = ProvisioningService(db_session)

    # Create OPA provider
    provider_data = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="Test OPA",
        endpoint_url="http://localhost:8181",
    )
    provider = await service.create_provider(provider_data, "test-tenant")

    # Mock translation service
    with patch.object(service.translation_service, "translate_to_rego") as mock_translate:
        mock_translate.return_value = "package authz\nallow { true }"

        # Mock HTTP client
        with patch("app.services.provisioning_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_response
            )

            operation = await service.provision_policy(
                sample_policy.policy_id, provider.provider_id, "test-tenant"
            )

            assert operation.status == ProvisioningStatus.SUCCESS
            assert operation.translated_policy is not None
            assert "package authz" in operation.translated_policy


@pytest.mark.asyncio
async def test_provision_policy_opa_failure(db_session, sample_policy):
    """Test handling OPA provisioning failure."""
    service = ProvisioningService(db_session)

    # Create OPA provider
    provider_data = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="Test OPA",
        endpoint_url="http://localhost:8181",
    )
    provider = await service.create_provider(provider_data, "test-tenant")

    # Mock translation service
    with patch.object(service.translation_service, "translate_to_rego") as mock_translate:
        mock_translate.return_value = "package authz\nallow { true }"

        # Mock HTTP client with error
        with patch("app.services.provisioning_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_response
            )

            operation = await service.provision_policy(
                sample_policy.policy_id, provider.provider_id, "test-tenant"
            )

            assert operation.status == ProvisioningStatus.FAILED
            assert operation.error_message is not None
            assert "500" in operation.error_message


@pytest.mark.asyncio
async def test_bulk_provision_policies(db_session):
    """Test bulk provisioning multiple policies."""
    service = ProvisioningService(db_session)

    # Create multiple policies
    policies = []
    for i in range(3):
        policy = Policy(
            tenant_id="test-tenant",
            repository_id=1,
            subject=f"User{i}",
            resource="resource",
            action="read",
            conditions="true",
            description=f"Policy {i}",
            status=PolicyStatus.APPROVED,
            risk_score=30,
            complexity_score=20,
            impact_score=40,
            confidence_score=90,
            historical_score=0,
            risk_level=RiskLevel.LOW,
            source_type=SourceType.BACKEND,
        )
        db_session.add(policy)
        db_session.commit()
        db_session.refresh(policy)
        policies.append(policy)

    # Create provider
    provider_data = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="Test OPA",
        endpoint_url="http://localhost:8181",
    )
    provider = await service.create_provider(provider_data, "test-tenant")

    # Mock translation and HTTP
    with patch.object(service.translation_service, "translate_to_rego") as mock_translate:
        mock_translate.return_value = "package authz\nallow { true }"

        with patch("app.services.provisioning_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_response
            )

            policy_ids = [p.policy_id for p in policies]
            operations = await service.bulk_provision_policies(
                policy_ids, provider.provider_id, "test-tenant"
            )

            assert len(operations) == 3
            assert all(op.status == ProvisioningStatus.SUCCESS for op in operations)


@pytest.mark.asyncio
async def test_get_operations(db_session, sample_policy):
    """Test getting provisioning operations."""
    service = ProvisioningService(db_session)

    # Create provider
    provider_data = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="Test OPA",
        endpoint_url="http://localhost:8181",
    )
    provider = await service.create_provider(provider_data, "test-tenant")

    # Mock provisioning
    with patch.object(service.translation_service, "translate_to_rego") as mock_translate:
        mock_translate.return_value = "package authz\nallow { true }"

        with patch("app.services.provisioning_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_response
            )

            await service.provision_policy(
                sample_policy.policy_id, provider.provider_id, "test-tenant"
            )

    # Get operations
    operations = await service.get_operations("test-tenant")
    assert len(operations) == 1

    # Filter by provider
    operations_filtered = await service.get_operations("test-tenant", provider.provider_id)
    assert len(operations_filtered) == 1


@pytest.mark.asyncio
async def test_tenant_isolation(db_session, sample_policy):
    """Test that tenant isolation works for providers and operations."""
    service = ProvisioningService(db_session)

    # Create provider for tenant A
    provider_data = PBACProviderCreate(
        provider_type=ProviderType.OPA,
        name="Tenant A OPA",
        endpoint_url="http://localhost:8181",
    )
    provider_a = await service.create_provider(provider_data, "tenant-a")

    # Create provider for tenant B
    provider_b = await service.create_provider(provider_data, "tenant-b")

    # Tenant A should only see their provider
    providers_a = await service.get_providers("tenant-a")
    assert len(providers_a) == 1
    assert providers_a[0].provider_id == provider_a.provider_id

    # Tenant B should only see their provider
    providers_b = await service.get_providers("tenant-b")
    assert len(providers_b) == 1
    assert providers_b[0].provider_id == provider_b.provider_id

    # Tenant A cannot update Tenant B's provider
    update_data = PBACProviderUpdate(name="Hacked Name")
    updated = await service.update_provider(provider_b.provider_id, update_data, "tenant-a")
    assert updated is None
