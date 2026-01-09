"""Provisioning service for pushing policies to PBAC platforms."""

from datetime import datetime

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.provisioning import (
    PBACProvider,
    ProviderType,
    ProvisioningOperation,
    ProvisioningStatus,
)
from app.schemas.provisioning import (
    PBACProviderCreate,
    PBACProviderUpdate,
)
from app.services.translation_service import TranslationService

logger = structlog.get_logger(__name__)


class ProvisioningService:
    """Service for provisioning policies to PBAC platforms."""

    def __init__(self, db: Session):
        """Initialize the provisioning service."""
        self.db = db
        self.translation_service = TranslationService()

    async def create_provider(
        self, provider_data: PBACProviderCreate, tenant_id: str
    ) -> PBACProvider:
        """
        Create a new PBAC provider configuration.

        Args:
            provider_data: The provider configuration
            tenant_id: The tenant ID

        Returns:
            PBACProvider: The created provider
        """
        logger.info("creating_pbac_provider", tenant_id=tenant_id, provider_type=provider_data.provider_type)

        provider = PBACProvider(
            tenant_id=tenant_id,
            provider_type=provider_data.provider_type,
            name=provider_data.name,
            endpoint_url=provider_data.endpoint_url,
            api_key=provider_data.api_key,
            configuration=provider_data.configuration,
        )

        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)

        logger.info("provider_created", provider_id=provider.provider_id)
        return provider

    async def update_provider(
        self, provider_id: int, provider_data: PBACProviderUpdate, tenant_id: str
    ) -> PBACProvider | None:
        """
        Update a PBAC provider configuration.

        Args:
            provider_id: The provider ID
            provider_data: The update data
            tenant_id: The tenant ID

        Returns:
            Optional[PBACProvider]: The updated provider or None if not found
        """
        logger.info("updating_pbac_provider", provider_id=provider_id, tenant_id=tenant_id)

        # Fetch provider
        stmt = select(PBACProvider).where(
            PBACProvider.provider_id == provider_id,
            PBACProvider.tenant_id == tenant_id,
        )
        result = self.db.execute(stmt)
        provider = result.scalar_one_or_none()

        if not provider:
            logger.warning("provider_not_found", provider_id=provider_id)
            return None

        # Update fields
        if provider_data.name is not None:
            provider.name = provider_data.name
        if provider_data.endpoint_url is not None:
            provider.endpoint_url = provider_data.endpoint_url
        if provider_data.api_key is not None:
            provider.api_key = provider_data.api_key
        if provider_data.configuration is not None:
            provider.configuration = provider_data.configuration

        self.db.commit()
        self.db.refresh(provider)

        logger.info("provider_updated", provider_id=provider.provider_id)
        return provider

    async def get_providers(self, tenant_id: str) -> list[PBACProvider]:
        """
        Get all PBAC providers for a tenant.

        Args:
            tenant_id: The tenant ID

        Returns:
            list[PBACProvider]: List of providers
        """
        stmt = select(PBACProvider).where(PBACProvider.tenant_id == tenant_id)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_provider(self, provider_id: int, tenant_id: str) -> bool:
        """
        Delete a PBAC provider.

        Args:
            provider_id: The provider ID
            tenant_id: The tenant ID

        Returns:
            bool: True if deleted, False if not found
        """
        logger.info("deleting_pbac_provider", provider_id=provider_id, tenant_id=tenant_id)

        stmt = select(PBACProvider).where(
            PBACProvider.provider_id == provider_id,
            PBACProvider.tenant_id == tenant_id,
        )
        result = self.db.execute(stmt)
        provider = result.scalar_one_or_none()

        if not provider:
            logger.warning("provider_not_found", provider_id=provider_id)
            return False

        self.db.delete(provider)
        self.db.commit()

        logger.info("provider_deleted", provider_id=provider_id)
        return True

    async def provision_policy(
        self, policy_id: int, provider_id: int, tenant_id: str
    ) -> ProvisioningOperation:
        """
        Provision a single policy to a PBAC platform.

        Args:
            policy_id: The policy ID
            provider_id: The provider ID
            tenant_id: The tenant ID

        Returns:
            ProvisioningOperation: The provisioning operation

        Raises:
            ValueError: If policy or provider not found
        """
        logger.info(
            "provisioning_policy",
            policy_id=policy_id,
            provider_id=provider_id,
            tenant_id=tenant_id,
        )

        # Fetch policy
        policy_stmt = select(Policy).where(
            Policy.policy_id == policy_id,
            Policy.tenant_id == tenant_id,
        )
        policy_result = self.db.execute(policy_stmt)
        policy = policy_result.scalar_one_or_none()

        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        # Fetch provider
        provider_stmt = select(PBACProvider).where(
            PBACProvider.provider_id == provider_id,
            PBACProvider.tenant_id == tenant_id,
        )
        provider_result = self.db.execute(provider_stmt)
        provider = provider_result.scalar_one_or_none()

        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        # Create provisioning operation
        operation = ProvisioningOperation(
            tenant_id=tenant_id,
            provider_id=provider_id,
            policy_id=policy_id,
            status=ProvisioningStatus.IN_PROGRESS,
        )

        self.db.add(operation)
        self.db.commit()
        self.db.refresh(operation)

        try:
            # Translate policy to target format
            if provider.provider_type == ProviderType.OPA:
                translated_policy = await self.translation_service.translate_to_rego(policy)
            elif provider.provider_type == ProviderType.AWS_VERIFIED_PERMISSIONS:
                translated_policy = await self.translation_service.translate_to_cedar(policy)
            else:
                translated_policy = await self.translation_service.translate_to_json(policy)

            operation.translated_policy = translated_policy

            # Push to PBAC platform
            await self._push_to_platform(provider, policy, translated_policy)

            # Mark as successful
            operation.status = ProvisioningStatus.SUCCESS
            operation.completed_at = datetime.utcnow()

            logger.info(
                "provisioning_successful",
                operation_id=operation.operation_id,
                policy_id=policy_id,
            )

        except Exception as e:
            logger.error(
                "provisioning_failed",
                operation_id=operation.operation_id,
                error=str(e),
            )
            operation.status = ProvisioningStatus.FAILED
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(operation)

        return operation

    async def bulk_provision_policies(
        self, policy_ids: list[int], provider_id: int, tenant_id: str
    ) -> list[ProvisioningOperation]:
        """
        Provision multiple policies to a PBAC platform.

        Args:
            policy_ids: List of policy IDs
            provider_id: The provider ID
            tenant_id: The tenant ID

        Returns:
            list[ProvisioningOperation]: List of provisioning operations
        """
        logger.info(
            "bulk_provisioning_policies",
            policy_count=len(policy_ids),
            provider_id=provider_id,
            tenant_id=tenant_id,
        )

        operations = []
        for policy_id in policy_ids:
            try:
                operation = await self.provision_policy(policy_id, provider_id, tenant_id)
                operations.append(operation)
            except Exception as e:
                logger.error(
                    "bulk_provisioning_error",
                    policy_id=policy_id,
                    error=str(e),
                )
                # Create failed operation
                operation = ProvisioningOperation(
                    tenant_id=tenant_id,
                    provider_id=provider_id,
                    policy_id=policy_id,
                    status=ProvisioningStatus.FAILED,
                    error_message=str(e),
                    completed_at=datetime.utcnow(),
                )
                self.db.add(operation)
                self.db.commit()
                self.db.refresh(operation)
                operations.append(operation)

        logger.info(
            "bulk_provisioning_complete",
            total=len(operations),
            successful=len([op for op in operations if op.status == ProvisioningStatus.SUCCESS]),
            failed=len([op for op in operations if op.status == ProvisioningStatus.FAILED]),
        )

        return operations

    async def get_operations(
        self, tenant_id: str, provider_id: int | None = None
    ) -> list[ProvisioningOperation]:
        """
        Get provisioning operations for a tenant.

        Args:
            tenant_id: The tenant ID
            provider_id: Optional provider ID filter

        Returns:
            list[ProvisioningOperation]: List of operations
        """
        stmt = select(ProvisioningOperation).where(
            ProvisioningOperation.tenant_id == tenant_id
        )

        if provider_id is not None:
            stmt = stmt.where(ProvisioningOperation.provider_id == provider_id)

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def _push_to_platform(
        self, provider: PBACProvider, policy: Policy, translated_policy: str
    ) -> None:
        """
        Push the translated policy to the PBAC platform.

        Args:
            provider: The PBAC provider
            policy: The original policy
            translated_policy: The translated policy

        Raises:
            Exception: If push fails
        """
        if provider.provider_type == ProviderType.OPA:
            await self._push_to_opa(provider, policy, translated_policy)
        elif provider.provider_type == ProviderType.AWS_VERIFIED_PERMISSIONS:
            await self._push_to_aws_verified_permissions(provider, policy, translated_policy)
        else:
            logger.warning(
                "unsupported_provider_type",
                provider_type=provider.provider_type,
            )
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")

    async def _push_to_opa(
        self, provider: PBACProvider, policy: Policy, rego_policy: str
    ) -> None:
        """
        Push Rego policy to OPA via REST API.

        Args:
            provider: The OPA provider
            policy: The original policy
            rego_policy: The Rego policy

        Raises:
            Exception: If push fails
        """
        logger.info(
            "pushing_to_opa",
            endpoint=provider.endpoint_url,
            policy_id=policy.id,
        )

        # OPA policy path: /v1/policies/{policy_id}
        policy_path = f"policy_{policy.id}"
        url = f"{provider.endpoint_url.rstrip('/')}/v1/policies/{policy_path}"

        headers = {"Content-Type": "text/plain"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                content=rego_policy,
                headers=headers,
                timeout=30.0,
            )

            if response.status_code not in (200, 201):
                error_msg = f"OPA returned status {response.status_code}: {response.text}"
                logger.error("opa_push_failed", error=error_msg)
                raise Exception(error_msg)

        logger.info("opa_push_successful", policy_id=policy.id)

    async def _push_to_aws_verified_permissions(
        self, provider: PBACProvider, policy: Policy, cedar_policy: str
    ) -> None:
        """
        Push Cedar policy to AWS Verified Permissions.

        Args:
            provider: The AWS provider
            policy: The original policy
            cedar_policy: The Cedar policy

        Raises:
            Exception: If push fails
        """
        # This is a placeholder - actual AWS SDK integration would go here
        logger.info(
            "pushing_to_aws_verified_permissions",
            endpoint=provider.endpoint_url,
            policy_id=policy.id,
        )
        # TODO: Implement AWS Verified Permissions SDK integration
        raise NotImplementedError("AWS Verified Permissions integration not yet implemented")
