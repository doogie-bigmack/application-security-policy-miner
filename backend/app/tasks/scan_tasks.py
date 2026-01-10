"""Celery tasks for repository scanning."""

import structlog
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.database import get_db
from app.services.scanner_service import ScannerService

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="scan_repository")
def scan_repository_task(
    self,
    repository_id: int,
    tenant_id: str | None = None,
    incremental: bool = False,
) -> dict:
    """
    Async task to scan a repository and extract policies.

    Args:
        repository_id: ID of the repository to scan
        tenant_id: Optional tenant ID for multi-tenancy
        incremental: If True, only scan changed files since last scan

    Returns:
        Dictionary with scan results
    """
    logger.info(
        "Starting scan task",
        task_id=self.request.id,
        repository_id=repository_id,
        tenant_id=tenant_id,
        incremental=incremental,
    )

    # Update task state to STARTED
    self.update_state(
        state="STARTED",
        meta={
            "repository_id": repository_id,
            "status": "Initializing scan...",
        }
    )

    # Get database session
    db: Session = next(get_db())

    try:
        # Create scanner service
        scanner = ScannerService(db)

        # Run scan synchronously (within async context)
        import asyncio

        # Create new event loop for this task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                scanner.scan_repository(
                    repository_id=repository_id,
                    tenant_id=tenant_id,
                    incremental=incremental,
                )
            )

            logger.info(
                "Scan task completed successfully",
                task_id=self.request.id,
                repository_id=repository_id,
                policies_extracted=result.get("policies_extracted", 0),
            )

            return result

        finally:
            loop.close()

    except Exception as e:
        logger.error(
            "Scan task failed",
            task_id=self.request.id,
            repository_id=repository_id,
            error=str(e),
        )
        raise

    finally:
        db.close()


@celery_app.task(bind=True, name="bulk_scan_repositories")
def bulk_scan_repositories_task(
    self,
    repository_ids: list[int],
    tenant_id: str | None = None,
    incremental: bool = False,
    batch_size: int = 50,
) -> dict:
    """
    Async task to scan multiple repositories in parallel with batching.

    This task spawns individual scan tasks for each repository
    and tracks their progress. For enterprise-scale (1000+ repos),
    repositories are processed in batches to prevent queue overload.

    Args:
        repository_ids: List of repository IDs to scan
        tenant_id: Optional tenant ID for multi-tenancy
        incremental: If True, only scan changed files
        batch_size: Number of repositories to process per batch (default: 50)

    Returns:
        Dictionary with overall scan results and task IDs
    """
    logger.info(
        "Starting bulk scan task",
        task_id=self.request.id,
        repository_count=len(repository_ids),
        tenant_id=tenant_id,
        batch_size=batch_size,
    )

    # Calculate batches
    total_batches = (len(repository_ids) + batch_size - 1) // batch_size

    # Update task state
    self.update_state(
        state="STARTED",
        meta={
            "total_repositories": len(repository_ids),
            "total_batches": total_batches,
            "batch_size": batch_size,
            "status": "Spawning scan tasks in batches...",
        }
    )

    # Spawn individual scan tasks in batches
    task_ids = []
    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, len(repository_ids))
        batch_repo_ids = repository_ids[batch_start:batch_end]

        logger.info(
            "Processing batch",
            task_id=self.request.id,
            batch_num=batch_num + 1,
            total_batches=total_batches,
            batch_repos=len(batch_repo_ids),
        )

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "total_repositories": len(repository_ids),
                "total_batches": total_batches,
                "current_batch": batch_num + 1,
                "batch_size": batch_size,
                "spawned_so_far": len(task_ids),
                "status": f"Processing batch {batch_num + 1} of {total_batches}...",
            }
        )

        # Spawn tasks for this batch
        for repo_id in batch_repo_ids:
            task = scan_repository_task.apply_async(
                kwargs={
                    "repository_id": repo_id,
                    "tenant_id": tenant_id,
                    "incremental": incremental,
                }
            )
            task_ids.append({
                "repository_id": repo_id,
                "task_id": task.id,
                "batch": batch_num + 1,
            })

    logger.info(
        "Bulk scan tasks spawned",
        task_id=self.request.id,
        spawned_tasks=len(task_ids),
        total_batches=total_batches,
    )

    return {
        "total_repositories": len(repository_ids),
        "total_batches": total_batches,
        "batch_size": batch_size,
        "spawned_tasks": len(task_ids),
        "task_ids": task_ids,
        "status": "Tasks spawned successfully",
    }
