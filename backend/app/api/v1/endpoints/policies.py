"""Policy API endpoints."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.models.policy import Policy, SourceType
from app.models.repository import Repository
from app.models.user import User
from app.schemas.policy import Policy as PolicySchema
from app.schemas.policy import PolicyList, PolicyUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=PolicyList)
async def list_policies(
    current_user: Annotated[User, Depends(get_current_active_user)],
    repository_id: int | None = None,
    source_type: SourceType | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> PolicyList:
    """List all policies with optional filtering (tenant-isolated).

    Args:
        current_user: Authenticated user
        repository_id: Filter by repository ID
        source_type: Filter by source type (frontend/backend/database/unknown)
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of policies
    """
    # Join with Repository to filter by tenant_id
    query = db.query(Policy).join(Repository, Policy.repository_id == Repository.id)
    query = query.filter(Repository.tenant_id == current_user.tenant_id)

    if repository_id:
        query = query.filter(Policy.repository_id == repository_id)

    if source_type:
        query = query.filter(Policy.source_type == source_type)

    total = query.count()
    policies = query.offset(skip).limit(limit).all()

    return PolicyList(policies=policies, total=total)


def _check_policy_access(db: Session, policy_id: int, tenant_id: str) -> Policy:
    """Check if user has access to policy (tenant-isolated).

    Raises HTTPException if policy not found or access denied.
    """
    policy = (
        db.query(Policy)
        .join(Repository, Policy.repository_id == Repository.id)
        .filter(Policy.id == policy_id, Repository.tenant_id == tenant_id)
        .first()
    )

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    return policy


@router.get("/{policy_id}", response_model=PolicySchema)
async def get_policy(
    policy_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> PolicySchema:
    """Get a single policy by ID (tenant-isolated).

    Args:
        policy_id: Policy ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Policy details
    """
    policy = _check_policy_access(db, policy_id, current_user.tenant_id)
    return policy


@router.put("/{policy_id}", response_model=PolicySchema)
async def update_policy(
    policy_id: int,
    policy_update: PolicyUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> PolicySchema:
    """Update a policy (tenant-isolated).

    Args:
        policy_id: Policy ID
        policy_update: Updated policy data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated policy
    """
    policy = _check_policy_access(db, policy_id, current_user.tenant_id)

    # Update only provided fields
    update_data = policy_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)

    logger.info(f"Policy {policy_id} updated", extra={"policy_id": policy_id, "tenant_id": current_user.tenant_id})

    return policy


@router.put("/{policy_id}/approve")
async def approve_policy(
    policy_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> dict:
    """Approve a policy (tenant-isolated).

    Args:
        policy_id: Policy ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    from app.models.policy import PolicyStatus

    policy = _check_policy_access(db, policy_id, current_user.tenant_id)

    policy.status = PolicyStatus.APPROVED
    db.commit()

    return {"status": "success", "message": "Policy approved"}


@router.put("/{policy_id}/reject")
async def reject_policy(
    policy_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> dict:
    """Reject a policy (tenant-isolated).

    Args:
        policy_id: Policy ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    from app.models.policy import PolicyStatus

    policy = _check_policy_access(db, policy_id, current_user.tenant_id)

    policy.status = PolicyStatus.REJECTED
    db.commit()

    return {"status": "success", "message": "Policy rejected"}


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> dict:
    """Delete a policy (tenant-isolated).

    Args:
        policy_id: Policy ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    policy = _check_policy_access(db, policy_id, current_user.tenant_id)

    db.delete(policy)
    db.commit()

    return {"status": "success", "message": "Policy deleted"}
