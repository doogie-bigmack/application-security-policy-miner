"""API endpoints for organization management."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.organization import BusinessUnit, Division, Organization
from app.schemas.organization import (
    BusinessUnitCreate,
    BusinessUnitResponse,
    DivisionCreate,
    DivisionResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationWithHierarchy,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# Organization endpoints
@router.post("/", response_model=OrganizationResponse, status_code=201)
def create_organization(
    organization: OrganizationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    """Create a new organization.

    Args:
        organization: Organization data
        db: Database session

    Returns:
        Created organization

    Raises:
        HTTPException: If organization name already exists
    """
    # Check if organization name already exists
    existing = db.query(Organization).filter(Organization.name == organization.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization name already exists")

    db_organization = Organization(**organization.model_dump())
    db.add(db_organization)
    db.commit()
    db.refresh(db_organization)

    logger.info("organization_created", organization_id=db_organization.id, name=db_organization.name)

    return db_organization


@router.get("/", response_model=list[OrganizationResponse])
def list_organizations(
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Organization]:
    """List all organizations.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of organizations
    """
    organizations = db.query(Organization).order_by(Organization.name).offset(skip).limit(limit).all()
    return organizations


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    """Get a specific organization.

    Args:
        organization_id: ID of the organization
        db: Database session

    Returns:
        Organization

    Raises:
        HTTPException: If organization not found
    """
    organization = db.query(Organization).filter(Organization.id == organization_id).first()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    return organization


@router.get("/{organization_id}/hierarchy", response_model=OrganizationWithHierarchy)
def get_organization_hierarchy(
    organization_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    """Get organization with full hierarchy (divisions and business units).

    Args:
        organization_id: ID of the organization
        db: Database session

    Returns:
        Organization with divisions and business units

    Raises:
        HTTPException: If organization not found
    """
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .options(joinedload(Organization.divisions).joinedload(Division.business_units))
        .first()
    )

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    return organization


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: int,
    organization: OrganizationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    """Update an organization.

    Args:
        organization_id: ID of the organization
        organization: Updated organization data
        db: Database session

    Returns:
        Updated organization

    Raises:
        HTTPException: If organization not found or name already exists
    """
    db_organization = db.query(Organization).filter(Organization.id == organization_id).first()

    if not db_organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check if new name conflicts with another organization
    if organization.name != db_organization.name:
        existing = db.query(Organization).filter(Organization.name == organization.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Organization name already exists")

    for key, value in organization.model_dump().items():
        setattr(db_organization, key, value)

    db.commit()
    db.refresh(db_organization)

    logger.info("organization_updated", organization_id=db_organization.id)

    return db_organization


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Delete an organization (cascade deletes divisions and business units).

    Args:
        organization_id: ID of the organization
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If organization not found
    """
    organization = db.query(Organization).filter(Organization.id == organization_id).first()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    db.delete(organization)
    db.commit()

    logger.info("organization_deleted", organization_id=organization_id)

    return {"message": "Organization deleted successfully"}


# Division endpoints
@router.post("/{organization_id}/divisions", response_model=DivisionResponse, status_code=201)
def create_division(
    organization_id: int,
    division: DivisionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Division:
    """Create a new division within an organization.

    Args:
        organization_id: ID of the parent organization
        division: Division data
        db: Database session

    Returns:
        Created division

    Raises:
        HTTPException: If organization not found
    """
    # Verify organization exists
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    db_division = Division(organization_id=organization_id, **division.model_dump())
    db.add(db_division)
    db.commit()
    db.refresh(db_division)

    logger.info("division_created", division_id=db_division.id, organization_id=organization_id)

    return db_division


@router.get("/{organization_id}/divisions", response_model=list[DivisionResponse])
def list_divisions(
    organization_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[Division]:
    """List all divisions in an organization.

    Args:
        organization_id: ID of the organization
        db: Database session

    Returns:
        List of divisions
    """
    divisions = (
        db.query(Division)
        .filter(Division.organization_id == organization_id)
        .order_by(Division.name)
        .all()
    )
    return divisions


@router.put("/divisions/{division_id}", response_model=DivisionResponse)
def update_division(
    division_id: int,
    division: DivisionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Division:
    """Update a division.

    Args:
        division_id: ID of the division
        division: Updated division data
        db: Database session

    Returns:
        Updated division

    Raises:
        HTTPException: If division not found
    """
    db_division = db.query(Division).filter(Division.id == division_id).first()

    if not db_division:
        raise HTTPException(status_code=404, detail="Division not found")

    for key, value in division.model_dump().items():
        setattr(db_division, key, value)

    db.commit()
    db.refresh(db_division)

    logger.info("division_updated", division_id=division_id)

    return db_division


@router.delete("/divisions/{division_id}")
def delete_division(
    division_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Delete a division (cascade deletes business units).

    Args:
        division_id: ID of the division
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If division not found
    """
    division = db.query(Division).filter(Division.id == division_id).first()

    if not division:
        raise HTTPException(status_code=404, detail="Division not found")

    db.delete(division)
    db.commit()

    logger.info("division_deleted", division_id=division_id)

    return {"message": "Division deleted successfully"}


# Business Unit endpoints
@router.post("/divisions/{division_id}/business-units", response_model=BusinessUnitResponse, status_code=201)
def create_business_unit(
    division_id: int,
    business_unit: BusinessUnitCreate,
    db: Annotated[Session, Depends(get_db)],
) -> BusinessUnit:
    """Create a new business unit within a division.

    Args:
        division_id: ID of the parent division
        business_unit: Business unit data
        db: Database session

    Returns:
        Created business unit

    Raises:
        HTTPException: If division not found
    """
    # Verify division exists
    division = db.query(Division).filter(Division.id == division_id).first()
    if not division:
        raise HTTPException(status_code=404, detail="Division not found")

    db_business_unit = BusinessUnit(division_id=division_id, **business_unit.model_dump())
    db.add(db_business_unit)
    db.commit()
    db.refresh(db_business_unit)

    logger.info("business_unit_created", business_unit_id=db_business_unit.id, division_id=division_id)

    return db_business_unit


@router.get("/divisions/{division_id}/business-units", response_model=list[BusinessUnitResponse])
def list_business_units(
    division_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[BusinessUnit]:
    """List all business units in a division.

    Args:
        division_id: ID of the division
        db: Database session

    Returns:
        List of business units
    """
    business_units = (
        db.query(BusinessUnit)
        .filter(BusinessUnit.division_id == division_id)
        .order_by(BusinessUnit.name)
        .all()
    )
    return business_units


@router.put("/business-units/{business_unit_id}", response_model=BusinessUnitResponse)
def update_business_unit(
    business_unit_id: int,
    business_unit: BusinessUnitCreate,
    db: Annotated[Session, Depends(get_db)],
) -> BusinessUnit:
    """Update a business unit.

    Args:
        business_unit_id: ID of the business unit
        business_unit: Updated business unit data
        db: Database session

    Returns:
        Updated business unit

    Raises:
        HTTPException: If business unit not found
    """
    db_business_unit = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit_id).first()

    if not db_business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")

    for key, value in business_unit.model_dump().items():
        setattr(db_business_unit, key, value)

    db.commit()
    db.refresh(db_business_unit)

    logger.info("business_unit_updated", business_unit_id=business_unit_id)

    return db_business_unit


@router.delete("/business-units/{business_unit_id}")
def delete_business_unit(
    business_unit_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Delete a business unit.

    Args:
        business_unit_id: ID of the business unit
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If business unit not found
    """
    business_unit = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit_id).first()

    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")

    db.delete(business_unit)
    db.commit()

    logger.info("business_unit_deleted", business_unit_id=business_unit_id)

    return {"message": "Business unit deleted successfully"}
