"""API endpoints for application management."""
import csv
import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.application import Application, CriticalityLevel
from app.models.organization import BusinessUnit
from app.models.policy import Policy, RiskLevel, SourceType
from app.schemas.application import (
    ApplicationCreate,
    ApplicationImportResult,
    ApplicationResponse,
    ApplicationUpdate,
    ApplicationWithPolicies,
)
from app.schemas.policy import Policy as PolicySchema

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ApplicationResponse, status_code=201)
def create_application(
    application: ApplicationCreate,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> Application:
    """Create a new application.

    Args:
        application: Application data
        db: Database session
        tenant_id: Tenant ID from auth context

    Returns:
        Created application

    Raises:
        HTTPException: If business unit not found
    """
    # Verify business unit exists
    business_unit = db.query(BusinessUnit).filter(BusinessUnit.id == application.business_unit_id).first()
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")

    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"

    db_application = Application(
        **application.model_dump(),
        tenant_id=effective_tenant_id,
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)

    logger.info(
        "application_created",
        application_id=db_application.id,
        name=db_application.name,
        tenant_id=tenant_id,
    )

    return db_application


@router.get("/", response_model=list[ApplicationResponse])
def list_applications(
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    criticality: CriticalityLevel | None = None,
    business_unit_id: int | None = None,
    division_id: int | None = None,
    search: str | None = None,
) -> list[Application]:
    """List applications with filtering.

    Args:
        db: Database session
        tenant_id: Tenant ID from auth context
        skip: Number of records to skip
        limit: Maximum number of records to return
        criticality: Filter by criticality level
        business_unit_id: Filter by business unit
        division_id: Filter by division (all business units in division)
        search: Search in name, description, tech_stack, owner

    Returns:
        List of applications
    """
    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"
    query = db.query(Application).filter(Application.tenant_id == effective_tenant_id)

    # Apply filters
    if criticality:
        query = query.filter(Application.criticality == criticality)

    if business_unit_id:
        query = query.filter(Application.business_unit_id == business_unit_id)

    # Filter by division (join with BusinessUnit)
    if division_id:
        query = query.join(BusinessUnit).filter(BusinessUnit.division_id == division_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Application.name.ilike(search_pattern),
                Application.description.ilike(search_pattern),
                Application.tech_stack.ilike(search_pattern),
                Application.owner.ilike(search_pattern),
            )
        )

    applications = query.order_by(Application.name).offset(skip).limit(limit).all()
    return applications


@router.get("/count", response_model=dict)
def count_applications(
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
    criticality: CriticalityLevel | None = None,
    business_unit_id: int | None = None,
    division_id: int | None = None,
    search: str | None = None,
) -> dict:
    """Get count of applications with optional filters.

    Args:
        db: Database session
        tenant_id: Tenant ID from auth context
        criticality: Filter by criticality level
        business_unit_id: Filter by business unit
        division_id: Filter by division (all business units in division)
        search: Search in name, description, tech_stack, owner

    Returns:
        Dictionary with count
    """
    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"

    # Build base query - if division_id is set, we need to join from the start
    if division_id:
        query = (
            db.query(func.count(Application.id))
            .select_from(Application)
            .join(BusinessUnit)
            .filter(
                Application.tenant_id == effective_tenant_id,
                BusinessUnit.division_id == division_id
            )
        )
    else:
        query = db.query(func.count(Application.id)).filter(Application.tenant_id == effective_tenant_id)

    # Apply same filters as list endpoint
    if criticality:
        query = query.filter(Application.criticality == criticality)

    if business_unit_id:
        query = query.filter(Application.business_unit_id == business_unit_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Application.name.ilike(search_pattern),
                Application.description.ilike(search_pattern),
                Application.tech_stack.ilike(search_pattern),
                Application.owner.ilike(search_pattern),
            )
        )

    count = query.scalar()
    return {"count": count}


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> Application:
    """Get a specific application.

    Args:
        application_id: ID of the application
        db: Database session
        tenant_id: Tenant ID from auth context

    Returns:
        Application

    Raises:
        HTTPException: If application not found
    """
    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"
    application = (
        db.query(Application)
        .filter(Application.id == application_id, Application.tenant_id == effective_tenant_id)
        .first()
    )

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    application_update: ApplicationUpdate,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> Application:
    """Update an application.

    Args:
        application_id: ID of the application
        application_update: Application update data
        db: Database session
        tenant_id: Tenant ID from auth context

    Returns:
        Updated application

    Raises:
        HTTPException: If application not found or business unit not found
    """
    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"
    application = (
        db.query(Application)
        .filter(Application.id == application_id, Application.tenant_id == effective_tenant_id)
        .first()
    )

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Verify business unit if it's being changed
    if application_update.business_unit_id and application_update.business_unit_id != application.business_unit_id:
        business_unit = db.query(BusinessUnit).filter(
            BusinessUnit.id == application_update.business_unit_id
        ).first()
        if not business_unit:
            raise HTTPException(status_code=404, detail="Business unit not found")

    # Update fields
    update_data = application_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(application, field, value)

    db.commit()
    db.refresh(application)

    logger.info(
        "application_updated",
        application_id=application.id,
        name=application.name,
        tenant_id=tenant_id,
    )

    return application


@router.delete("/{application_id}", status_code=204)
def delete_application(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> None:
    """Delete an application.

    Args:
        application_id: ID of the application
        db: Database session
        tenant_id: Tenant ID from auth context

    Raises:
        HTTPException: If application not found
    """
    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"
    application = (
        db.query(Application)
        .filter(Application.id == application_id, Application.tenant_id == effective_tenant_id)
        .first()
    )

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(application)
    db.commit()

    logger.info(
        "application_deleted",
        application_id=application_id,
        tenant_id=tenant_id,
    )


@router.post("/import-csv", response_model=ApplicationImportResult)
async def import_applications_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> ApplicationImportResult:
    """Import applications from CSV file.

    Expected CSV format:
    name,business_unit_id,description,criticality,tech_stack,owner

    Args:
        file: CSV file upload
        db: Database session
        tenant_id: Tenant ID from auth context

    Returns:
        Import result with success/failure counts

    Raises:
        HTTPException: If file is not a CSV
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"

    content = await file.read()
    csv_text = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_text))

    total = 0
    success = 0
    failed = 0
    errors = []

    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
        total += 1
        try:
            # Validate required fields
            if not row.get('name') or not row.get('business_unit_id'):
                errors.append(f"Row {row_num}: Missing required fields (name, business_unit_id)")
                failed += 1
                continue

            # Verify business unit exists
            business_unit_id = int(row['business_unit_id'])
            business_unit = db.query(BusinessUnit).filter(
                BusinessUnit.id == business_unit_id
            ).first()
            if not business_unit:
                errors.append(f"Row {row_num}: Business unit {business_unit_id} not found")
                failed += 1
                continue

            # Parse criticality
            criticality_str = row.get('criticality', 'medium').lower()
            try:
                criticality = CriticalityLevel(criticality_str)
            except ValueError:
                criticality = CriticalityLevel.MEDIUM

            # Create application
            application = Application(
                name=row['name'].strip(),
                business_unit_id=business_unit_id,
                description=row.get('description', '').strip() or None,
                criticality=criticality,
                tech_stack=row.get('tech_stack', '').strip() or None,
                owner=row.get('owner', '').strip() or None,
                tenant_id=effective_tenant_id,
            )
            db.add(application)
            success += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            failed += 1
            logger.error("csv_import_row_failed", row_num=row_num, error=str(e))

    # Commit all successful imports
    try:
        db.commit()
        logger.info(
            "applications_imported",
            total=total,
            success=success,
            failed=failed,
            tenant_id=effective_tenant_id,
        )
    except Exception as e:
        db.rollback()
        logger.error("csv_import_commit_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to commit imports: {str(e)}")

    return ApplicationImportResult(
        total=total,
        success=success,
        failed=failed,
        errors=errors[:100],  # Limit to first 100 errors
    )


@router.get("/{application_id}/policies", response_model=list[PolicySchema])
def get_application_policies(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
    source_type: SourceType | None = None,
    risk_level: RiskLevel | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Policy]:
    """Get all policies for a specific application.

    Args:
        application_id: ID of the application
        db: Database session
        tenant_id: Tenant ID from auth context
        source_type: Filter by source type (frontend/backend/database)
        risk_level: Filter by risk level
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of policies belonging to the application

    Raises:
        HTTPException: If application not found
    """
    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"

    # Verify application exists and belongs to tenant
    application = (
        db.query(Application)
        .filter(Application.id == application_id, Application.tenant_id == effective_tenant_id)
        .first()
    )

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Build query for policies
    query = db.query(Policy).filter(Policy.application_id == application_id)

    # Apply filters
    if source_type:
        query = query.filter(Policy.source_type == source_type)

    if risk_level:
        query = query.filter(Policy.risk_level == risk_level)

    policies = query.order_by(Policy.created_at.desc()).offset(skip).limit(limit).all()

    logger.info(
        "application_policies_retrieved",
        application_id=application_id,
        policy_count=len(policies),
        tenant_id=effective_tenant_id,
    )

    return policies


@router.get("/{application_id}/with-policies", response_model=ApplicationWithPolicies)
def get_application_with_policy_stats(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> dict:
    """Get application with policy statistics.

    Args:
        application_id: ID of the application
        db: Database session
        tenant_id: Tenant ID from auth context

    Returns:
        Application with policy counts and statistics

    Raises:
        HTTPException: If application not found
    """
    # Use default tenant if not authenticated
    effective_tenant_id = tenant_id or "default"

    # Get application
    application = (
        db.query(Application)
        .filter(Application.id == application_id, Application.tenant_id == effective_tenant_id)
        .first()
    )

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get policy count
    policy_count = db.query(func.count(Policy.id)).filter(Policy.application_id == application_id).scalar()

    # Get policy count by source type
    source_counts = (
        db.query(Policy.source_type, func.count(Policy.id))
        .filter(Policy.application_id == application_id)
        .group_by(Policy.source_type)
        .all()
    )
    policy_count_by_source = {source.value if source else 'unknown': count for source, count in source_counts}

    # Get policy count by risk level
    risk_counts = (
        db.query(Policy.risk_level, func.count(Policy.id))
        .filter(Policy.application_id == application_id)
        .group_by(Policy.risk_level)
        .all()
    )
    policy_count_by_risk = {risk.value: count for risk, count in risk_counts if risk}

    # Build response
    response = {
        **application.__dict__,
        "policy_count": policy_count or 0,
        "policy_count_by_source": policy_count_by_source,
        "policy_count_by_risk": policy_count_by_risk,
    }

    return response
