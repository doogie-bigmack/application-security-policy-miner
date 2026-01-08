"""Conflict API endpoints."""
import logging
import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.models.conflict import ConflictStatus, PolicyConflict
from app.models.policy import Policy
from app.models.repository import Repository
from app.models.user import User
from app.schemas.conflict import Conflict, ConflictList, ConflictResolve
from app.services.conflict_detection import ConflictDetectionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/detect", response_model=ConflictList)
def detect_conflicts(
    current_user: Annotated[User, Depends(get_current_active_user)],
    repository_id: int | None = None,
    db: Session = Depends(get_db),
) -> ConflictList:
    """
    Detect conflicts between policies (tenant-isolated).

    Args:
        current_user: Authenticated user
        repository_id: Optional repository ID to limit conflict detection
        db: Database session

    Returns:
        List of detected conflicts
    """
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # If repository_id provided, verify tenant access
    if repository_id:
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo or repo.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Repository not found")

    service = ConflictDetectionService(db, anthropic_api_key)
    service.detect_conflicts(repository_id, tenant_id=current_user.tenant_id)

    # Get all conflicts for this tenant
    query = db.query(PolicyConflict).join(
        Policy, PolicyConflict.policy_a_id == Policy.id
    ).join(
        Repository, Policy.repository_id == Repository.id
    ).filter(Repository.tenant_id == current_user.tenant_id)

    if repository_id:
        query = query.filter(Repository.id == repository_id)

    all_conflicts = query.all()

    return ConflictList(conflicts=all_conflicts, total=len(all_conflicts))


def _check_conflict_access(db: Session, conflict_id: int, tenant_id: str) -> PolicyConflict:
    """Check if user has access to conflict (tenant-isolated)."""
    conflict = (
        db.query(PolicyConflict)
        .join(Policy, PolicyConflict.policy_a_id == Policy.id)
        .join(Repository, Policy.repository_id == Repository.id)
        .filter(PolicyConflict.id == conflict_id, Repository.tenant_id == tenant_id)
        .first()
    )

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    return conflict


@router.get("/", response_model=ConflictList)
def list_conflicts(
    current_user: Annotated[User, Depends(get_current_active_user)],
    status: ConflictStatus | None = None,
    repository_id: int | None = None,
    db: Session = Depends(get_db),
) -> ConflictList:
    """
    List all conflicts (tenant-isolated).

    Args:
        current_user: Authenticated user
        status: Optional filter by conflict status
        repository_id: Optional filter by repository
        db: Database session

    Returns:
        List of conflicts
    """
    # Join through policy_a to repository to filter by tenant
    query = db.query(PolicyConflict).join(
        Policy, PolicyConflict.policy_a_id == Policy.id
    ).join(
        Repository, Policy.repository_id == Repository.id
    ).filter(Repository.tenant_id == current_user.tenant_id)

    if status:
        query = query.filter(PolicyConflict.status == status)

    if repository_id:
        # Verify tenant owns this repository
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo or repo.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Repository not found")
        query = query.filter(Repository.id == repository_id)

    conflicts = query.all()

    return ConflictList(conflicts=conflicts, total=len(conflicts))


@router.get("/{conflict_id}", response_model=Conflict)
def get_conflict(
    conflict_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> Conflict:
    """
    Get a specific conflict (tenant-isolated).

    Args:
        conflict_id: Conflict ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Conflict details
    """
    conflict = _check_conflict_access(db, conflict_id, current_user.tenant_id)
    return conflict


@router.put("/{conflict_id}/resolve", response_model=Conflict)
def resolve_conflict(
    conflict_id: int,
    resolution: ConflictResolve,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> Conflict:
    """
    Resolve a conflict (tenant-isolated).

    Args:
        conflict_id: Conflict ID
        resolution: Resolution details
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated conflict
    """
    conflict = _check_conflict_access(db, conflict_id, current_user.tenant_id)

    # Update conflict status
    conflict.status = ConflictStatus.RESOLVED
    conflict.resolution_strategy = resolution.resolution_strategy
    conflict.resolution_notes = resolution.resolution_notes
    conflict.resolved_at = datetime.now(UTC)

    db.commit()
    db.refresh(conflict)

    logger.info(f"Resolved conflict {conflict_id} with strategy: {resolution.resolution_strategy}")

    return conflict


@router.delete("/{conflict_id}")
def delete_conflict(
    conflict_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete a conflict (tenant-isolated).

    Args:
        conflict_id: Conflict ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    conflict = _check_conflict_access(db, conflict_id, current_user.tenant_id)

    db.delete(conflict)
    db.commit()

    logger.info(f"Deleted conflict {conflict_id}")

    return {"message": "Conflict deleted successfully"}
