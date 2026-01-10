"""API endpoints for inconsistent enforcement detection."""
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.inconsistent_enforcement import (
    InconsistentEnforcementSeverity,
    InconsistentEnforcementStatus,
)
from app.schemas.inconsistent_enforcement import (
    DetectInconsistenciesResponse,
    InconsistentEnforcementResponse,
    InconsistentEnforcementStatusUpdate,
)
from app.services.inconsistent_enforcement_service import InconsistentEnforcementService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/detect", response_model=DetectInconsistenciesResponse)
async def detect_inconsistencies(
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)] = None,
) -> DetectInconsistenciesResponse:
    """Detect inconsistent policy enforcement across applications.

    This endpoint analyzes all policies across applications to find
    resources that are protected inconsistently (different authorization
    requirements in different apps).

    Returns:
        DetectInconsistenciesResponse with list of detected inconsistencies
    """
    logger.info("detect_inconsistencies_endpoint", tenant_id=tenant_id)

    service = InconsistentEnforcementService(db, tenant_id)
    inconsistencies = await service.detect_inconsistencies()

    return DetectInconsistenciesResponse(
        inconsistencies_found=len(inconsistencies),
        inconsistencies=[
            InconsistentEnforcementResponse.model_validate(inc) for inc in inconsistencies
        ],
    )


@router.get("/", response_model=list[InconsistentEnforcementResponse])
def list_inconsistencies(
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)] = None,
    status: InconsistentEnforcementStatus | None = Query(None, description="Filter by status"),
    severity: InconsistentEnforcementSeverity | None = Query(None, description="Filter by severity"),
) -> list[InconsistentEnforcementResponse]:
    """List all inconsistent enforcement records.

    Args:
        status: Optional status filter (pending, acknowledged, resolved, dismissed)
        severity: Optional severity filter (low, medium, high, critical)

    Returns:
        List of inconsistency records
    """
    logger.info("list_inconsistencies_endpoint", tenant_id=tenant_id, status=status, severity=severity)

    service = InconsistentEnforcementService(db, tenant_id)
    inconsistencies = service.get_all_inconsistencies(status=status, severity=severity)

    return [InconsistentEnforcementResponse.model_validate(inc) for inc in inconsistencies]


@router.get("/{inconsistency_id}", response_model=InconsistentEnforcementResponse)
def get_inconsistency(
    inconsistency_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)] = None,
) -> InconsistentEnforcementResponse:
    """Get a specific inconsistency by ID.

    Args:
        inconsistency_id: Inconsistency ID

    Returns:
        InconsistentEnforcementResponse

    Raises:
        HTTPException: 404 if inconsistency not found
    """
    service = InconsistentEnforcementService(db, tenant_id)
    inconsistency = service.get_inconsistency(inconsistency_id)

    if not inconsistency:
        raise HTTPException(status_code=404, detail="Inconsistency not found")

    return InconsistentEnforcementResponse.model_validate(inconsistency)


@router.put("/{inconsistency_id}/status", response_model=InconsistentEnforcementResponse)
def update_inconsistency_status(
    inconsistency_id: int,
    status_update: InconsistentEnforcementStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)] = None,
) -> InconsistentEnforcementResponse:
    """Update inconsistency status.

    Args:
        inconsistency_id: Inconsistency ID
        status_update: Status update data

    Returns:
        Updated InconsistentEnforcementResponse

    Raises:
        HTTPException: 404 if inconsistency not found
    """
    logger.info(
        "update_inconsistency_status",
        inconsistency_id=inconsistency_id,
        status=status_update.status,
    )

    service = InconsistentEnforcementService(db, tenant_id)
    inconsistency = service.update_status(
        inconsistency_id=inconsistency_id,
        status=status_update.status,
        resolution_notes=status_update.resolution_notes,
        resolved_by=status_update.resolved_by,
    )

    if not inconsistency:
        raise HTTPException(status_code=404, detail="Inconsistency not found")

    return InconsistentEnforcementResponse.model_validate(inconsistency)


@router.delete("/{inconsistency_id}", status_code=204)
def delete_inconsistency(
    inconsistency_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)] = None,
) -> None:
    """Delete an inconsistency record.

    Args:
        inconsistency_id: Inconsistency ID

    Raises:
        HTTPException: 404 if inconsistency not found
    """
    logger.info("delete_inconsistency", inconsistency_id=inconsistency_id)

    service = InconsistentEnforcementService(db, tenant_id)
    success = service.delete_inconsistency(inconsistency_id)

    if not success:
        raise HTTPException(status_code=404, detail="Inconsistency not found")
