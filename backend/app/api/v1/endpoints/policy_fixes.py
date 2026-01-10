"""API endpoints for policy fixing."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.policy_fix import FixSeverity, FixStatus
from app.schemas.policy_fix import (
    AnalyzePolicyRequest,
    PolicyFixResponse,
    UpdateFixStatusRequest,
)
from app.services.policy_fixing_service import PolicyFixingService

router = APIRouter()


@router.post("/analyze", response_model=PolicyFixResponse | dict)
async def analyze_policy(
    request: AnalyzePolicyRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Analyze a policy for security gaps and generate a fix.

    Returns PolicyFix if gaps found, or {"has_gaps": false} if policy is complete.
    """
    service = PolicyFixingService(db, tenant_id)

    try:
        policy_fix = await service.analyze_policy(request.policy_id)

        if policy_fix is None:
            return {"has_gaps": False, "policy_id": request.policy_id}

        return policy_fix
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=list[PolicyFixResponse])
def list_fixes(
    policy_id: int | None = None,
    status: FixStatus | None = None,
    severity: FixSeverity | None = None,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """List policy fixes with optional filtering."""
    service = PolicyFixingService(db, tenant_id)
    fixes = service.list_fixes(policy_id=policy_id, status=status, severity=severity)
    return fixes


@router.get("/{fix_id}", response_model=PolicyFixResponse)
def get_fix(
    fix_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Get a specific policy fix by ID."""
    service = PolicyFixingService(db, tenant_id)
    policy_fix = service.get_fix(fix_id)

    if not policy_fix:
        raise HTTPException(status_code=404, detail=f"PolicyFix {fix_id} not found")

    return policy_fix


@router.put("/{fix_id}/status", response_model=PolicyFixResponse)
def update_fix_status(
    fix_id: int,
    request: UpdateFixStatusRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Update the status of a policy fix after review."""
    service = PolicyFixingService(db, tenant_id)
    policy_fix = service.update_fix_status(
        fix_id=fix_id,
        status=request.status,
        reviewed_by=request.reviewed_by,
        review_comment=request.review_comment,
    )

    if not policy_fix:
        raise HTTPException(status_code=404, detail=f"PolicyFix {fix_id} not found")

    return policy_fix


@router.post("/{fix_id}/test-cases", response_model=PolicyFixResponse)
async def generate_test_cases(
    fix_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Generate test cases to prove the fix prevents security gaps."""
    service = PolicyFixingService(db, tenant_id)

    try:
        policy_fix = await service.generate_test_cases(fix_id)
        return policy_fix
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{fix_id}")
def delete_fix(
    fix_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Delete a policy fix."""
    service = PolicyFixingService(db, tenant_id)
    success = service.delete_fix(fix_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"PolicyFix {fix_id} not found")

    return {"message": "PolicyFix deleted successfully"}
