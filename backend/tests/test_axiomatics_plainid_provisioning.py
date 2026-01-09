"""Tests for Axiomatics and PlainID policy provisioning."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Import all models to ensure they're registered with SQLAlchemy
from app.models.policy import Policy  # noqa: F401
from app.models.provisioning import (
    PBACProvider,
    ProviderType,
    ProvisioningStatus,
)
from app.models.repository import Base, Repository  # noqa: F401
from app.models.secret_detection import SecretDetectionLog  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.scan_progress import ScanProgress  # noqa: F401
from app.models.policy_change import PolicyChange, WorkItem  # noqa: F401
from app.models.conflict import PolicyConflict  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.services.provisioning_service import ProvisioningService


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("postgresql://policy_miner:dev_password@postgres:5432/policy_miner")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Create test tenant if not exists
    tenant = session.query(Tenant).filter_by(tenant_id="test-tenant").first()
    if not tenant:
        tenant = Tenant(tenant_id="test-tenant", name="Test Tenant")
        session.add(tenant)
        session.commit()

    yield session

    session.close()


@pytest.fixture
def test_repository(db_session: Session):
    """Create a test repository."""
    repository = Repository(
        tenant_id="test-tenant",
        name="Test Repository",
        repository_type="git",
        source_url="https://github.com/test/repo.git",
        status="connected",
    )
    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)
    return repository


@pytest.fixture
def test_policy(db_session: Session, test_repository: Repository):
    """Create a test policy."""
    policy = Policy(
        tenant_id="test-tenant",
        repository_id=test_repository.id,
        subject="Manager",
        resource="ExpenseReport",
        action="approve",
        conditions="amount < 5000",
        description="Test policy for provisioning",
        risk_score=50.0,
        complexity_score=30.0,
        impact_score=60.0,
        confidence_score=80.0,
        historical_score=0.0,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def axiomatics_provider(db_session: Session):
    """Create an Axiomatics provider."""
    provider = PBACProvider(
        tenant_id="test-tenant",
        provider_type=ProviderType.AXIOMATICS,
        name="Test Axiomatics",
        endpoint_url="https://axiomatics.example.com",
        api_key="test-axiomatics-key",
        configuration=json.dumps({"auth_type": "bearer"}),
    )
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)
    return provider


@pytest.fixture
def plainid_provider(db_session: Session):
    """Create a PlainID provider."""
    provider = PBACProvider(
        tenant_id="test-tenant",
        provider_type=ProviderType.PLAINID,
        name="Test PlainID",
        endpoint_url="https://plainid.example.com",
        api_key="test-plainid-key",
        configuration=json.dumps({"tenant_id": "customer-123"}),
    )
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)
    return provider


class TestAxiomaticsProvisioning:
    """Tests for Axiomatics provisioning."""

    @pytest.mark.asyncio
    async def test_push_to_axiomatics_success(
        self, db_session: Session, test_policy: Policy, axiomatics_provider: PBACProvider
    ):
        """Test successful push to Axiomatics."""
        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            await service._push_to_axiomatics(
                axiomatics_provider,
                test_policy,
                '{"policy": "test"}',
            )

            # Verify PUT was called
            mock_put.assert_called_once()
            call_args = mock_put.call_args

            # Verify URL
            assert call_args.args[0] == f"https://axiomatics.example.com/api/policies/policy-{test_policy.id}"

            # Verify headers
            headers = call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer test-axiomatics-key"
            assert headers["Content-Type"] == "application/json"

            # Verify payload
            payload = call_args.kwargs["json"]
            assert payload["policyId"] == f"policy-{test_policy.id}"
            assert payload["content"] == '{"policy": "test"}'
            assert payload["enabled"] is True

    @pytest.mark.asyncio
    async def test_push_to_axiomatics_create_if_not_exists(
        self, db_session: Session, test_policy: Policy, axiomatics_provider: PBACProvider
    ):
        """Test creating policy if it doesn't exist in Axiomatics."""
        service = ProvisioningService(db_session)

        mock_put_response = MagicMock()
        mock_put_response.status_code = 404

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.text = "Created"

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_put_response)
            mock_post = AsyncMock(return_value=mock_post_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await service._push_to_axiomatics(
                axiomatics_provider,
                test_policy,
                '{"policy": "test"}',
            )

            # Verify PUT was called first
            mock_put.assert_called_once()

            # Verify POST was called after 404
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.args[0] == "https://axiomatics.example.com/api/policies"

    @pytest.mark.asyncio
    async def test_push_to_axiomatics_with_apikey_auth(
        self, db_session: Session, test_policy: Policy
    ):
        """Test Axiomatics push with API key authentication."""
        provider = PBACProvider(
            tenant_id="test-tenant",
            provider_type=ProviderType.AXIOMATICS,
            name="Test Axiomatics",
            endpoint_url="https://axiomatics.example.com",
            api_key="test-key",
            configuration=json.dumps({"auth_type": "apikey"}),
        )
        db_session.add(provider)
        db_session.commit()

        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            await service._push_to_axiomatics(provider, test_policy, '{"policy": "test"}')

            call_args = mock_put.call_args
            headers = call_args.kwargs["headers"]
            assert headers["X-API-Key"] == "test-key"

    @pytest.mark.asyncio
    async def test_push_to_axiomatics_error_handling(
        self, db_session: Session, test_policy: Policy, axiomatics_provider: PBACProvider
    ):
        """Test error handling for Axiomatics push."""
        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            with pytest.raises(Exception) as exc_info:
                await service._push_to_axiomatics(
                    axiomatics_provider,
                    test_policy,
                    '{"policy": "test"}',
                )

            assert "Axiomatics returned status 500" in str(exc_info.value)


class TestPlainIDProvisioning:
    """Tests for PlainID provisioning."""

    @pytest.mark.asyncio
    async def test_push_to_plainid_success(
        self, db_session: Session, test_policy: Policy, plainid_provider: PBACProvider
    ):
        """Test successful push to PlainID."""
        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            await service._push_to_plainid(
                plainid_provider,
                test_policy,
                '{"policy": "test"}',
            )

            # Verify PUT was called
            mock_put.assert_called_once()
            call_args = mock_put.call_args

            # Verify URL
            assert call_args.args[0] == f"https://plainid.example.com/api/v1/policies/policy-{test_policy.id}"

            # Verify headers
            headers = call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer test-plainid-key"
            assert headers["Content-Type"] == "application/json"

            # Verify payload
            payload = call_args.kwargs["json"]
            assert payload["id"] == f"policy-{test_policy.id}"
            assert payload["status"] == "active"
            assert payload["tenantId"] == "customer-123"
            assert "policy_miner" in payload["tags"]

    @pytest.mark.asyncio
    async def test_push_to_plainid_create_if_not_exists(
        self, db_session: Session, test_policy: Policy, plainid_provider: PBACProvider
    ):
        """Test creating policy if it doesn't exist in PlainID."""
        service = ProvisioningService(db_session)

        mock_put_response = MagicMock()
        mock_put_response.status_code = 404

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.text = "Created"

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_put_response)
            mock_post = AsyncMock(return_value=mock_post_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await service._push_to_plainid(
                plainid_provider,
                test_policy,
                '{"policy": "test"}',
            )

            # Verify PUT was called first
            mock_put.assert_called_once()

            # Verify POST was called after 404
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.args[0] == "https://plainid.example.com/api/v1/policies"

    @pytest.mark.asyncio
    async def test_push_to_plainid_with_json_policy(
        self, db_session: Session, test_policy: Policy, plainid_provider: PBACProvider
    ):
        """Test PlainID push with JSON policy format."""
        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 200

        json_policy = '{"subject": "Manager", "resource": "ExpenseReport", "action": "approve"}'

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            await service._push_to_plainid(plainid_provider, test_policy, json_policy)

            call_args = mock_put.call_args
            payload = call_args.kwargs["json"]

            # Verify JSON policy was parsed
            assert isinstance(payload["policy"], dict)
            assert payload["policy"]["subject"] == "Manager"

    @pytest.mark.asyncio
    async def test_push_to_plainid_error_handling(
        self, db_session: Session, test_policy: Policy, plainid_provider: PBACProvider
    ):
        """Test error handling for PlainID push."""
        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            with pytest.raises(Exception) as exc_info:
                await service._push_to_plainid(
                    plainid_provider,
                    test_policy,
                    '{"policy": "test"}',
                )

            assert "PlainID returned status 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_push_to_plainid_includes_metadata(
        self, db_session: Session, test_policy: Policy, plainid_provider: PBACProvider
    ):
        """Test that PlainID payload includes policy metadata."""
        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            await service._push_to_plainid(plainid_provider, test_policy, '{"test": "policy"}')

            call_args = mock_put.call_args
            payload = call_args.kwargs["json"]

            # Verify metadata
            assert "metadata" in payload
            metadata = payload["metadata"]
            assert metadata["source"] == "policy_miner"
            assert metadata["subject"] == "Manager"
            assert metadata["resource"] == "ExpenseReport"
            assert metadata["action"] == "approve"
            assert metadata["risk_score"] == 50.0


class TestIntegrationProvisioning:
    """Integration tests for provisioning workflow."""

    @pytest.mark.asyncio
    async def test_provision_policy_to_axiomatics_end_to_end(
        self, db_session: Session, test_policy: Policy, axiomatics_provider: PBACProvider
    ):
        """Test complete provisioning workflow to Axiomatics."""
        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            with patch.object(
                service.translation_service,
                "translate_to_json",
                return_value='{"policy": "test"}',
            ):
                operation = await service.provision_policy(
                    test_policy.id,
                    axiomatics_provider.provider_id,
                    "test-tenant",
                )

                # Verify operation was created and marked successful
                assert operation.status == ProvisioningStatus.SUCCESS
                assert operation.policy_id == test_policy.id
                assert operation.provider_id == axiomatics_provider.provider_id
                assert operation.translated_policy == '{"policy": "test"}'
                assert operation.completed_at is not None

    @pytest.mark.asyncio
    async def test_provision_policy_to_plainid_end_to_end(
        self, db_session: Session, test_policy: Policy, plainid_provider: PBACProvider
    ):
        """Test complete provisioning workflow to PlainID."""
        service = ProvisioningService(db_session)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_put = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.put = mock_put

            with patch.object(
                service.translation_service,
                "translate_to_json",
                return_value='{"policy": "test"}',
            ):
                operation = await service.provision_policy(
                    test_policy.id,
                    plainid_provider.provider_id,
                    "test-tenant",
                )

                # Verify operation was created and marked successful
                assert operation.status == ProvisioningStatus.SUCCESS
                assert operation.policy_id == test_policy.id
                assert operation.provider_id == plainid_provider.provider_id
                assert operation.completed_at is not None
