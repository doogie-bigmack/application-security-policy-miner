"""API endpoints for role normalization."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.models.role_mapping import MappingStatus, RoleMapping
from app.schemas.role_mapping import (
    RoleDiscoveryRequest,
    RoleDiscoveryResponse,
    RoleMappingApproval,
    RoleMappingCreate,
    RoleMappingResponse,
    RoleMappingStats,
)
from app.services.normalization_service import NormalizationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/discover", response_model=list[RoleDiscoveryResponse])
async def discover_role_variations(
    request: RoleDiscoveryRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> list[RoleDiscoveryResponse]:
    """Discover role variations across applications using Claude Agent SDK.

    This endpoint analyzes all policies across applications to find role names
    that are semantically equivalent but named differently. Uses AI to determine
    if roles like 'admin', 'administrator', and 'sysadmin' should be normalized.
    """
    service = NormalizationService()

    try:
        discovered_groups = await service.discover_role_variations(
            db=db,
            tenant_id=tenant_id,
            min_applications=request.min_applications,
        )

        return [
            RoleDiscoveryResponse(
                roles=group["roles"],
                standard_role=group["standard_role"],
                confidence=group["confidence"],
                reasoning=group["reasoning"],
                application_count=group["application_count"],
                applications=group["applications"],
                apps_by_role=group["apps_by_role"],
            )
            for group in discovered_groups
        ]

    except Exception as e:
        logger.error(f"Error discovering role variations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/mappings", response_model=RoleMappingResponse)
async def create_role_mapping(
    mapping: RoleMappingCreate,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> RoleMappingResponse:
    """Create a new role mapping suggestion.

    Role mappings are created in SUGGESTED status and must be approved before
    being applied to policies.
    """
    service = NormalizationService()

    try:
        created_mapping = await service.create_role_mapping(
            db=db,
            tenant_id=tenant_id or "default",
            standard_role=mapping.standard_role,
            variant_roles=mapping.variant_roles,
            affected_applications=mapping.affected_applications,
            confidence_score=mapping.confidence_score,
            reasoning=mapping.reasoning or "",
        )

        return RoleMappingResponse.model_validate(created_mapping)

    except Exception as e:
        logger.error(f"Error creating role mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/mappings", response_model=list[RoleMappingResponse])
def get_role_mappings(
    status: MappingStatus | None = None,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> list[RoleMappingResponse]:
    """Get all role mappings, optionally filtered by status."""
    query = db.query(RoleMapping)

    if tenant_id:
        query = query.filter(RoleMapping.tenant_id == tenant_id)

    if status:
        query = query.filter(RoleMapping.status == status)

    mappings = query.order_by(RoleMapping.created_at.desc()).all()

    return [RoleMappingResponse.model_validate(m) for m in mappings]


@router.get("/mappings/{mapping_id}", response_model=RoleMappingResponse)
def get_role_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> RoleMappingResponse:
    """Get a specific role mapping by ID."""
    query = db.query(RoleMapping).filter(RoleMapping.id == mapping_id)

    if tenant_id:
        query = query.filter(RoleMapping.tenant_id == tenant_id)

    mapping = query.first()

    if not mapping:
        raise HTTPException(status_code=404, detail="Role mapping not found")

    return RoleMappingResponse.model_validate(mapping)


@router.post("/mappings/{mapping_id}/apply", response_model=dict)
async def apply_role_mapping(
    mapping_id: int,
    approval: RoleMappingApproval,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict:
    """Apply an approved role mapping to policies.

    This will update all affected policies to use the standard role name.
    """
    service = NormalizationService()

    # Verify mapping exists and belongs to tenant
    mapping = db.query(RoleMapping).filter(RoleMapping.id == mapping_id).first()

    if not mapping:
        raise HTTPException(status_code=404, detail="Role mapping not found")

    if tenant_id and mapping.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        updated_count = await service.apply_role_mapping(
            db=db,
            mapping_id=mapping_id,
            approved_by=approval.approved_by,
        )

        return {
            "success": True,
            "mapping_id": mapping_id,
            "policies_updated": updated_count,
            "message": f"Applied role mapping: {mapping.standard_role} "
            f"(updated {updated_count} policies)",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error applying role mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/mappings/{mapping_id}")
def delete_role_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict:
    """Delete a role mapping (only if not yet applied)."""
    mapping = db.query(RoleMapping).filter(RoleMapping.id == mapping_id).first()

    if not mapping:
        raise HTTPException(status_code=404, detail="Role mapping not found")

    if tenant_id and mapping.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if mapping.status == MappingStatus.APPLIED:
        raise HTTPException(status_code=400, detail="Cannot delete applied mapping")

    db.delete(mapping)
    db.commit()

    return {"success": True, "message": f"Deleted role mapping {mapping_id}"}


@router.get("/stats", response_model=RoleMappingStats)
def get_normalization_stats(
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> RoleMappingStats:
    """Get statistics for role normalization."""
    query = db.query(RoleMapping)

    if tenant_id:
        query = query.filter(RoleMapping.tenant_id == tenant_id)

    all_mappings = query.all()

    total_mappings = len(all_mappings)
    suggested = sum(1 for m in all_mappings if m.status == MappingStatus.SUGGESTED)
    approved = sum(1 for m in all_mappings if m.status == MappingStatus.APPROVED)
    applied = sum(1 for m in all_mappings if m.status == MappingStatus.APPLIED)

    total_policies_normalized = sum(
        m.affected_policy_count for m in all_mappings if m.status == MappingStatus.APPLIED
    )

    return RoleMappingStats(
        total_mappings=total_mappings,
        suggested=suggested,
        approved=approved,
        applied=applied,
        total_policies_normalized=total_policies_normalized,
    )
