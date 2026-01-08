"""Scan progress API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.scan_progress import ScanProgress
from app.schemas.scan_progress import ScanProgress as ScanProgressSchema

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/repository/{repository_id}/latest", response_model=ScanProgressSchema)
def get_latest_scan_progress(
    repository_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Get the latest scan progress for a repository.

    Args:
        repository_id: Repository ID
        db: Database session
        tenant_id: Optional tenant ID for multi-tenancy

    Returns:
        Latest scan progress
    """
    query = db.query(ScanProgress).filter(ScanProgress.repository_id == repository_id)

    if tenant_id:
        query = query.filter(ScanProgress.tenant_id == tenant_id)

    scan_progress = query.order_by(ScanProgress.created_at.desc()).first()

    if not scan_progress:
        raise HTTPException(status_code=404, detail="No scan progress found for this repository")

    return scan_progress


@router.get("/{scan_id}", response_model=ScanProgressSchema)
def get_scan_progress(
    scan_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Get scan progress by ID.

    Args:
        scan_id: Scan progress ID
        db: Database session
        tenant_id: Optional tenant ID for multi-tenancy

    Returns:
        Scan progress
    """
    query = db.query(ScanProgress).filter(ScanProgress.id == scan_id)

    if tenant_id:
        query = query.filter(ScanProgress.tenant_id == tenant_id)

    scan_progress = query.first()

    if not scan_progress:
        raise HTTPException(status_code=404, detail="Scan progress not found")

    return scan_progress
