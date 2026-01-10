"""API endpoints for division and business unit listing."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.organization import BusinessUnit, Division
from app.schemas.organization import BusinessUnitResponse, DivisionResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[DivisionResponse])
def list_all_divisions(
    db: Annotated[Session, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 1000,
) -> list[Division]:
    """List all divisions across all organizations.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of all divisions
    """
    divisions = db.query(Division).order_by(Division.name).offset(skip).limit(limit).all()
    return divisions


@router.get("/business-units/", response_model=list[BusinessUnitResponse])
def list_all_business_units(
    db: Annotated[Session, Depends(get_db)],
    division_id: Annotated[int | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 1000,
) -> list[BusinessUnit]:
    """List all business units, optionally filtered by division.

    Args:
        db: Database session
        division_id: Optional division ID to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of business units
    """
    query = db.query(BusinessUnit)

    if division_id is not None:
        query = query.filter(BusinessUnit.division_id == division_id)

    business_units = query.order_by(BusinessUnit.name).offset(skip).limit(limit).all()
    return business_units
