"""Provisioning service for pushing policies to PBAC platforms."""

import json
from datetime import datetime

import boto3
import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.test_mode import is_test_mode
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
        self.test_mode = is_test_mode()
        if self.test_mode:
            logger.info("provisioning_service_initialized_in_test_mode")

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
            Policy.id == policy_id,
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
        # In TEST_MODE, skip actual API calls
        if self.test_mode:
            logger.info(
                "test_mode_push_skipped",
                provider_type=provider.provider_type,
                policy_id=policy.id,
                translated_policy_length=len(translated_policy),
            )
            return

        if provider.provider_type == ProviderType.OPA:
            await self._push_to_opa(provider, policy, translated_policy)
        elif provider.provider_type == ProviderType.AWS_VERIFIED_PERMISSIONS:
            await self._push_to_aws_verified_permissions(provider, policy, translated_policy)
        elif provider.provider_type == ProviderType.AXIOMATICS:
            await self._push_to_axiomatics(provider, policy, translated_policy)
        elif provider.provider_type == ProviderType.PLAINID:
            await self._push_to_plainid(provider, policy, translated_policy)
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
        logger.info(
            "pushing_to_aws_verified_permissions",
            region=provider.endpoint_url,
            policy_id=policy.id,
        )

        # Parse provider configuration
        # Expected format: {"policy_store_id": "...", "aws_access_key_id": "...", "aws_secret_access_key": "..."}
        config = json.loads(provider.configuration) if provider.configuration else {}

        policy_store_id = config.get("policy_store_id")
        if not policy_store_id:
            raise ValueError("AWS Verified Permissions requires policy_store_id in configuration")

        # Initialize AWS Verified Permissions client
        # Region is stored in endpoint_url field
        region = provider.endpoint_url

        client_kwargs = {"region_name": region}

        # Use explicit credentials if provided, otherwise use IAM role/profile
        if config.get("aws_access_key_id") and config.get("aws_secret_access_key"):
            client_kwargs["aws_access_key_id"] = config["aws_access_key_id"]
            client_kwargs["aws_secret_access_key"] = config["aws_secret_access_key"]

        client = boto3.client("verifiedpermissions", **client_kwargs)

        try:
            # Create or update policy in AWS Verified Permissions
            # Policy ID is derived from our internal policy ID
            policy_id = f"policy-{policy.id}"

            # Build the policy definition
            policy_definition = {
                "static": {
                    "statement": cedar_policy,
                    "description": policy.description or f"Policy for {policy.subject} accessing {policy.resource}",
                }
            }

            # Try to update existing policy first
            try:
                response = client.update_policy(
                    policyStoreId=policy_store_id,
                    policyId=policy_id,
                    definition=policy_definition,
                )
                logger.info(
                    "aws_policy_updated",
                    policy_id=policy_id,
                    policy_version=response.get("policyVersion"),
                )
            except client.exceptions.ResourceNotFoundException:
                # Policy doesn't exist, create it
                response = client.create_policy(
                    policyStoreId=policy_store_id,
                    clientToken=f"policy-miner-{policy.id}",
                    definition=policy_definition,
                )
                logger.info(
                    "aws_policy_created",
                    policy_id=response.get("policyId"),
                    policy_version=response.get("policyVersion"),
                )

        except Exception as e:
            error_msg = f"AWS Verified Permissions error: {str(e)}"
            logger.error("aws_push_failed", error=error_msg, policy_id=policy.id)
            raise Exception(error_msg) from e

        logger.info("aws_push_successful", policy_id=policy.id)

    async def _push_to_axiomatics(
        self, provider: PBACProvider, policy: Policy, translated_policy: str
    ) -> None:
        """
        Push policy to Axiomatics via REST API.

        Args:
            provider: The Axiomatics provider
            policy: The original policy
            translated_policy: The translated policy (XACML or JSON)

        Raises:
            Exception: If push fails
        """
        logger.info(
            "pushing_to_axiomatics",
            endpoint=provider.endpoint_url,
            policy_id=policy.id,
        )

        # Parse provider configuration
        # Expected format: {"auth_type": "bearer", "additional_headers": {...}}
        config = json.loads(provider.configuration) if provider.configuration else {}

        # Build policy payload for Axiomatics API
        # Axiomatics typically uses XACML or custom JSON format
        policy_id = f"policy-{policy.id}"

        payload = {
            "policyId": policy_id,
            "name": f"Policy for {policy.subject} accessing {policy.resource}",
            "description": policy.description or f"Policy {policy.id}",
            "content": translated_policy,
            "enabled": True,
            "metadata": {
                "source": "policy_miner",
                "subject": policy.subject,
                "resource": policy.resource,
                "action": policy.action,
            }
        }

        # Build headers
        headers = {"Content-Type": "application/json"}

        # Add authentication
        if provider.api_key:
            auth_type = config.get("auth_type", "bearer")
            if auth_type.lower() == "bearer":
                headers["Authorization"] = f"Bearer {provider.api_key}"
            elif auth_type.lower() == "apikey":
                headers["X-API-Key"] = provider.api_key
            else:
                headers["Authorization"] = f"Bearer {provider.api_key}"

        # Add any additional headers from configuration
        if "additional_headers" in config:
            headers.update(config["additional_headers"])

        # Axiomatics REST API: POST /api/policies or PUT /api/policies/{policy_id}
        url = f"{provider.endpoint_url.rstrip('/')}/api/policies/{policy_id}"

        async with httpx.AsyncClient() as client:
            # Try PUT first (update), then POST if not found
            try:
                response = await client.put(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code == 404:
                    # Policy doesn't exist, create it with POST
                    create_url = f"{provider.endpoint_url.rstrip('/')}/api/policies"
                    response = await client.post(
                        create_url,
                        json=payload,
                        headers=headers,
                        timeout=30.0,
                    )

                if response.status_code not in (200, 201, 204):
                    error_msg = f"Axiomatics returned status {response.status_code}: {response.text}"
                    logger.error("axiomatics_push_failed", error=error_msg)
                    raise Exception(error_msg)

            except httpx.RequestError as e:
                error_msg = f"Axiomatics connection error: {str(e)}"
                logger.error("axiomatics_connection_error", error=error_msg)
                raise Exception(error_msg) from e

        logger.info("axiomatics_push_successful", policy_id=policy.id)

    async def _push_to_plainid(
        self, provider: PBACProvider, policy: Policy, translated_policy: str
    ) -> None:
        """
        Push policy to PlainID via REST API.

        Args:
            provider: The PlainID provider
            policy: The original policy
            translated_policy: The translated policy (JSON format)

        Raises:
            Exception: If push fails
        """
        logger.info(
            "pushing_to_plainid",
            endpoint=provider.endpoint_url,
            policy_id=policy.id,
        )

        # Parse provider configuration
        # Expected format: {"tenant_id": "...", "environment": "production"}
        config = json.loads(provider.configuration) if provider.configuration else {}

        # Build policy payload for PlainID API
        # PlainID uses a proprietary JSON format for policies
        policy_id = f"policy-{policy.id}"

        payload = {
            "id": policy_id,
            "name": f"Policy for {policy.subject} accessing {policy.resource}",
            "description": policy.description or f"Mined policy {policy.id}",
            "status": "active",
            "policy": json.loads(translated_policy) if translated_policy.startswith("{") else {"content": translated_policy},
            "tags": ["policy_miner", "automated"],
            "metadata": {
                "source": "policy_miner",
                "original_policy_id": str(policy.id),
                "subject": policy.subject,
                "resource": policy.resource,
                "action": policy.action,
                "risk_score": policy.risk_score,
            }
        }

        # Add tenant ID if provided
        if "tenant_id" in config:
            payload["tenantId"] = config["tenant_id"]

        # Build headers
        headers = {"Content-Type": "application/json"}

        # Add authentication (PlainID uses API key authentication)
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        # PlainID REST API: POST /api/v1/policies or PUT /api/v1/policies/{policy_id}
        url = f"{provider.endpoint_url.rstrip('/')}/api/v1/policies/{policy_id}"

        async with httpx.AsyncClient() as client:
            # Try PUT first (update existing policy)
            try:
                response = await client.put(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code == 404:
                    # Policy doesn't exist, create it with POST
                    create_url = f"{provider.endpoint_url.rstrip('/')}/api/v1/policies"
                    response = await client.post(
                        create_url,
                        json=payload,
                        headers=headers,
                        timeout=30.0,
                    )

                if response.status_code not in (200, 201, 204):
                    error_msg = f"PlainID returned status {response.status_code}: {response.text}"
                    logger.error("plainid_push_failed", error=error_msg)
                    raise Exception(error_msg)

            except httpx.RequestError as e:
                error_msg = f"PlainID connection error: {str(e)}"
                logger.error("plainid_connection_error", error=error_msg)
                raise Exception(error_msg) from e

        logger.info("plainid_push_successful", policy_id=policy.id)
