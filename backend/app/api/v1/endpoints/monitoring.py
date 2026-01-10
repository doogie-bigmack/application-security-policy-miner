"""Monitoring API endpoints for Celery workers and queues."""

from typing import Any

import structlog
from celery import current_app as celery_app
from celery.result import AsyncResult
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
logger = structlog.get_logger(__name__)


class QueueStats(BaseModel):
    """Queue statistics model."""

    queue_name: str
    queue_depth: int
    active_tasks: int
    reserved_tasks: int


class WorkerStats(BaseModel):
    """Worker statistics model."""

    worker_name: str
    status: str
    active_tasks: int
    processed_tasks: int
    pool_size: int


class MonitoringResponse(BaseModel):
    """Monitoring response model."""

    total_workers: int
    active_workers: int
    total_tasks_active: int
    total_tasks_reserved: int
    queue_depth: int
    workers: list[WorkerStats]
    queues: list[QueueStats]


@router.get("/queue-stats/", response_model=MonitoringResponse)
async def get_queue_stats() -> MonitoringResponse:
    """
    Get current queue depth and worker utilization stats.

    This endpoint provides real-time monitoring of the Celery
    worker pool and task queues, useful for tracking enterprise-scale
    bulk scanning operations.

    Returns:
        MonitoringResponse with queue and worker statistics
    """
    logger.info("Fetching queue and worker stats")

    # Get inspect interface
    inspect = celery_app.control.inspect()

    # Get active tasks per worker
    active_tasks_by_worker = inspect.active() or {}

    # Get reserved tasks per worker
    reserved_tasks_by_worker = inspect.reserved() or {}

    # Get stats per worker
    worker_stats_data = inspect.stats() or {}

    # Calculate totals
    total_workers = len(worker_stats_data)
    active_workers = len([w for w in worker_stats_data if worker_stats_data[w]])
    total_tasks_active = sum(len(tasks) for tasks in active_tasks_by_worker.values())
    total_tasks_reserved = sum(len(tasks) for tasks in reserved_tasks_by_worker.values())

    # Build worker stats
    workers = []
    for worker_name, stats in worker_stats_data.items():
        active_count = len(active_tasks_by_worker.get(worker_name, []))

        workers.append(WorkerStats(
            worker_name=worker_name,
            status="active" if active_count > 0 else "idle",
            active_tasks=active_count,
            processed_tasks=stats.get("total", {}).get("tasks.received", 0) if stats else 0,
            pool_size=stats.get("pool", {}).get("max-concurrency", 0) if stats else 0,
        ))

    # Get queue stats (default queue)
    # Note: Celery doesn't directly expose queue depth, but we can estimate from reserved + active
    queues = [
        QueueStats(
            queue_name="celery",  # Default queue name
            queue_depth=total_tasks_reserved,  # Approximate queue depth
            active_tasks=total_tasks_active,
            reserved_tasks=total_tasks_reserved,
        )
    ]

    logger.info(
        "Queue stats fetched",
        total_workers=total_workers,
        active_workers=active_workers,
        total_tasks_active=total_tasks_active,
    )

    return MonitoringResponse(
        total_workers=total_workers,
        active_workers=active_workers,
        total_tasks_active=total_tasks_active,
        total_tasks_reserved=total_tasks_reserved,
        queue_depth=total_tasks_reserved,
        workers=workers,
        queues=queues,
    )


@router.get("/bulk-task/{task_id}/progress/")
async def get_bulk_task_progress(task_id: str) -> dict[str, Any]:
    """
    Get detailed progress for a bulk scan task.

    Args:
        task_id: Celery task ID of the bulk scan

    Returns:
        Dictionary with progress information
    """
    logger.info("Fetching bulk task progress", task_id=task_id)

    task_result = AsyncResult(task_id)

    # Get task info
    response = {
        "task_id": task_id,
        "state": task_result.state,
        "result": None,
        "meta": None,
    }

    if task_result.state == "PENDING":
        response["meta"] = {"status": "Task is queued or not started yet"}
    elif task_result.state == "STARTED":
        response["meta"] = task_result.info if isinstance(task_result.info, dict) else {}
    elif task_result.state == "PROGRESS":
        response["meta"] = task_result.info if isinstance(task_result.info, dict) else {}
    elif task_result.state == "SUCCESS":
        response["result"] = task_result.result
        response["meta"] = {"status": "Task completed successfully"}
    elif task_result.state == "FAILURE":
        response["meta"] = {
            "status": "Task failed",
            "error": str(task_result.info) if task_result.info else "Unknown error",
        }
    else:
        response["meta"] = task_result.info if isinstance(task_result.info, dict) else {}

    return response
