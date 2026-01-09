"""Auto-approval API endpoints."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.schemas.auto_approval import (
    AutoApprovalDecision,
    AutoApprovalMetrics,
    AutoApprovalSettings,
    AutoApprovalSettingsUpdate,
)
from app.services.auto_approval_service import AutoApprovalService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/settings", response_model=AutoApprovalSettings)
def get_auto_approval_settings(
    tenant_id: str | None = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> AutoApprovalSettings:
    """Get auto-approval settings for tenant."""
    service = AutoApprovalService(db)
    settings = service.get_or_create_settings(tenant_id)
    return settings


@router.put("/settings", response_model=AutoApprovalSettings)
def update_auto_approval_settings(
    update: AutoApprovalSettingsUpdate,
    tenant_id: str | None = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> AutoApprovalSettings:
    """Update auto-approval settings."""
    service = AutoApprovalService(db)
    settings = service.update_settings(
        tenant_id=tenant_id,
        enabled=update.enabled,
        risk_threshold=update.risk_threshold,
        min_historical_approvals=update.min_historical_approvals,
    )
    logger.info(f"Updated auto-approval settings for tenant {tenant_id or 'default-tenant'}")
    return settings


@router.get("/metrics", response_model=AutoApprovalMetrics)
def get_auto_approval_metrics(
    tenant_id: str | None = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> AutoApprovalMetrics:
    """Get auto-approval metrics."""
    service = AutoApprovalService(db)
    metrics = service.get_metrics(tenant_id)
    return AutoApprovalMetrics(**metrics)


@router.get("/decisions", response_model=list[AutoApprovalDecision])
def get_auto_approval_decisions(
    limit: int = 100,
    tenant_id: str | None = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> list[AutoApprovalDecision]:
    """Get recent auto-approval decisions."""
    service = AutoApprovalService(db)
    decisions = service.get_decisions(tenant_id, limit=limit)
    return decisions
