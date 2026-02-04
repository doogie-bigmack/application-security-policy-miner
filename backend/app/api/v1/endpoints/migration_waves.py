"""Migration wave endpoints."""
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.migration_wave import MigrationWaveStatus
from app.models.repository import Repository
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
from app.tasks.scan_tasks import bulk_scan_repositories_task

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


@router.get("/velocity-comparison", response_model=list[MigrationWaveReport])
def get_velocity_comparison(
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
    status: MigrationWaveStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of waves to compare"),
) -> list[MigrationWaveReport]:
    """Get velocity comparison across migration waves for analysis."""
    # Get waves
    waves = MigrationWaveService.list_waves(
        db, tenant_id or "default", status=status, skip=0, limit=limit
    )

    # Generate reports for each wave
    reports = []
    for wave in waves:
        report = MigrationWaveService.generate_report(db, wave.id, tenant_id or "default")
        if report:
            reports.append(report)

    # Sort by completion time (most recent first)
    reports.sort(
        key=lambda r: r.completed_at if r.completed_at else r.started_at if r.started_at else "",
        reverse=True,
    )

    return reports


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


@router.post("/{wave_id}/scan", status_code=202)
def start_wave_scan(
    wave_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
    incremental: bool = Query(False, description="If True, only scan changed files"),
    batch_size: int = Query(50, ge=1, le=100, description="Number of repos per batch"),
) -> dict[str, Any]:
    """Start bulk scanning all repositories for applications in this wave."""
    wave = MigrationWaveService.get_wave(db, wave_id, tenant_id or "default")
    if not wave:
        raise HTTPException(status_code=404, detail="Migration wave not found")

    # Get all application IDs in wave
    app_ids = [app.id for app in wave.applications]

    if not app_ids:
        raise HTTPException(status_code=400, detail="No applications in wave to scan")

    # Get all repositories associated with these applications
    repositories = (
        db.query(Repository)
        .filter(
            Repository.application_id.in_(app_ids),
            Repository.tenant_id == (tenant_id or "default"),
        )
        .all()
    )

    if not repositories:
        raise HTTPException(status_code=404, detail="No repositories found for wave applications")

    repository_ids = [r.id for r in repositories]

    # Update wave status to in_progress
    if wave.status == MigrationWaveStatus.PLANNED:
        from datetime import UTC, datetime
        wave.status = MigrationWaveStatus.IN_PROGRESS
        wave.started_at = datetime.now(UTC)
        db.commit()

    # Spawn bulk scan task
    task = bulk_scan_repositories_task.apply_async(
        kwargs={
            "repository_ids": repository_ids,
            "tenant_id": tenant_id or "default",
            "incremental": incremental,
            "batch_size": batch_size,
        }
    )

    logger.info(
        "Wave scan started",
        extra={
            "wave_id": wave_id,
            "wave_name": wave.name,
            "task_id": task.id,
            "repository_count": len(repository_ids),
            "application_count": len(app_ids),
        },
    )

    return {
        "task_id": task.id,
        "wave_id": wave_id,
        "wave_name": wave.name,
        "repository_count": len(repository_ids),
        "application_count": len(app_ids),
        "status": "Scan queued",
    }
