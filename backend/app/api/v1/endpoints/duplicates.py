"""API endpoints for duplicate policy detection and management."""


import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.duplicate_policy_group import DuplicateGroupStatus
from app.schemas.duplicate_policy_group import (
    ConsolidateRequest,
    DismissRequest,
    DuplicateDetectionRequest,
    DuplicateDetectionResponse,
    DuplicatePolicyGroupMemberWithPolicy,
    DuplicatePolicyGroupResponse,
    DuplicatePolicyGroupWithPolicies,
)
from app.services.deduplication_service import deduplication_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/detect/", response_model=DuplicateDetectionResponse)
def detect_duplicates(
    request: DuplicateDetectionRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> DuplicateDetectionResponse:
    """Detect duplicate policies across applications.

    This endpoint scans all policies and groups those that are semantically very similar
    (likely duplicates). Each group can then be reviewed and consolidated.

    Args:
        request: Detection parameters (min_similarity, repository_id)
        db: Database session
        tenant_id: Tenant ID from authentication

    Returns:
        Detection results with created groups

    """
    logger.info(
        "detect_duplicates_request",
        min_similarity=request.min_similarity,
        repository_id=request.repository_id,
        tenant_id=tenant_id,
    )

    try:
        groups = deduplication_service.detect_duplicates(
            db=db,
            min_similarity=request.min_similarity,
            tenant_id=tenant_id,
            repository_id=request.repository_id,
        )

        # Count total policies across all groups
        total_policies = sum(group.policy_count for group in groups)

        return DuplicateDetectionResponse(
            groups_created=len(groups),
            policies_in_groups=total_policies,
            groups=[DuplicatePolicyGroupResponse.model_validate(group) for group in groups],
        )

    except Exception as e:
        logger.error("detect_duplicates_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to detect duplicates: {str(e)}")


@router.get("/", response_model=list[DuplicatePolicyGroupResponse])
def list_duplicate_groups(
    status: DuplicateGroupStatus | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> list[DuplicatePolicyGroupResponse]:
    """List all duplicate policy groups.

    Args:
        status: Optional status filter
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        tenant_id: Tenant ID from authentication

    Returns:
        List of duplicate policy groups

    """
    logger.info(
        "list_duplicate_groups",
        status=status,
        skip=skip,
        limit=limit,
        tenant_id=tenant_id,
    )

    try:
        groups = deduplication_service.get_duplicate_groups(
            db=db,
            tenant_id=tenant_id,
            status=status,
            skip=skip,
            limit=limit,
        )

        return [DuplicatePolicyGroupResponse.model_validate(group) for group in groups]

    except Exception as e:
        logger.error("list_duplicate_groups_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list duplicate groups: {str(e)}")


@router.get("/{group_id}/", response_model=DuplicatePolicyGroupWithPolicies)
def get_duplicate_group(
    group_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> DuplicatePolicyGroupWithPolicies:
    """Get a duplicate group with all its policies.

    Args:
        group_id: ID of the duplicate group
        db: Database session
        tenant_id: Tenant ID from authentication

    Returns:
        Duplicate group with all policies and similarity scores

    Raises:
        HTTPException: If group not found

    """
    logger.info("get_duplicate_group", group_id=group_id, tenant_id=tenant_id)

    try:
        result = deduplication_service.get_duplicate_group_with_policies(
            db=db,
            group_id=group_id,
        )

        if not result:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")

        group, policies_with_scores = result

        # Verify tenant access
        if tenant_id and group.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")

        # Build response
        members = [
            DuplicatePolicyGroupMemberWithPolicy(
                policy_id=policy.id,
                similarity_to_group=score,
                policy=policy,
            )
            for policy, score in policies_with_scores
        ]

        response = DuplicatePolicyGroupWithPolicies.model_validate(group)
        response.policies = members

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_duplicate_group_failed", group_id=group_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get duplicate group: {str(e)}")


@router.put("/{group_id}/consolidate/", response_model=DuplicatePolicyGroupResponse)
def consolidate_duplicate_group(
    group_id: int,
    request: ConsolidateRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> DuplicatePolicyGroupResponse:
    """Consolidate a duplicate group by selecting one policy as the centralized version.

    Args:
        group_id: ID of the duplicate group
        request: Consolidation request with policy ID and notes
        db: Database session
        tenant_id: Tenant ID from authentication

    Returns:
        Updated duplicate group

    Raises:
        HTTPException: If group not found or policy not in group

    """
    logger.info(
        "consolidate_duplicate_group",
        group_id=group_id,
        consolidated_policy_id=request.consolidated_policy_id,
        tenant_id=tenant_id,
    )

    try:
        group = deduplication_service.consolidate_duplicates(
            db=db,
            group_id=group_id,
            consolidated_policy_id=request.consolidated_policy_id,
            notes=request.notes,
        )

        # Verify tenant access
        if tenant_id and group.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")

        return DuplicatePolicyGroupResponse.model_validate(group)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("consolidate_duplicate_group_failed", group_id=group_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to consolidate duplicates: {str(e)}")


@router.put("/{group_id}/dismiss/", response_model=DuplicatePolicyGroupResponse)
def dismiss_duplicate_group(
    group_id: int,
    request: DismissRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> DuplicatePolicyGroupResponse:
    """Dismiss a duplicate group as a false positive.

    Args:
        group_id: ID of the duplicate group
        request: Dismiss request with notes
        db: Database session
        tenant_id: Tenant ID from authentication

    Returns:
        Updated duplicate group

    Raises:
        HTTPException: If group not found

    """
    logger.info("dismiss_duplicate_group", group_id=group_id, tenant_id=tenant_id)

    try:
        group = deduplication_service.dismiss_duplicates(
            db=db,
            group_id=group_id,
            notes=request.notes,
        )

        # Verify tenant access
        if tenant_id and group.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")

        return DuplicatePolicyGroupResponse.model_validate(group)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("dismiss_duplicate_group_failed", group_id=group_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to dismiss duplicates: {str(e)}")


@router.delete("/{group_id}/")
def delete_duplicate_group(
    group_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict:
    """Delete a duplicate group.

    Args:
        group_id: ID of the duplicate group
        db: Database session
        tenant_id: Tenant ID from authentication

    Returns:
        Success message

    Raises:
        HTTPException: If group not found

    """
    logger.info("delete_duplicate_group", group_id=group_id, tenant_id=tenant_id)

    try:
        # Get the group to verify tenant access
        result = deduplication_service.get_duplicate_group_with_policies(
            db=db,
            group_id=group_id,
        )

        if not result:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")

        group, _ = result

        # Verify tenant access
        if tenant_id and group.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=f"Duplicate group {group_id} not found")

        # Delete the group (cascade will handle members)
        db.delete(group)
        db.commit()

        logger.info("duplicate_group_deleted", group_id=group_id)

        return {"message": f"Duplicate group {group_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_duplicate_group_failed", group_id=group_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete duplicate group: {str(e)}")
