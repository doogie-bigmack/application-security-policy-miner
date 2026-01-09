"""Provisioning API endpoints."""


import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.schemas.provisioning import (
    BulkProvisioningRequest,
    PBACProvider,
    PBACProviderCreate,
    PBACProviderUpdate,
    ProvisioningOperation,
    ProvisioningOperationCreate,
)
from app.services.provisioning_service import ProvisioningService

logger = structlog.get_logger(__name__)

router = APIRouter()


def get_effective_tenant_id(tenant_id: str | None) -> str:
    """Get effective tenant ID, using default if not authenticated."""
    return tenant_id or "default"


@router.post("/providers/", response_model=PBACProvider, status_code=201)
async def create_provider(
    provider: PBACProviderCreate,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    Create a new PBAC provider configuration.
    """
    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"
    logger.info("api_create_provider", tenant_id=effective_tenant_id)

    service = ProvisioningService(db)
    return await service.create_provider(provider, effective_tenant_id)


@router.get("/providers/", response_model=list[PBACProvider])
async def list_providers(
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    List all PBAC providers for the tenant.
    """
    logger.info("api_list_providers", tenant_id=tenant_id)

    service = ProvisioningService(db)
    effective_tenant_id = get_effective_tenant_id(tenant_id)
    return await service.get_providers(effective_tenant_id)


@router.get("/providers/{provider_id}", response_model=PBACProvider)
async def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    Get a specific PBAC provider.
    """
    logger.info("api_get_provider", provider_id=provider_id, tenant_id=tenant_id)

    service = ProvisioningService(db)
    effective_tenant_id = get_effective_tenant_id(tenant_id)
    providers = await service.get_providers(effective_tenant_id)
    provider = next((p for p in providers if p.provider_id == provider_id), None)

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    return provider


@router.put("/providers/{provider_id}", response_model=PBACProvider)
async def update_provider(
    provider_id: int,
    provider_data: PBACProviderUpdate,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    Update a PBAC provider configuration.
    """
    logger.info("api_update_provider", provider_id=provider_id, tenant_id=tenant_id)

    service = ProvisioningService(db)
    effective_tenant_id = get_effective_tenant_id(tenant_id)
    provider = await service.update_provider(provider_id, provider_data, effective_tenant_id)

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    return provider


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    Delete a PBAC provider.
    """
    logger.info("api_delete_provider", provider_id=provider_id, tenant_id=tenant_id)

    service = ProvisioningService(db)
    effective_tenant_id = get_effective_tenant_id(tenant_id)
    deleted = await service.delete_provider(provider_id, effective_tenant_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Provider not found")


@router.post("/provision/", response_model=ProvisioningOperation, status_code=201)
async def provision_policy(
    request: ProvisioningOperationCreate,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    Provision a single policy to a PBAC platform.
    """
    logger.info(
        "api_provision_policy",
        policy_id=request.policy_id,
        provider_id=request.provider_id,
        tenant_id=tenant_id,
    )

    service = ProvisioningService(db)

    try:
        effective_tenant_id = get_effective_tenant_id(tenant_id)
        operation = await service.provision_policy(
            request.policy_id, request.provider_id, effective_tenant_id
        )
        return operation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("provisioning_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/provision/bulk/", response_model=list[ProvisioningOperation], status_code=201)
async def bulk_provision_policies(
    request: BulkProvisioningRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    Provision multiple policies to a PBAC platform in bulk.
    """
    logger.info(
        "api_bulk_provision_policies",
        policy_count=len(request.policy_ids),
        provider_id=request.provider_id,
        tenant_id=tenant_id,
    )

    service = ProvisioningService(db)
    effective_tenant_id = get_effective_tenant_id(tenant_id)
    operations = await service.bulk_provision_policies(
        request.policy_ids, request.provider_id, effective_tenant_id
    )

    return operations


@router.get("/operations/", response_model=list[ProvisioningOperation])
async def list_operations(
    provider_id: int | None = None,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    List provisioning operations for the tenant.
    """
    logger.info("api_list_operations", tenant_id=tenant_id, provider_id=provider_id)

    service = ProvisioningService(db)
    effective_tenant_id = get_effective_tenant_id(tenant_id)
    operations = await service.get_operations(effective_tenant_id, provider_id)

    return operations
