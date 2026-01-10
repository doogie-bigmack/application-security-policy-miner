"""Bulk scan API endpoints for parallel repository scanning."""

from typing import Any

import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.repository import Repository
from app.tasks.scan_tasks import bulk_scan_repositories_task, scan_repository_task

router = APIRouter()
logger = structlog.get_logger(__name__)


class BulkScanRequest(BaseModel):
    """Request model for bulk scanning."""

    repository_ids: list[int] = Field(
        ..., description="List of repository IDs to scan", min_length=1
    )
    incremental: bool = Field(
        default=False, description="If True, only scan changed files"
    )
    batch_size: int = Field(
        default=50,
        description="Number of repositories to process per batch (for enterprise-scale scanning)",
        ge=1,
        le=100,
    )


class BulkScanResponse(BaseModel):
    """Response model for bulk scan."""

    total_repositories: int
    total_batches: int
    batch_size: int
    spawned_tasks: int
    task_ids: list[dict[str, Any]]
    status: str
    bulk_task_id: str


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    task_id: str
    state: str
    result: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


@router.post("/bulk-scan/", response_model=BulkScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def bulk_scan(
    request: BulkScanRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> BulkScanResponse:
    """
    Trigger bulk scanning of multiple repositories in parallel.

    This endpoint spawns separate Celery tasks for each repository,
    enabling true parallel processing.

    Args:
        request: Bulk scan request with repository IDs
        db: Database session
        tenant_id: Optional tenant ID for multi-tenancy

    Returns:
        BulkScanResponse with task IDs for tracking progress
    """
    logger.info(
        "Bulk scan requested",
        repository_count=len(request.repository_ids),
        tenant_id=tenant_id,
    )

    # Validate repositories exist and user has access
    query = db.query(Repository).filter(Repository.id.in_(request.repository_ids))
    if tenant_id:
        query = query.filter(Repository.tenant_id == tenant_id)

    repos = query.all()

    if len(repos) != len(request.repository_ids):
        found_ids = {r.id for r in repos}
        requested_ids = set(request.repository_ids)
        missing_ids = requested_ids - found_ids

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repositories not found or access denied: {missing_ids}",
        )

    # Spawn bulk scan task
    task = bulk_scan_repositories_task.apply_async(
        kwargs={
            "repository_ids": request.repository_ids,
            "tenant_id": tenant_id,
            "incremental": request.incremental,
            "batch_size": request.batch_size,
        }
    )

    logger.info(
        "Bulk scan task spawned",
        bulk_task_id=task.id,
        repository_count=len(request.repository_ids),
    )

    # Get task result to return task IDs
    # Wait a short time for the bulk task to spawn individual tasks
    import time
    time.sleep(1)

    result = task.get(timeout=5)

    return BulkScanResponse(
        total_repositories=result["total_repositories"],
        total_batches=result["total_batches"],
        batch_size=result["batch_size"],
        spawned_tasks=result["spawned_tasks"],
        task_ids=result["task_ids"],
        status=result["status"],
        bulk_task_id=task.id,
    )


@router.get("/task/{task_id}/status/", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    Get status of a Celery task.

    Args:
        task_id: Celery task ID

    Returns:
        TaskStatusResponse with current task state and result
    """
    task_result = AsyncResult(task_id)

    return TaskStatusResponse(
        task_id=task_id,
        state=task_result.state,
        result=task_result.result if task_result.successful() else None,
        meta=task_result.info if isinstance(task_result.info, dict) else None,
    )


@router.post("/scan/{repository_id}/", status_code=status.HTTP_202_ACCEPTED)
async def async_scan_repository(
    repository_id: int,
    incremental: bool = False,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> dict[str, Any]:
    """
    Trigger async scan of a single repository using Celery.

    Args:
        repository_id: ID of the repository to scan
        incremental: If True, only scan changed files
        db: Database session
        tenant_id: Optional tenant ID for multi-tenancy

    Returns:
        Dictionary with task ID for tracking
    """
    logger.info(
        "Async scan requested",
        repository_id=repository_id,
        tenant_id=tenant_id,
        incremental=incremental,
    )

    # Validate repository exists
    query = db.query(Repository).filter(Repository.id == repository_id)
    if tenant_id:
        query = query.filter(Repository.tenant_id == tenant_id)

    repo = query.first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    # Spawn scan task
    task = scan_repository_task.apply_async(
        kwargs={
            "repository_id": repository_id,
            "tenant_id": tenant_id,
            "incremental": incremental,
        }
    )

    logger.info(
        "Scan task spawned",
        task_id=task.id,
        repository_id=repository_id,
    )

    return {
        "task_id": task.id,
        "repository_id": repository_id,
        "status": "Task queued",
    }
