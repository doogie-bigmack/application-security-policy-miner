"""Migration wave endpoints."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.migration_wave import MigrationWaveStatus
from app.schemas.migration_wave import (
    MigrationWaveApplicationAdd,
    MigrationWaveApplicationRemove,
    MigrationWaveCreate,
    MigrationWaveProgressUpdate,
    MigrationWaveReport,
    MigrationWaveResponse,
    MigrationWaveUpdate,
    MigrationWaveWithApplications,
)
from app.services.migration_wave_service import MigrationWaveService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=MigrationWaveResponse, status_code=201)
def create_migration_wave(
    wave_data: MigrationWaveCreate,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> MigrationWaveResponse:
    """Create a new migration wave."""
    wave = MigrationWaveService.create_wave(db, wave_data, tenant_id or "default")
    return MigrationWaveResponse.model_validate(wave)


@router.get("/", response_model=list[MigrationWaveResponse])
def list_migration_waves(
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
    status: MigrationWaveStatus | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[MigrationWaveResponse]:
    """List migration waves."""
    waves = MigrationWaveService.list_waves(db, tenant_id or "default", status, skip, limit)
    return [MigrationWaveResponse.model_validate(wave) for wave in waves]


@router.get("/{wave_id}", response_model=MigrationWaveWithApplications)
def get_migration_wave(
    wave_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> MigrationWaveWithApplications:
    """Get a migration wave by ID."""
    wave = MigrationWaveService.get_wave(db, wave_id, tenant_id or "default")
    if not wave:
        raise HTTPException(status_code=404, detail="Migration wave not found")

    # Get application IDs
    app_ids = [app.id for app in wave.applications]

    response_data = MigrationWaveResponse.model_validate(wave).model_dump()
    response_data["application_ids"] = app_ids

    return MigrationWaveWithApplications(**response_data)


@router.patch("/{wave_id}", response_model=MigrationWaveResponse)
def update_migration_wave(
    wave_id: int,
    wave_data: MigrationWaveUpdate,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> MigrationWaveResponse:
    """Update a migration wave."""
    wave = MigrationWaveService.update_wave(db, wave_id, tenant_id or "default", wave_data)
    if not wave:
        raise HTTPException(status_code=404, detail="Migration wave not found")

    return MigrationWaveResponse.model_validate(wave)


@router.delete("/{wave_id}", status_code=204)
def delete_migration_wave(
    wave_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> None:
    """Delete a migration wave."""
    success = MigrationWaveService.delete_wave(db, wave_id, tenant_id or "default")
    if not success:
        raise HTTPException(status_code=404, detail="Migration wave not found")


@router.post("/{wave_id}/applications", response_model=MigrationWaveResponse)
def add_applications_to_wave(
    wave_id: int,
    data: MigrationWaveApplicationAdd,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> MigrationWaveResponse:
    """Add applications to a migration wave."""
    wave = MigrationWaveService.add_applications(
        db, wave_id, tenant_id or "default", data.application_ids
    )
    if not wave:
        raise HTTPException(status_code=404, detail="Migration wave not found")

    return MigrationWaveResponse.model_validate(wave)


@router.delete("/{wave_id}/applications", response_model=MigrationWaveResponse)
def remove_applications_from_wave(
    wave_id: int,
    data: MigrationWaveApplicationRemove,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> MigrationWaveResponse:
    """Remove applications from a migration wave."""
    wave = MigrationWaveService.remove_applications(
        db, wave_id, tenant_id or "default", data.application_ids
    )
    if not wave:
        raise HTTPException(status_code=404, detail="Migration wave not found")

    return MigrationWaveResponse.model_validate(wave)


@router.patch("/{wave_id}/progress", response_model=MigrationWaveResponse)
def update_wave_progress(
    wave_id: int,
    data: MigrationWaveProgressUpdate,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> MigrationWaveResponse:
    """Update migration wave progress."""
    wave = MigrationWaveService.update_progress(
        db,
        wave_id,
        tenant_id or "default",
        data.scanned_applications,
        data.provisioned_applications,
    )
    if not wave:
        raise HTTPException(status_code=404, detail="Migration wave not found")

    return MigrationWaveResponse.model_validate(wave)


@router.get("/{wave_id}/report", response_model=MigrationWaveReport)
def get_wave_report(
    wave_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> MigrationWaveReport:
    """Generate completion report for a migration wave."""
    report = MigrationWaveService.generate_report(db, wave_id, tenant_id or "default")
    if not report:
        raise HTTPException(status_code=404, detail="Migration wave not found")

    return report
