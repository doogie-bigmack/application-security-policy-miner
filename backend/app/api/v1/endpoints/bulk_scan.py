"""Bulk scan API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id as get_current_tenant_id
from app.schemas.bulk_scan import (
    BulkScanJobInfo,
    BulkScanProgress,
    BulkScanRequest,
    BulkScanResponse,
)
from app.services.bulk_scan_service import BulkScanService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=BulkScanResponse)
async def initiate_bulk_scan(
    request: BulkScanRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_current_tenant_id),
):
    """Initiate a bulk scan operation for multiple repositories.

    Args:
        request: Bulk scan request with repository IDs
        db: Database session
        tenant_id: Tenant ID from auth

    Returns:
        Bulk scan response with job information
    """
    logger.info(
        f"Initiating bulk scan for {len(request.repository_ids)} repositories",
        tenant_id=tenant_id,
    )

    try:
        service = BulkScanService(db)
        bulk_scan, jobs_info = service.initiate_bulk_scan(
            repository_ids=request.repository_ids,
            tenant_id=tenant_id,
            incremental=request.incremental,
            max_parallel_workers=request.max_parallel_workers,
        )

        # Convert jobs_info to schema
        jobs = [
            BulkScanJobInfo(
                repository_id=job["repository_id"],
                repository_name=job["repository_name"],
                job_id=job["job_id"],
                status=job["status"],
            )
            for job in jobs_info
        ]

        return BulkScanResponse(
            bulk_scan_id=bulk_scan.id,
            total_applications=bulk_scan.total_applications,
            initiated_scans=len(jobs),
            failed_initiations=bulk_scan.total_applications - len(jobs),
            max_parallel_workers=bulk_scan.max_parallel_workers,
            jobs=jobs,
        )

    except Exception as e:
        logger.error(f"Failed to initiate bulk scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{bulk_scan_id}", response_model=BulkScanProgress)
async def get_bulk_scan_progress(
    bulk_scan_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_current_tenant_id),
):
    """Get progress of a bulk scan operation.

    Args:
        bulk_scan_id: Bulk scan ID
        db: Database session
        tenant_id: Tenant ID from auth

    Returns:
        Bulk scan progress
    """
    try:
        service = BulkScanService(db)
        progress = service.get_bulk_scan_progress(bulk_scan_id)

        # Verify tenant access if tenant_id provided
        if tenant_id and progress.get("tenant_id") != tenant_id:
            raise HTTPException(status_code=404, detail="Bulk scan not found")

        return BulkScanProgress(**progress)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get bulk scan progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[BulkScanProgress])
async def list_bulk_scans(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_current_tenant_id),
):
    """List bulk scans for the current tenant.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        tenant_id: Tenant ID from auth

    Returns:
        List of bulk scan progress records
    """
    try:
        service = BulkScanService(db)
        bulk_scans = service.list_bulk_scans(tenant_id, skip, limit)

        return [
            BulkScanProgress(
                bulk_scan_id=bs.id,
                status=bs.status,
                total_applications=bs.total_applications,
                completed_applications=bs.completed_applications,
                failed_applications=bs.failed_applications,
                total_policies_extracted=bs.total_policies_extracted,
                total_files_scanned=bs.total_files_scanned,
                average_scan_duration_seconds=bs.average_scan_duration_seconds,
                started_at=bs.started_at,
                completed_at=bs.completed_at,
                created_at=bs.created_at,
            )
            for bs in bulk_scans
        ]

    except Exception as e:
        logger.error(f"Failed to list bulk scans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{bulk_scan_id}")
async def cancel_bulk_scan(
    bulk_scan_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_current_tenant_id),
):
    """Cancel a running bulk scan operation.

    Args:
        bulk_scan_id: Bulk scan ID
        db: Database session
        tenant_id: Tenant ID from auth

    Returns:
        Success message
    """
    try:
        service = BulkScanService(db)
        service.cancel_bulk_scan(bulk_scan_id)

        return {"status": "success", "message": f"Bulk scan {bulk_scan_id} cancelled"}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to cancel bulk scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
