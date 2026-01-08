"""Policy API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.policy import Policy
from app.schemas.policy import Policy as PolicySchema
from app.schemas.policy import PolicyList

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=PolicyList)
async def list_policies(
    repository_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> PolicyList:
    """List all policies with optional filtering.

    Args:
        repository_id: Filter by repository ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of policies
    """
    query = db.query(Policy)

    if repository_id:
        query = query.filter(Policy.repository_id == repository_id)

    total = query.count()
    policies = query.offset(skip).limit(limit).all()

    return PolicyList(policies=policies, total=total)


@router.get("/{policy_id}", response_model=PolicySchema)
async def get_policy(policy_id: int, db: Session = Depends(get_db)) -> PolicySchema:
    """Get a single policy by ID.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Policy details
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    return policy


@router.put("/{policy_id}/approve")
async def approve_policy(policy_id: int, db: Session = Depends(get_db)) -> dict:
    """Approve a policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Success message
    """
    from app.models.policy import PolicyStatus

    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.status = PolicyStatus.APPROVED
    db.commit()

    return {"status": "success", "message": "Policy approved"}


@router.put("/{policy_id}/reject")
async def reject_policy(policy_id: int, db: Session = Depends(get_db)) -> dict:
    """Reject a policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Success message
    """
    from app.models.policy import PolicyStatus

    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.status = PolicyStatus.REJECTED
    db.commit()

    return {"status": "success", "message": "Policy rejected"}


@router.delete("/{policy_id}")
async def delete_policy(policy_id: int, db: Session = Depends(get_db)) -> dict:
    """Delete a policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Success message
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    db.delete(policy)
    db.commit()

    return {"status": "success", "message": "Policy deleted"}
