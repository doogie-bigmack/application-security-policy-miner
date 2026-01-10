"""Work items and spaghetti detection API endpoints."""
import logging
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.policy_change import WorkItem, WorkItemPriority, WorkItemStatus

logger = structlog.get_logger()

router = APIRouter()


class WorkItemResponse(BaseModel):
    """Work item response model."""

    id: int
    policy_change_id: int
    repository_id: int
    title: str
    description: str | None
    status: str
    priority: str
    assigned_to: str | None
    is_spaghetti_detection: int
    refactoring_suggestion: str | None
    created_at: str
    updated_at: str
    resolved_at: str | None
    tenant_id: str | None

    class Config:
        """Pydantic config."""

        from_attributes = True


class SpaghettiMetricsResponse(BaseModel):
    """Spaghetti detection metrics response."""

    total_detections: int
    open_detections: int
    resolved_detections: int
    detection_rate: float  # Detections per day
    avg_resolution_time_hours: float | None
    detections_by_repository: list[dict]
    recent_detections: list[WorkItemResponse]


class WorkItemUpdateRequest(BaseModel):
    """Request to update a work item."""

    status: str | None = None
    assigned_to: str | None = None
    priority: str | None = None


@router.get("/", response_model=list[WorkItemResponse])
def list_work_items(
    x_tenant_id: Annotated[str | None, Header()] = None,
    status: str | None = None,
    priority: str | None = None,
    spaghetti_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List all work items with optional filters.

    Args:
        x_tenant_id: Tenant ID for multi-tenancy
        status: Filter by status (open, in_progress, resolved, closed)
        priority: Filter by priority (low, medium, high, critical)
        spaghetti_only: If True, only return spaghetti detection work items
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of work items
    """
    logger.info(
        "list_work_items",
        tenant_id=x_tenant_id,
        status=status,
        priority=priority,
        spaghetti_only=spaghetti_only,
    )

    query = select(WorkItem)

    # Apply filters
    filters = []
    if x_tenant_id:
        filters.append(WorkItem.tenant_id == x_tenant_id)
    if status:
        try:
            status_enum = WorkItemStatus(status)
            filters.append(WorkItem.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if priority:
        try:
            priority_enum = WorkItemPriority(priority)
            filters.append(WorkItem.priority == priority_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
    if spaghetti_only:
        filters.append(WorkItem.is_spaghetti_detection == 1)

    if filters:
        query = query.where(and_(*filters))

    # Order by priority (critical first) then created_at (newest first)
    query = query.order_by(
        WorkItem.priority.desc(),
        WorkItem.created_at.desc(),
    ).offset(skip).limit(limit)

    work_items = db.scalars(query).all()

    return [
        WorkItemResponse(
            id=item.id,
            policy_change_id=item.policy_change_id,
            repository_id=item.repository_id,
            title=item.title,
            description=item.description,
            status=item.status.value,
            priority=item.priority.value,
            assigned_to=item.assigned_to,
            is_spaghetti_detection=item.is_spaghetti_detection,
            refactoring_suggestion=item.refactoring_suggestion,
            created_at=item.created_at.isoformat() if item.created_at else "",
            updated_at=item.updated_at.isoformat() if item.updated_at else "",
            resolved_at=item.resolved_at.isoformat() if item.resolved_at else None,
            tenant_id=item.tenant_id,
        )
        for item in work_items
    ]


@router.get("/{work_item_id}", response_model=WorkItemResponse)
def get_work_item(
    work_item_id: int,
    x_tenant_id: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
):
    """Get a specific work item by ID."""
    logger.info("get_work_item", work_item_id=work_item_id, tenant_id=x_tenant_id)

    query = select(WorkItem).where(WorkItem.id == work_item_id)
    if x_tenant_id:
        query = query.where(WorkItem.tenant_id == x_tenant_id)

    work_item = db.scalars(query).first()
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")

    return WorkItemResponse(
        id=work_item.id,
        policy_change_id=work_item.policy_change_id,
        repository_id=work_item.repository_id,
        title=work_item.title,
        description=work_item.description,
        status=work_item.status.value,
        priority=work_item.priority.value,
        assigned_to=work_item.assigned_to,
        is_spaghetti_detection=work_item.is_spaghetti_detection,
        refactoring_suggestion=work_item.refactoring_suggestion,
        created_at=work_item.created_at.isoformat() if work_item.created_at else "",
        updated_at=work_item.updated_at.isoformat() if work_item.updated_at else "",
        resolved_at=work_item.resolved_at.isoformat() if work_item.resolved_at else None,
        tenant_id=work_item.tenant_id,
    )


@router.patch("/{work_item_id}", response_model=WorkItemResponse)
def update_work_item(
    work_item_id: int,
    request: WorkItemUpdateRequest,
    x_tenant_id: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
):
    """Update a work item's status, assignment, or priority."""
    logger.info("update_work_item", work_item_id=work_item_id, tenant_id=x_tenant_id)

    query = select(WorkItem).where(WorkItem.id == work_item_id)
    if x_tenant_id:
        query = query.where(WorkItem.tenant_id == x_tenant_id)

    work_item = db.scalars(query).first()
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")

    # Update fields if provided
    if request.status:
        try:
            work_item.status = WorkItemStatus(request.status)
            # If marking as resolved, set resolved_at timestamp
            if work_item.status in [WorkItemStatus.RESOLVED, WorkItemStatus.CLOSED]:
                from datetime import UTC, datetime
                work_item.resolved_at = datetime.now(UTC)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

    if request.assigned_to is not None:
        work_item.assigned_to = request.assigned_to

    if request.priority:
        try:
            work_item.priority = WorkItemPriority(request.priority)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {request.priority}")

    db.commit()
    db.refresh(work_item)

    return WorkItemResponse(
        id=work_item.id,
        policy_change_id=work_item.policy_change_id,
        repository_id=work_item.repository_id,
        title=work_item.title,
        description=work_item.description,
        status=work_item.status.value,
        priority=work_item.priority.value,
        assigned_to=work_item.assigned_to,
        is_spaghetti_detection=work_item.is_spaghetti_detection,
        refactoring_suggestion=work_item.refactoring_suggestion,
        created_at=work_item.created_at.isoformat() if work_item.created_at else "",
        updated_at=work_item.updated_at.isoformat() if work_item.updated_at else "",
        resolved_at=work_item.resolved_at.isoformat() if work_item.resolved_at else None,
        tenant_id=work_item.tenant_id,
    )


@router.get("/metrics/spaghetti", response_model=SpaghettiMetricsResponse)
def get_spaghetti_metrics(
    x_tenant_id: Annotated[str | None, Header()] = None,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
):
    """
    Get spaghetti detection metrics and prevention statistics.

    Args:
        x_tenant_id: Tenant ID for multi-tenancy
        days: Number of days to analyze (default: 30)
        db: Database session

    Returns:
        Spaghetti detection metrics including:
        - Total detections
        - Open/resolved counts
        - Detection rate per day
        - Average resolution time
        - Detections by repository
        - Recent detections
    """
    logger.info("get_spaghetti_metrics", tenant_id=x_tenant_id, days=days)

    from datetime import UTC, datetime, timedelta

    # Calculate date range
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    # Build base query for spaghetti detections
    base_query = select(WorkItem).where(
        and_(
            WorkItem.is_spaghetti_detection == 1,
            WorkItem.created_at >= start_date,
        )
    )
    if x_tenant_id:
        base_query = base_query.where(WorkItem.tenant_id == x_tenant_id)

    # Get all spaghetti work items in the date range
    all_items = db.scalars(base_query).all()

    # Calculate metrics
    total_detections = len(all_items)
    open_detections = sum(1 for item in all_items if item.status in [WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS])
    resolved_detections = sum(1 for item in all_items if item.status in [WorkItemStatus.RESOLVED, WorkItemStatus.CLOSED])

    # Calculate detection rate (detections per day)
    detection_rate = total_detections / days if days > 0 else 0

    # Calculate average resolution time
    resolved_items_with_time = [
        item for item in all_items
        if item.resolved_at and item.status in [WorkItemStatus.RESOLVED, WorkItemStatus.CLOSED]
    ]
    if resolved_items_with_time:
        total_resolution_hours = sum(
            (item.resolved_at - item.created_at).total_seconds() / 3600
            for item in resolved_items_with_time
        )
        avg_resolution_time_hours = total_resolution_hours / len(resolved_items_with_time)
    else:
        avg_resolution_time_hours = None

    # Group by repository
    from collections import defaultdict
    repo_counts: dict[int, dict] = defaultdict(lambda: {"total": 0, "open": 0, "resolved": 0})
    for item in all_items:
        repo_counts[item.repository_id]["total"] += 1
        if item.status in [WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS]:
            repo_counts[item.repository_id]["open"] += 1
        if item.status in [WorkItemStatus.RESOLVED, WorkItemStatus.CLOSED]:
            repo_counts[item.repository_id]["resolved"] += 1

    detections_by_repository = [
        {
            "repository_id": repo_id,
            "total": counts["total"],
            "open": counts["open"],
            "resolved": counts["resolved"],
        }
        for repo_id, counts in repo_counts.items()
    ]

    # Get recent detections (last 10)
    recent_query = base_query.order_by(WorkItem.created_at.desc()).limit(10)
    recent_items = db.scalars(recent_query).all()

    recent_detections = [
        WorkItemResponse(
            id=item.id,
            policy_change_id=item.policy_change_id,
            repository_id=item.repository_id,
            title=item.title,
            description=item.description,
            status=item.status.value,
            priority=item.priority.value,
            assigned_to=item.assigned_to,
            is_spaghetti_detection=item.is_spaghetti_detection,
            refactoring_suggestion=item.refactoring_suggestion,
            created_at=item.created_at.isoformat() if item.created_at else "",
            updated_at=item.updated_at.isoformat() if item.updated_at else "",
            resolved_at=item.resolved_at.isoformat() if item.resolved_at else None,
            tenant_id=item.tenant_id,
        )
        for item in recent_items
    ]

    return SpaghettiMetricsResponse(
        total_detections=total_detections,
        open_detections=open_detections,
        resolved_detections=resolved_detections,
        detection_rate=round(detection_rate, 2),
        avg_resolution_time_hours=round(avg_resolution_time_hours, 2) if avg_resolution_time_hours else None,
        detections_by_repository=detections_by_repository,
        recent_detections=recent_detections,
    )
