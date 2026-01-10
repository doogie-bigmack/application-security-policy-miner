"""API endpoints for duplicate policy detection."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.schemas.duplicate import (
    ConsolidateRequest,
    ConsolidateResponse,
    DuplicateGroup,
    DuplicateStatistics,
)
from app.services.duplicate_detection_service import duplicate_detection_service

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/statistics", response_model=DuplicateStatistics)
def get_duplicate_statistics(
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
    min_similarity: float = Query(0.95, ge=0.0, le=1.0, description="Minimum similarity threshold"),
):
    """Get statistics about duplicate policies across applications.

    Args:
        db: Database session
        tenant_id: Tenant ID from authentication
        min_similarity: Minimum similarity threshold (0-1)

    Returns:
        Statistics about duplicate policies

    """
    try:
        stats = duplicate_detection_service.get_duplicate_statistics(
            db=db,
            tenant_id=tenant_id,
            min_similarity=min_similarity,
        )

        logger.info("duplicate_statistics_retrieved", stats=stats)
        return stats

    except Exception as e:
        logger.error("error_getting_duplicate_statistics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[DuplicateGroup])
def find_duplicates(
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
    min_similarity: float = Query(0.95, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    application_ids: list[int] | None = Query(None, description="Filter by application IDs"),
):
    """Find duplicate policies across applications.

    Args:
        db: Database session
        tenant_id: Tenant ID from authentication
        min_similarity: Minimum similarity threshold (0-1)
        application_ids: Optional list of application IDs to filter by

    Returns:
        List of duplicate groups with similar policies

    """
    try:
        duplicate_groups = duplicate_detection_service.find_duplicates_across_applications(
            db=db,
            tenant_id=tenant_id,
            min_similarity=min_similarity,
            application_ids=application_ids,
        )

        logger.info(
            "duplicates_found",
            count=len(duplicate_groups),
            total_policies=sum(len(g["policies"]) for g in duplicate_groups),
        )

        # Convert to response schema
        response = []
        for group in duplicate_groups:
            response.append(
                DuplicateGroup(
                    policy_ids=group["policy_ids"],
                    similarity_score=group["similarity_score"],
                    application_count=group["application_count"],
                    potential_savings=group["potential_savings"],
                    sample_policy=group["sample_policy"],
                    applications=[
                        {
                            "id": app.id,
                            "name": app.name,
                            "business_unit_id": app.business_unit_id,
                        }
                        for app in group["applications"]
                    ],
                )
            )

        return response

    except Exception as e:
        logger.error("error_finding_duplicates", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consolidate", response_model=ConsolidateResponse)
def consolidate_duplicates(
    request: ConsolidateRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Consolidate a group of duplicate policies.

    Keeps one policy and removes the others.

    Args:
        request: Consolidation request with policy IDs
        db: Database session
        tenant_id: Tenant ID from authentication

    Returns:
        Result of consolidation

    """
    try:
        result = duplicate_detection_service.consolidate_duplicate_group(
            db=db,
            policy_ids=request.policy_ids,
            keep_policy_id=request.keep_policy_id,
        )

        logger.info(
            "duplicates_consolidated",
            kept_policy_id=result["kept_policy_id"],
            removed_count=result["removed_count"],
        )

        return ConsolidateResponse(
            kept_policy_id=result["kept_policy_id"],
            removed_policy_ids=result["removed_policy_ids"],
            removed_count=result["removed_count"],
        )

    except ValueError as e:
        logger.error("invalid_consolidation_request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("error_consolidating_duplicates", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
