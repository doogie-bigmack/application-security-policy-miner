"""Policy endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.policy import Policy
from app.schemas.policy import (
    PolicyListResponse,
    PolicyResponse,
    PolicyUpdate,
    ScanRequest,
    ScanResponse,
)
from app.services.scan_service import ScanService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/scan", response_model=ScanResponse)
async def scan_repository(
    request: ScanRequest,
    db: Session = Depends(get_db),
) -> ScanResponse:
    """
    Scan a repository and extract authorization policies.

    Args:
        request: Scan request with repository ID
        db: Database session

    Returns:
        Scan response with number of policies extracted
    """
    logger.info("Starting scan for repository %d", request.repository_id)

    try:
        scan_service = ScanService(db)
        policies_count = await scan_service.scan_repository(request.repository_id)

        return ScanResponse(
            message=f"Successfully scanned repository and extracted {policies_count} policies",
            repository_id=request.repository_id,
            policies_extracted=policies_count,
        )

    except ValueError as e:
        logger.error("Scan failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.exception("Scan failed with unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {e!s}",
        ) from e


@router.get("/", response_model=PolicyListResponse)
def list_policies(
    repository_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> PolicyListResponse:
    """
    List policies with optional filtering.

    Args:
        repository_id: Optional repository ID to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of policies
    """
    query = db.query(Policy)

    if repository_id is not None:
        query = query.filter(Policy.repository_id == repository_id)

    total = query.count()
    policies = query.offset(skip).limit(limit).all()

    return PolicyListResponse(
        policies=[PolicyResponse.model_validate(p) for p in policies],
        total=total,
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """
    Get a specific policy by ID.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Policy details
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found",
        )

    return PolicyResponse.model_validate(policy)


@router.patch("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int,
    policy_update: PolicyUpdate,
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """
    Update a policy.

    Args:
        policy_id: Policy ID
        policy_update: Policy update data
        db: Database session

    Returns:
        Updated policy
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found",
        )

    # Update fields
    update_data = policy_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)

    return PolicyResponse.model_validate(policy)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a policy.

    Args:
        policy_id: Policy ID
        db: Database session
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found",
        )

    db.delete(policy)
    db.commit()
