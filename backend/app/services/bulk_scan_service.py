"""Bulk scan service for parallel application scanning."""
import logging
from datetime import datetime
from typing import Any

from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.bulk_scan import BulkScan, BulkScanStatus
from app.models.repository import Repository

logger = logging.getLogger(__name__)


class BulkScanService:
    """Service for orchestrating parallel repository scans."""

    def __init__(self, db: Session):
        """Initialize bulk scan service.

        Args:
            db: Database session
        """
        self.db = db
        self.redis_conn = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.queue = Queue("scans", connection=self.redis_conn)

    def initiate_bulk_scan(
        self,
        repository_ids: list[int],
        tenant_id: str | None,
        incremental: bool = False,
        max_parallel_workers: int = 10,
    ) -> tuple[BulkScan, list[dict[str, Any]]]:
        """Initiate a bulk scan operation for multiple repositories.

        Args:
            repository_ids: List of repository IDs to scan
            tenant_id: Tenant ID for multi-tenancy
            incremental: Whether to perform incremental scans
            max_parallel_workers: Maximum number of parallel workers

        Returns:
            Tuple of (BulkScan object, list of job information dicts)
        """
        logger.info(
            f"Initiating bulk scan for {len(repository_ids)} repositories",
            tenant_id=tenant_id,
            incremental=incremental,
            max_parallel_workers=max_parallel_workers,
        )

        # Create bulk scan record
        bulk_scan = BulkScan(
            tenant_id=tenant_id,
            total_applications=len(repository_ids),
            target_ids=repository_ids,
            max_parallel_workers=max_parallel_workers,
            status=BulkScanStatus.QUEUED,
            started_at=datetime.utcnow(),
        )
        self.db.add(bulk_scan)
        self.db.commit()
        self.db.refresh(bulk_scan)

        # Queue scan jobs for each repository
        jobs_info = []
        initiated_count = 0
        failed_count = 0

        for repo_id in repository_ids:
            try:
                # Get repository info
                query = self.db.query(Repository).filter(Repository.id == repo_id)
                if tenant_id:
                    query = query.filter(Repository.tenant_id == tenant_id)
                repo = query.first()

                if not repo:
                    logger.warning(f"Repository {repo_id} not found, skipping")
                    failed_count += 1
                    continue

                # Enqueue scan job
                job = self.queue.enqueue(
                    "app.worker.scan_repository_task",
                    repo_id,
                    tenant_id,
                    incremental,
                    bulk_scan.id,
                    job_timeout="30m",  # 30 minute timeout per scan
                    result_ttl=3600,  # Keep results for 1 hour
                    failure_ttl=86400,  # Keep failures for 24 hours
                )

                jobs_info.append({
                    "repository_id": repo_id,
                    "repository_name": repo.name,
                    "job_id": job.id,
                    "status": job.get_status(),
                })
                initiated_count += 1

                logger.info(
                    f"Queued scan job {job.id} for repository {repo_id} ({repo.name})"
                )

            except Exception as e:
                logger.error(f"Failed to queue scan for repository {repo_id}: {e}")
                failed_count += 1
                continue

        # Update bulk scan status
        if initiated_count > 0:
            bulk_scan.status = BulkScanStatus.PROCESSING
        else:
            bulk_scan.status = BulkScanStatus.FAILED
            bulk_scan.error_message = "Failed to initiate any scan jobs"

        self.db.commit()

        logger.info(
            f"Bulk scan {bulk_scan.id} initiated: {initiated_count} jobs queued, "
            f"{failed_count} failed"
        )

        return bulk_scan, jobs_info

    def get_bulk_scan_progress(self, bulk_scan_id: int) -> dict[str, Any]:
        """Get progress of a bulk scan operation.

        Args:
            bulk_scan_id: Bulk scan ID

        Returns:
            Progress information dictionary
        """
        bulk_scan = self.db.query(BulkScan).filter(BulkScan.id == bulk_scan_id).first()
        if not bulk_scan:
            raise ValueError(f"Bulk scan {bulk_scan_id} not found")

        # Note: In production, we would track job IDs from RQ
        # For now, we rely on ScanProgress records and database state

        return {
            "bulk_scan_id": bulk_scan.id,
            "status": bulk_scan.status,
            "total_applications": bulk_scan.total_applications,
            "completed_applications": bulk_scan.completed_applications,
            "failed_applications": bulk_scan.failed_applications,
            "total_policies_extracted": bulk_scan.total_policies_extracted,
            "total_files_scanned": bulk_scan.total_files_scanned,
            "average_scan_duration_seconds": bulk_scan.average_scan_duration_seconds,
            "started_at": bulk_scan.started_at,
            "completed_at": bulk_scan.completed_at,
            "created_at": bulk_scan.created_at,
        }

    def update_bulk_scan_from_job(
        self, bulk_scan_id: int, scan_result: dict[str, Any], success: bool
    ) -> None:
        """Update bulk scan progress from a completed job.

        Args:
            bulk_scan_id: Bulk scan ID
            scan_result: Scan result from worker
            success: Whether the scan succeeded
        """
        bulk_scan = self.db.query(BulkScan).filter(BulkScan.id == bulk_scan_id).first()
        if not bulk_scan:
            logger.error(f"Bulk scan {bulk_scan_id} not found")
            return

        # Update counters
        if success:
            bulk_scan.completed_applications += 1
            bulk_scan.total_policies_extracted += scan_result.get(
                "policies_extracted", 0
            )
            bulk_scan.total_files_scanned += scan_result.get("files_scanned", 0)
        else:
            bulk_scan.failed_applications += 1

        # Check if all jobs completed
        total_finished = bulk_scan.completed_applications + bulk_scan.failed_applications
        if total_finished >= bulk_scan.total_applications:
            bulk_scan.status = BulkScanStatus.COMPLETED
            bulk_scan.completed_at = datetime.utcnow()

            # Calculate average scan duration
            if bulk_scan.completed_applications > 0:
                duration = (bulk_scan.completed_at - bulk_scan.started_at).total_seconds()
                bulk_scan.average_scan_duration_seconds = int(
                    duration / bulk_scan.completed_applications
                )

            logger.info(
                f"Bulk scan {bulk_scan_id} completed: "
                f"{bulk_scan.completed_applications} succeeded, "
                f"{bulk_scan.failed_applications} failed, "
                f"{bulk_scan.total_policies_extracted} policies extracted"
            )

        self.db.commit()

    def list_bulk_scans(
        self, tenant_id: str | None, skip: int = 0, limit: int = 20
    ) -> list[BulkScan]:
        """List bulk scans for a tenant.

        Args:
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of BulkScan objects
        """
        query = self.db.query(BulkScan)
        if tenant_id:
            query = query.filter(BulkScan.tenant_id == tenant_id)

        return query.order_by(BulkScan.created_at.desc()).offset(skip).limit(limit).all()

    def cancel_bulk_scan(self, bulk_scan_id: int) -> None:
        """Cancel a running bulk scan.

        Args:
            bulk_scan_id: Bulk scan ID
        """
        bulk_scan = self.db.query(BulkScan).filter(BulkScan.id == bulk_scan_id).first()
        if not bulk_scan:
            raise ValueError(f"Bulk scan {bulk_scan_id} not found")

        if bulk_scan.status in [BulkScanStatus.COMPLETED, BulkScanStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel bulk scan with status {bulk_scan.status}")

        # Cancel all queued/running jobs
        # Note: Requires storing job IDs in bulk_scan for full implementation
        bulk_scan.status = BulkScanStatus.CANCELLED
        bulk_scan.completed_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Bulk scan {bulk_scan_id} cancelled")
