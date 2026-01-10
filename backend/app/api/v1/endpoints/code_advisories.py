"""API endpoints for code advisories."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.code_advisory import AdvisoryStatus
from app.schemas.code_advisory import (
    CodeAdvisory,
    CodeAdvisoryUpdate,
    GenerateAdvisoryRequest,
)
from app.services.code_advisory_service import CodeAdvisoryService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/generate/", response_model=CodeAdvisory, status_code=201)
async def generate_advisory(
    request: GenerateAdvisoryRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> CodeAdvisory:
    """Generate code refactoring advisory for a policy.

    This endpoint uses AI to analyze the policy's inline authorization code
    and generate refactored code that calls a PBAC platform instead.
    """
    service = CodeAdvisoryService(db, tenant_id)
    try:
        advisory = await service.generate_advisory(
            policy_id=request.policy_id,
            target_platform=request.target_platform,
        )
        return advisory
    except ValueError as e:
        logger.error("generate_advisory_failed", error=str(e), policy_id=request.policy_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("generate_advisory_error", error=str(e), policy_id=request.policy_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate advisory: {e}") from e


@router.get("/", response_model=list[CodeAdvisory])
def list_advisories(
    policy_id: int | None = None,
    status: AdvisoryStatus | None = None,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> list[CodeAdvisory]:
    """List all code advisories with optional filtering."""
    service = CodeAdvisoryService(db, tenant_id)
    return service.list_advisories(policy_id=policy_id, status=status)


@router.get("/{advisory_id}/", response_model=CodeAdvisory)
def get_advisory(
    advisory_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> CodeAdvisory:
    """Get a specific code advisory."""
    service = CodeAdvisoryService(db, tenant_id)
    advisory = service.get_advisory(advisory_id)
    if not advisory:
        raise HTTPException(status_code=404, detail="Advisory not found")
    return advisory


@router.put("/{advisory_id}/", response_model=CodeAdvisory)
def update_advisory(
    advisory_id: int,
    update: CodeAdvisoryUpdate,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> CodeAdvisory:
    """Update advisory status (reviewed, applied, rejected)."""
    service = CodeAdvisoryService(db, tenant_id)

    if update.status is None:
        raise HTTPException(status_code=400, detail="Status is required")

    advisory = service.update_advisory(advisory_id, update.status)
    if not advisory:
        raise HTTPException(status_code=404, detail="Advisory not found")

    return advisory


@router.delete("/{advisory_id}/", status_code=204)
def delete_advisory(
    advisory_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> None:
    """Delete a code advisory."""
    service = CodeAdvisoryService(db, tenant_id)
    success = service.delete_advisory(advisory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Advisory not found")


@router.post("/{advisory_id}/generate-tests/", response_model=CodeAdvisory)
async def generate_test_cases(
    advisory_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> CodeAdvisory:
    """Generate test cases for a code advisory.

    This endpoint uses AI to generate comprehensive test cases that verify
    the refactored code maintains behavioral equivalence with the original code.
    """
    service = CodeAdvisoryService(db, tenant_id)
    try:
        advisory = await service.generate_test_cases(advisory_id)
        return advisory
    except ValueError as e:
        logger.error("generate_test_cases_failed", error=str(e), advisory_id=advisory_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("generate_test_cases_error", error=str(e), advisory_id=advisory_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate test cases: {e}") from e
