"""Background worker for async tasks using RQ (Redis Queue)."""
import asyncio
import logging
from typing import Any

from redis import Redis
from rq import Worker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.scanner_service import ScannerService

logger = logging.getLogger(__name__)

# Create database engine and session factory
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def scan_repository_task(
    repository_id: int,
    tenant_id: str | None,
    incremental: bool,
    bulk_scan_id: int | None = None,
) -> dict[str, Any]:
    """Background task to scan a single repository.

    This function runs in an RQ worker process and performs the actual scan.

    Args:
        repository_id: Repository ID to scan
        tenant_id: Tenant ID for multi-tenancy
        incremental: Whether to perform incremental scan
        bulk_scan_id: Optional bulk scan ID if part of bulk operation

    Returns:
        Scan result dictionary
    """
    logger.info(
        f"Worker: Starting scan for repository {repository_id}",
        tenant_id=tenant_id,
        incremental=incremental,
        bulk_scan_id=bulk_scan_id,
    )

    db = SessionLocal()
    try:
        # Create scanner service
        scanner = ScannerService(db)

        # Run the scan (async function, so we need asyncio)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            scan_result = loop.run_until_complete(
                scanner.scan_repository(repository_id, tenant_id, incremental)
            )
        finally:
            loop.close()

        logger.info(
            f"Worker: Completed scan for repository {repository_id}",
            policies_extracted=scan_result.get("policies_extracted", 0),
            files_scanned=scan_result.get("files_scanned", 0),
        )

        # If part of bulk scan, update bulk scan progress
        if bulk_scan_id:
            from app.services.bulk_scan_service import BulkScanService

            bulk_scan_service = BulkScanService(db)
            bulk_scan_service.update_bulk_scan_from_job(
                bulk_scan_id, scan_result, success=True
            )

        return scan_result

    except Exception as e:
        logger.error(
            f"Worker: Scan failed for repository {repository_id}: {e}",
            exc_info=True,
        )

        # If part of bulk scan, update bulk scan with failure
        if bulk_scan_id:
            try:
                from app.services.bulk_scan_service import BulkScanService

                bulk_scan_service = BulkScanService(db)
                bulk_scan_service.update_bulk_scan_from_job(
                    bulk_scan_id, {"error": str(e)}, success=False
                )
            except Exception as update_error:
                logger.error(f"Failed to update bulk scan progress: {update_error}")

        raise

    finally:
        db.close()


def start_worker():
    """Start the RQ worker process.

    This function should be called from the command line:
    python -m app.worker
    """
    redis_conn = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    logger.info("Starting RQ worker for 'scans' queue")
    logger.info(f"Redis URL: {settings.REDIS_URL}")

    worker = Worker(["scans"], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    start_worker()
