"""Migration wave service for managing phased rollout."""
import logging
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.application import Application
from app.models.conflict import ConflictStatus, PolicyConflict
from app.models.migration_wave import MigrationWave, MigrationWaveStatus
from app.models.policy import Policy, RiskLevel
from app.models.provisioning import ProvisioningOperation, ProvisioningStatus
from app.schemas.migration_wave import (
    MigrationWaveCreate,
    MigrationWaveReport,
    MigrationWaveUpdate,
)

logger = logging.getLogger(__name__)


class MigrationWaveService:
    """Service for managing migration waves."""

    @staticmethod
    def create_wave(
        db: Session,
        wave_data: MigrationWaveCreate,
        tenant_id: str,
    ) -> MigrationWave:
        """Create a new migration wave."""
        # Create wave
        wave = MigrationWave(
            name=wave_data.name,
            description=wave_data.description,
            tenant_id=tenant_id,
            status=MigrationWaveStatus.PLANNED,
            total_applications=len(wave_data.application_ids),
        )

        db.add(wave)
        db.flush()

        # Add applications to wave
        if wave_data.application_ids:
            applications = (
                db.query(Application)
                .filter(
                    Application.id.in_(wave_data.application_ids),
                    Application.tenant_id == tenant_id,
                )
                .all()
            )

            wave.applications.extend(applications)
            wave.total_applications = len(applications)

        db.commit()
        db.refresh(wave)

        logger.info(
            "Created migration wave",
            extra={
                "wave_id": wave.id,
                "wave_name": wave.name,
                "tenant_id": tenant_id,
                "total_applications": wave.total_applications,
            },
        )

        return wave

    @staticmethod
    def get_wave(
        db: Session,
        wave_id: int,
        tenant_id: str,
    ) -> MigrationWave | None:
        """Get a migration wave by ID."""
        return (
            db.query(MigrationWave)
            .options(selectinload(MigrationWave.applications))
            .filter(
                MigrationWave.id == wave_id,
                MigrationWave.tenant_id == tenant_id,
            )
            .first()
        )

    @staticmethod
    def list_waves(
        db: Session,
        tenant_id: str,
        status: MigrationWaveStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MigrationWave]:
        """List migration waves."""
        query = db.query(MigrationWave).filter(MigrationWave.tenant_id == tenant_id)

        if status:
            query = query.filter(MigrationWave.status == status)

        return query.order_by(MigrationWave.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_wave(
        db: Session,
        wave_id: int,
        tenant_id: str,
        wave_data: MigrationWaveUpdate,
    ) -> MigrationWave | None:
        """Update a migration wave."""
        wave = MigrationWaveService.get_wave(db, wave_id, tenant_id)
        if not wave:
            return None

        update_dict = wave_data.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            setattr(wave, key, value)

        # Update timestamps based on status
        if wave_data.status:
            if wave_data.status == MigrationWaveStatus.IN_PROGRESS and not wave.started_at:
                wave.started_at = datetime.now(UTC)
            elif wave_data.status == MigrationWaveStatus.COMPLETED and not wave.completed_at:
                wave.completed_at = datetime.now(UTC)

        db.commit()
        db.refresh(wave)

        logger.info(
            "Updated migration wave",
            extra={
                "wave_id": wave.id,
                "wave_name": wave.name,
                "tenant_id": tenant_id,
                "updates": update_dict,
            },
        )

        return wave

    @staticmethod
    def delete_wave(
        db: Session,
        wave_id: int,
        tenant_id: str,
    ) -> bool:
        """Delete a migration wave."""
        wave = MigrationWaveService.get_wave(db, wave_id, tenant_id)
        if not wave:
            return False

        db.delete(wave)
        db.commit()

        logger.info(
            "Deleted migration wave",
            extra={
                "wave_id": wave_id,
                "wave_name": wave.name,
                "tenant_id": tenant_id,
            },
        )

        return True

    @staticmethod
    def add_applications(
        db: Session,
        wave_id: int,
        tenant_id: str,
        application_ids: list[int],
    ) -> MigrationWave | None:
        """Add applications to a migration wave."""
        wave = MigrationWaveService.get_wave(db, wave_id, tenant_id)
        if not wave:
            return None

        # Get applications
        applications = (
            db.query(Application)
            .filter(
                Application.id.in_(application_ids),
                Application.tenant_id == tenant_id,
            )
            .all()
        )

        # Add only new applications (avoid duplicates)
        existing_ids = {app.id for app in wave.applications}
        new_applications = [app for app in applications if app.id not in existing_ids]

        wave.applications.extend(new_applications)
        wave.total_applications = len(wave.applications)

        db.commit()
        db.refresh(wave)

        logger.info(
            "Added applications to wave",
            extra={
                "wave_id": wave.id,
                "tenant_id": tenant_id,
                "applications_added": len(new_applications),
                "total_applications": wave.total_applications,
            },
        )

        return wave

    @staticmethod
    def remove_applications(
        db: Session,
        wave_id: int,
        tenant_id: str,
        application_ids: list[int],
    ) -> MigrationWave | None:
        """Remove applications from a migration wave."""
        wave = MigrationWaveService.get_wave(db, wave_id, tenant_id)
        if not wave:
            return None

        # Remove applications
        wave.applications = [app for app in wave.applications if app.id not in application_ids]
        wave.total_applications = len(wave.applications)

        db.commit()
        db.refresh(wave)

        logger.info(
            "Removed applications from wave",
            extra={
                "wave_id": wave.id,
                "tenant_id": tenant_id,
                "applications_removed": len(application_ids),
                "total_applications": wave.total_applications,
            },
        )

        return wave

    @staticmethod
    def update_progress(
        db: Session,
        wave_id: int,
        tenant_id: str,
        scanned_applications: int | None = None,
        provisioned_applications: int | None = None,
    ) -> MigrationWave | None:
        """Update wave progress."""
        wave = MigrationWaveService.get_wave(db, wave_id, tenant_id)
        if not wave:
            return None

        if scanned_applications is not None:
            wave.scanned_applications = min(scanned_applications, wave.total_applications)

        if provisioned_applications is not None:
            wave.provisioned_applications = min(provisioned_applications, wave.total_applications)

        # Auto-complete wave if all applications are provisioned
        if wave.provisioned_applications >= wave.total_applications and wave.total_applications > 0:
            wave.status = MigrationWaveStatus.COMPLETED
            if not wave.completed_at:
                wave.completed_at = datetime.now(UTC)

        db.commit()
        db.refresh(wave)

        return wave

    @staticmethod
    def generate_report(
        db: Session,
        wave_id: int,
        tenant_id: str,
    ) -> MigrationWaveReport | None:
        """Generate completion report for a migration wave."""
        wave = MigrationWaveService.get_wave(db, wave_id, tenant_id)
        if not wave:
            return None

        # Get application IDs in this wave
        app_ids = [app.id for app in wave.applications]

        # Count total policies extracted
        policies_extracted = (
            db.query(func.count(Policy.id))
            .filter(
                Policy.application_id.in_(app_ids),
                Policy.tenant_id == tenant_id,
            )
            .scalar()
            or 0
        )

        # Count provisioned policies
        policies_provisioned = (
            db.query(func.count(ProvisioningOperation.id.distinct()))
            .filter(
                ProvisioningOperation.policy_id.in_(
                    db.query(Policy.id).filter(
                        Policy.application_id.in_(app_ids),
                        Policy.tenant_id == tenant_id,
                    )
                ),
                ProvisioningOperation.status == ProvisioningStatus.SUCCESS,
            )
            .scalar()
            or 0
        )

        # Count high-risk policies
        high_risk_policies = (
            db.query(func.count(Policy.id))
            .filter(
                Policy.application_id.in_(app_ids),
                Policy.tenant_id == tenant_id,
                Policy.risk_level == RiskLevel.HIGH,
            )
            .scalar()
            or 0
        )

        # Count conflicts detected
        conflicts_detected = (
            db.query(func.count(PolicyConflict.id))
            .filter(
                PolicyConflict.policy_a_id.in_(
                    db.query(Policy.id).filter(
                        Policy.application_id.in_(app_ids),
                        Policy.tenant_id == tenant_id,
                    )
                ),
                PolicyConflict.status != ConflictStatus.RESOLVED,
            )
            .scalar()
            or 0
        )

        # Calculate duration
        duration_minutes = None
        if wave.started_at and wave.completed_at:
            duration = wave.completed_at - wave.started_at
            duration_minutes = duration.total_seconds() / 60

        return MigrationWaveReport(
            wave_id=wave.id,
            wave_name=wave.name,
            status=wave.status,
            total_applications=wave.total_applications,
            scanned_applications=wave.scanned_applications,
            provisioned_applications=wave.provisioned_applications,
            progress_percentage=wave.progress_percentage,
            provisioned_percentage=wave.provisioned_percentage,
            started_at=wave.started_at,
            completed_at=wave.completed_at,
            duration_minutes=duration_minutes,
            policies_extracted=policies_extracted,
            policies_provisioned=policies_provisioned,
            high_risk_policies=high_risk_policies,
            conflicts_detected=conflicts_detected,
        )
