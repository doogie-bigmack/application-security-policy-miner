"""API endpoints for policy changes and work items."""
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models import ChangeType, WorkItemStatus
from app.models import PolicyChange as PolicyChangeModel
from app.models import WorkItem as WorkItemModel
from app.schemas.policy_change import PolicyChange, WorkItem, WorkItemUpdate
from app.services.change_detection_service import ChangeDetectionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/detect", response_model=dict[str, Any])
def detect_changes(
    repository_id: int = Query(..., description="Repository ID to detect changes for"),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict[str, Any]:
    """
    Detect policy changes for a repository.

    Compares current policies to previous scan and identifies added, modified, or deleted policies.
    Automatically creates work items for detected changes.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    service = ChangeDetectionService(db, api_key)

    try:
        changes = service.detect_changes(repository_id, tenant_id)
        return {
            "message": f"Detected {len(changes)} policy changes",
            "changes_count": len(changes),
            "added": sum(1 for c in changes if c.change_type == ChangeType.ADDED),
            "modified": sum(1 for c in changes if c.change_type == ChangeType.MODIFIED),
            "deleted": sum(1 for c in changes if c.change_type == ChangeType.DELETED),
        }
    except Exception as e:
        logger.exception(f"Error detecting changes: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/", response_model=list[PolicyChange])
def list_changes(
    repository_id: int | None = Query(None, description="Filter by repository ID"),
    change_type: ChangeType | None = Query(None, description="Filter by change type"),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> list[PolicyChangeModel]:
    """
    List all policy changes.

    Supports filtering by repository ID and change type.
    Results are automatically filtered by tenant for multi-tenancy.
    """
    query = db.query(PolicyChangeModel)

    if tenant_id:
        query = query.filter(PolicyChangeModel.tenant_id == tenant_id)

    if repository_id:
        query = query.filter(PolicyChangeModel.repository_id == repository_id)

    if change_type:
        query = query.filter(PolicyChangeModel.change_type == change_type)

    query = query.order_by(PolicyChangeModel.detected_at.desc())

    return query.all()


@router.get("/spaghetti-metrics", response_model=dict[str, Any])
def get_spaghetti_metrics(
    repository_id: int | None = Query(None, description="Filter by repository ID"),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict[str, Any]:
    """
    Get spaghetti code prevention metrics.

    Returns statistics about detected inline authorization (spaghetti code) and prevention efforts.
    """
    query = db.query(WorkItemModel)

    if tenant_id:
        query = query.filter(WorkItemModel.tenant_id == tenant_id)

    if repository_id:
        query = query.filter(WorkItemModel.repository_id == repository_id)

    all_work_items = query.all()

    # Calculate spaghetti-specific metrics
    spaghetti_items = [wi for wi in all_work_items if wi.is_spaghetti_detection == 1]
    total_spaghetti_detected = len(spaghetti_items)
    spaghetti_resolved = len([wi for wi in spaghetti_items if wi.status == WorkItemStatus.RESOLVED])
    spaghetti_open = len([wi for wi in spaghetti_items if wi.status == WorkItemStatus.OPEN])
    spaghetti_in_progress = len([wi for wi in spaghetti_items if wi.status == WorkItemStatus.IN_PROGRESS])

    # Calculate prevention rate (percentage of spaghetti items that have been addressed)
    prevention_rate = (spaghetti_resolved / total_spaghetti_detected * 100) if total_spaghetti_detected > 0 else 0

    return {
        "total_spaghetti_detected": total_spaghetti_detected,
        "spaghetti_resolved": spaghetti_resolved,
        "spaghetti_open": spaghetti_open,
        "spaghetti_in_progress": spaghetti_in_progress,
        "prevention_rate": round(prevention_rate, 2),
        "total_work_items": len(all_work_items),
        "message": "Spaghetti code prevention metrics retrieved successfully"
    }


@router.get("/{change_id}", response_model=PolicyChange)
def get_change(
    change_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> PolicyChangeModel:
    """Get a single policy change by ID."""
    query = db.query(PolicyChangeModel).filter(PolicyChangeModel.id == change_id)

    if tenant_id:
        query = query.filter(PolicyChangeModel.tenant_id == tenant_id)

    change = query.first()
    if not change:
        raise HTTPException(status_code=404, detail="Policy change not found")

    return change


@router.delete("/{change_id}")
def delete_change(
    change_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict[str, str]:
    """Delete a policy change."""
    query = db.query(PolicyChangeModel).filter(PolicyChangeModel.id == change_id)

    if tenant_id:
        query = query.filter(PolicyChangeModel.tenant_id == tenant_id)

    change = query.first()
    if not change:
        raise HTTPException(status_code=404, detail="Policy change not found")

    db.delete(change)
    db.commit()

    return {"message": "Policy change deleted successfully"}


# Work Items endpoints


@router.get("/work-items/", response_model=list[WorkItem])
def list_work_items(
    repository_id: int | None = Query(None, description="Filter by repository ID"),
    status: WorkItemStatus | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> list[WorkItemModel]:
    """
    List all work items.

    Supports filtering by repository ID and status.
    Results are automatically filtered by tenant for multi-tenancy.
    """
    query = db.query(WorkItemModel)

    if tenant_id:
        query = query.filter(WorkItemModel.tenant_id == tenant_id)

    if repository_id:
        query = query.filter(WorkItemModel.repository_id == repository_id)

    if status:
        query = query.filter(WorkItemModel.status == status)

    query = query.order_by(WorkItemModel.created_at.desc())

    return query.all()


@router.get("/work-items/{work_item_id}", response_model=WorkItem)
def get_work_item(
    work_item_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> WorkItemModel:
    """Get a single work item by ID."""
    query = db.query(WorkItemModel).filter(WorkItemModel.id == work_item_id)

    if tenant_id:
        query = query.filter(WorkItemModel.tenant_id == tenant_id)

    work_item = query.first()
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")

    return work_item


@router.put("/work-items/{work_item_id}", response_model=WorkItem)
def update_work_item(
    work_item_id: int,
    update_data: WorkItemUpdate,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> WorkItemModel:
    """Update a work item."""
    query = db.query(WorkItemModel).filter(WorkItemModel.id == work_item_id)

    if tenant_id:
        query = query.filter(WorkItemModel.tenant_id == tenant_id)

    work_item = query.first()
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")

    # Update fields
    if update_data.status is not None:
        work_item.status = update_data.status
        if update_data.status == WorkItemStatus.RESOLVED:
            from datetime import UTC, datetime

            work_item.resolved_at = datetime.now(UTC)

    if update_data.priority is not None:
        work_item.priority = update_data.priority

    if update_data.assigned_to is not None:
        work_item.assigned_to = update_data.assigned_to

    if update_data.description is not None:
        work_item.description = update_data.description

    db.commit()
    db.refresh(work_item)

    return work_item


@router.delete("/work-items/{work_item_id}")
def delete_work_item(
    work_item_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict[str, str]:
    """Delete a work item."""
    query = db.query(WorkItemModel).filter(WorkItemModel.id == work_item_id)

    if tenant_id:
        query = query.filter(WorkItemModel.tenant_id == tenant_id)

    work_item = query.first()
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")

    db.delete(work_item)
    db.commit()

    return {"message": "Work item deleted successfully"}


@router.get("/spaghetti-metrics", response_model=dict[str, Any])
def get_spaghetti_metrics(
    repository_id: int | None = Query(None, description="Filter by repository ID"),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict[str, Any]:
    """
    Get spaghetti code prevention metrics.

    Returns statistics about detected inline authorization (spaghetti code) and prevention efforts.
    """
    query = db.query(WorkItemModel)

    if tenant_id:
        query = query.filter(WorkItemModel.tenant_id == tenant_id)

    if repository_id:
        query = query.filter(WorkItemModel.repository_id == repository_id)

    all_work_items = query.all()

    # Calculate spaghetti-specific metrics
    spaghetti_items = [wi for wi in all_work_items if wi.is_spaghetti_detection == 1]
    total_spaghetti_detected = len(spaghetti_items)
    spaghetti_resolved = len([wi for wi in spaghetti_items if wi.status == WorkItemStatus.RESOLVED])
    spaghetti_open = len([wi for wi in spaghetti_items if wi.status == WorkItemStatus.OPEN])
    spaghetti_in_progress = len([wi for wi in spaghetti_items if wi.status == WorkItemStatus.IN_PROGRESS])

    # Calculate prevention rate (percentage of spaghetti items that have been addressed)
    prevention_rate = (spaghetti_resolved / total_spaghetti_detected * 100) if total_spaghetti_detected > 0 else 0

    return {
        "total_spaghetti_detected": total_spaghetti_detected,
        "spaghetti_resolved": spaghetti_resolved,
        "spaghetti_open": spaghetti_open,
        "spaghetti_in_progress": spaghetti_in_progress,
        "prevention_rate": round(prevention_rate, 2),
        "total_work_items": len(all_work_items),
        "message": "Spaghetti code prevention metrics retrieved successfully"
    }
