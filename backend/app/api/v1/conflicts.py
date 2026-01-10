"""Conflict API endpoints."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.conflict import ConflictStatus, PolicyConflict
from app.schemas.conflict import Conflict, ConflictList, ConflictResolve
from app.services.conflict_detection import ConflictDetectionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/detect", response_model=ConflictList)
def detect_conflicts(
    repository_id: int | None = None,
    db: Session = Depends(get_db),
) -> ConflictList:
    """
    Detect conflicts between policies.

    Args:
        repository_id: Optional repository ID to limit conflict detection
        db: Database session

    Returns:
        List of detected conflicts
    """
    service = ConflictDetectionService(db)
    service.detect_conflicts(repository_id)

    # Get all conflicts (including previously detected ones)
    query = db.query(PolicyConflict)
    if repository_id:
        # Filter by repository through the policies relationship
        query = query.join(PolicyConflict.policy_a).filter_by(repository_id=repository_id)

    all_conflicts = query.all()

    return ConflictList(conflicts=all_conflicts, total=len(all_conflicts))


@router.get("/", response_model=ConflictList)
def list_conflicts(
    status: ConflictStatus | None = None,
    repository_id: int | None = None,
    db: Session = Depends(get_db),
) -> ConflictList:
    """
    List all conflicts.

    Args:
        status: Optional filter by conflict status
        repository_id: Optional filter by repository
        db: Database session

    Returns:
        List of conflicts
    """
    query = db.query(PolicyConflict)

    if status:
        query = query.filter(PolicyConflict.status == status)

    if repository_id:
        query = query.join(PolicyConflict.policy_a).filter_by(repository_id=repository_id)

    conflicts = query.all()

    return ConflictList(conflicts=conflicts, total=len(conflicts))


@router.get("/{conflict_id}", response_model=Conflict)
def get_conflict(
    conflict_id: int,
    db: Session = Depends(get_db),
) -> Conflict:
    """
    Get a specific conflict.

    Args:
        conflict_id: Conflict ID
        db: Database session

    Returns:
        Conflict details
    """
    conflict = db.query(PolicyConflict).filter(PolicyConflict.id == conflict_id).first()

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    return conflict


@router.put("/{conflict_id}/resolve", response_model=Conflict)
def resolve_conflict(
    conflict_id: int,
    resolution: ConflictResolve,
    db: Session = Depends(get_db),
) -> Conflict:
    """
    Resolve a conflict.

    Args:
        conflict_id: Conflict ID
        resolution: Resolution details
        db: Database session

    Returns:
        Updated conflict
    """
    conflict = db.query(PolicyConflict).filter(PolicyConflict.id == conflict_id).first()

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

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
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete a conflict.

    Args:
        conflict_id: Conflict ID
        db: Database session

    Returns:
        Success message
    """
    conflict = db.query(PolicyConflict).filter(PolicyConflict.id == conflict_id).first()

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    db.delete(conflict)
    db.commit()

    logger.info(f"Deleted conflict {conflict_id}")

    return {"message": "Conflict deleted successfully"}
