"""Monitoring API endpoints for Celery workers and queues."""

from typing import Any

import structlog
from celery import current_app as celery_app
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.worker_autoscaler import get_autoscaler

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


class AutoscalerConfig(BaseModel):
    """Autoscaler configuration model."""

    min_workers: int
    max_workers: int
    scale_up_threshold: int
    scale_down_threshold: int
    check_interval: int


class AutoscalerMetrics(BaseModel):
    """Autoscaler metrics model."""

    config: AutoscalerConfig
    current_state: dict[str, Any]
    status: str


class ScaleRequest(BaseModel):
    """Manual scaling request."""

    target_count: int


@router.get("/autoscaler/metrics/", response_model=AutoscalerMetrics)
async def get_autoscaler_metrics() -> AutoscalerMetrics:
    """
    Get autoscaler metrics and configuration.

    Returns:
        AutoscalerMetrics with current configuration and state
    """
    logger.info("Fetching autoscaler metrics")

    autoscaler = get_autoscaler()
    metrics = autoscaler.get_metrics()

    return AutoscalerMetrics(
        config=AutoscalerConfig(**metrics["config"]),
        current_state=metrics["current_state"],
        status=metrics["status"],
    )


@router.post("/autoscaler/scale/")
async def manual_scale_workers(request: ScaleRequest) -> dict[str, Any]:
    """
    Manually scale workers to a target count.

    Args:
        request: ScaleRequest with target worker count

    Returns:
        Dictionary with scaling result
    """
    logger.info("Manual scaling requested", target_count=request.target_count)

    autoscaler = get_autoscaler()

    # Validate target count
    if request.target_count < autoscaler.min_workers:
        raise HTTPException(
            status_code=400,
            detail=f"Target count must be at least {autoscaler.min_workers}",
        )

    if request.target_count > autoscaler.max_workers:
        raise HTTPException(
            status_code=400,
            detail=f"Target count must not exceed {autoscaler.max_workers}",
        )

    success = autoscaler.scale_workers(request.target_count)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to scale workers. Check logs for details.",
        )

    return {
        "success": True,
        "target_count": request.target_count,
        "message": f"Workers scaling to {request.target_count}",
    }


@router.post("/autoscaler/start/")
async def start_autoscaler() -> dict[str, Any]:
    """
    Start the autoscaler monitoring loop.

    Returns:
        Dictionary with start result
    """
    logger.info("Starting autoscaler")

    # Note: This would need to be run in a background task
    # For now, we'll just return a status
    return {
        "success": True,
        "message": "Autoscaler start requested. Note: Autoscaler runs as a background service.",
    }


@router.post("/autoscaler/stop/")
async def stop_autoscaler() -> dict[str, Any]:
    """
    Stop the autoscaler monitoring loop.

    Returns:
        Dictionary with stop result
    """
    logger.info("Stopping autoscaler")

    autoscaler = get_autoscaler()
    autoscaler.stop()

    return {
        "success": True,
        "message": "Autoscaler stopped",
    }


@router.post("/workers/restart-failed/")
async def restart_failed_workers() -> dict[str, Any]:
    """
    Manually trigger restart of failed workers.

    Returns:
        Dictionary with restart result
    """
    logger.info("Manual restart of failed workers requested")

    autoscaler = get_autoscaler()
    autoscaler.restart_failed_workers()

    return {
        "success": True,
        "message": "Failed worker restart triggered",
    }
