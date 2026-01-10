"""API endpoints for secret detection logs."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.secret_detection import SecretDetectionLog
from app.schemas.secret_detection import SecretDetectionLogResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[SecretDetectionLogResponse])
def list_secret_logs(
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)] = None,
    repository_id: Annotated[int | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[SecretDetectionLog]:
    """List secret detection logs.

    Args:
        db: Database session
        tenant_id: Optional tenant ID for filtering
        repository_id: Optional repository ID for filtering
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of secret detection logs
    """
    query = db.query(SecretDetectionLog)

    # Apply tenant filtering if authenticated
    if tenant_id:
        query = query.filter(SecretDetectionLog.tenant_id == tenant_id)

    # Apply repository filtering
    if repository_id:
        query = query.filter(SecretDetectionLog.repository_id == repository_id)

    # Order by most recent first
    query = query.order_by(SecretDetectionLog.detected_at.desc())

    # Apply pagination
    logs = query.offset(skip).limit(limit).all()

    return logs


@router.get("/{log_id}", response_model=SecretDetectionLogResponse)
def get_secret_log(
    log_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)] = None,
) -> SecretDetectionLog:
    """Get a specific secret detection log.

    Args:
        log_id: ID of the log
        db: Database session
        tenant_id: Optional tenant ID for filtering

    Returns:
        Secret detection log

    Raises:
        HTTPException: If log not found or access denied
    """
    query = db.query(SecretDetectionLog).filter(SecretDetectionLog.id == log_id)

    # Apply tenant filtering if authenticated
    if tenant_id:
        query = query.filter(SecretDetectionLog.tenant_id == tenant_id)

    log = query.first()

    if not log:
        raise HTTPException(status_code=404, detail="Secret detection log not found")

    return log


@router.delete("/{log_id}")
def delete_secret_log(
    log_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)] = None,
) -> dict[str, str]:
    """Delete a secret detection log.

    Args:
        log_id: ID of the log to delete
        db: Database session
        tenant_id: Optional tenant ID for filtering

    Returns:
        Success message

    Raises:
        HTTPException: If log not found or access denied
    """
    query = db.query(SecretDetectionLog).filter(SecretDetectionLog.id == log_id)

    # Apply tenant filtering if authenticated
    if tenant_id:
        query = query.filter(SecretDetectionLog.tenant_id == tenant_id)

    log = query.first()

    if not log:
        raise HTTPException(status_code=404, detail="Secret detection log not found")

    db.delete(log)
    db.commit()

    return {"message": "Secret detection log deleted successfully"}
