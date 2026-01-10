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
) -> dict:
    """
    Async task to scan multiple repositories in parallel.

    This task spawns individual scan tasks for each repository
    and tracks their progress.

    Args:
        repository_ids: List of repository IDs to scan
        tenant_id: Optional tenant ID for multi-tenancy
        incremental: If True, only scan changed files

    Returns:
        Dictionary with overall scan results and task IDs
    """
    logger.info(
        "Starting bulk scan task",
        task_id=self.request.id,
        repository_count=len(repository_ids),
        tenant_id=tenant_id,
    )

    # Update task state
    self.update_state(
        state="STARTED",
        meta={
            "total_repositories": len(repository_ids),
            "status": "Spawning scan tasks...",
        }
    )

    # Spawn individual scan tasks
    task_ids = []
    for repo_id in repository_ids:
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
        })

    logger.info(
        "Bulk scan tasks spawned",
        task_id=self.request.id,
        spawned_tasks=len(task_ids),
    )

    return {
        "total_repositories": len(repository_ids),
        "spawned_tasks": len(task_ids),
        "task_ids": task_ids,
        "status": "Tasks spawned successfully",
    }
