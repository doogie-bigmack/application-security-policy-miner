"""Audit logs API endpoints."""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.schemas.audit_log import AuditLog, AuditLogList
from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.audit_log import AuditEventType
from app.models.audit_log import AuditLog as AuditLogModel

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=AuditLogList)
def list_audit_logs(
    event_type: AuditEventType | None = Query(None, description="Filter by event type"),
    user_email: str | None = Query(None, description="Filter by user email"),
    repository_id: int | None = Query(None, description="Filter by repository ID"),
    policy_id: int | None = Query(None, description="Filter by policy ID"),
    conflict_id: int | None = Query(None, description="Filter by conflict ID"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    tenant_id: int | None = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> AuditLogList:
    """List audit logs with optional filtering.

    This endpoint returns all audit log entries for the authenticated tenant.
    Logs include AI prompts, AI responses, user decisions, and system operations.

    Args:
        event_type: Filter by event type
        user_email: Filter by user email
        repository_id: Filter by repository ID
        policy_id: Filter by policy ID
        conflict_id: Filter by conflict ID
        start_date: Filter by start date (inclusive)
        end_date: Filter by end date (inclusive)
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        tenant_id: Authenticated tenant ID
        db: Database session

    Returns:
        List of audit log entries with total count
    """
    try:
        query = db.query(AuditLogModel)

        # Apply tenant filter
        if tenant_id is not None:
            query = query.filter(AuditLogModel.tenant_id == tenant_id)

        # Apply filters
        if event_type:
            query = query.filter(AuditLogModel.event_type == event_type)
        if user_email:
            query = query.filter(AuditLogModel.user_email == user_email)
        if repository_id:
            query = query.filter(AuditLogModel.repository_id == repository_id)
        if policy_id:
            query = query.filter(AuditLogModel.policy_id == policy_id)
        if conflict_id:
            query = query.filter(AuditLogModel.conflict_id == conflict_id)
        if start_date:
            query = query.filter(AuditLogModel.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLogModel.created_at <= end_date)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        logs = query.order_by(AuditLogModel.created_at.desc()).offset(skip).limit(limit).all()

        logger.info(
            "audit_logs_listed",
            tenant_id=tenant_id,
            total=total,
            returned=len(logs),
            event_type=event_type.value if event_type else None,
        )

        return AuditLogList(total=total, items=logs)

    except Exception as e:
        logger.error("failed_to_list_audit_logs", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve audit logs")


@router.get("/{audit_log_id}", response_model=AuditLog)
def get_audit_log(
    audit_log_id: int,
    tenant_id: int | None = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> AuditLog:
    """Get a specific audit log entry by ID.

    Args:
        audit_log_id: ID of the audit log entry
        tenant_id: Authenticated tenant ID
        db: Database session

    Returns:
        Audit log entry

    Raises:
        HTTPException: If audit log not found or access denied
    """
    try:
        query = db.query(AuditLogModel).filter(AuditLogModel.id == audit_log_id)

        # Apply tenant filter
        if tenant_id is not None:
            query = query.filter(AuditLogModel.tenant_id == tenant_id)

        log = query.first()

        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")

        logger.info("audit_log_retrieved", audit_log_id=audit_log_id, tenant_id=tenant_id)

        return log

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_get_audit_log",
            error=str(e),
            audit_log_id=audit_log_id,
            tenant_id=tenant_id,
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve audit log")


@router.delete("/{audit_log_id}")
def delete_audit_log(
    audit_log_id: int,
    tenant_id: int | None = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> dict:
    """Delete an audit log entry.

    Note: Deleting audit logs should be rare and only done for compliance reasons
    (e.g., GDPR data deletion requests). All deletions are themselves logged.

    Args:
        audit_log_id: ID of the audit log entry to delete
        tenant_id: Authenticated tenant ID
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If audit log not found or access denied
    """
    try:
        query = db.query(AuditLogModel).filter(AuditLogModel.id == audit_log_id)

        # Apply tenant filter
        if tenant_id is not None:
            query = query.filter(AuditLogModel.tenant_id == tenant_id)

        log = query.first()

        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")

        db.delete(log)
        db.commit()

        logger.warning(
            "audit_log_deleted",
            audit_log_id=audit_log_id,
            tenant_id=tenant_id,
            event_type=log.event_type.value,
        )

        return {"message": "Audit log deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_delete_audit_log",
            error=str(e),
            audit_log_id=audit_log_id,
            tenant_id=tenant_id,
        )
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete audit log")


@router.get("/export/csv")
def export_audit_logs_csv(
    event_type: AuditEventType | None = Query(None, description="Filter by event type"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    tenant_id: int | None = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> dict:
    """Export audit logs as CSV for compliance reporting.

    Args:
        event_type: Filter by event type
        start_date: Filter by start date
        end_date: Filter by end date
        tenant_id: Authenticated tenant ID
        db: Database session

    Returns:
        CSV export information (placeholder - actual CSV generation would be implemented)
    """
    try:
        query = db.query(AuditLogModel)

        # Apply tenant filter
        if tenant_id is not None:
            query = query.filter(AuditLogModel.tenant_id == tenant_id)

        # Apply filters
        if event_type:
            query = query.filter(AuditLogModel.event_type == event_type)
        if start_date:
            query = query.filter(AuditLogModel.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLogModel.created_at <= end_date)

        total = query.count()

        logger.info("audit_logs_export_requested", tenant_id=tenant_id, total=total)

        # In a real implementation, this would generate and return a CSV file
        return {
            "message": "CSV export functionality placeholder",
            "total_records": total,
            "filters": {
                "event_type": event_type.value if event_type else None,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        }

    except Exception as e:
        logger.error("failed_to_export_audit_logs", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to export audit logs")
