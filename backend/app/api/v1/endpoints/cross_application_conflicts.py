"""Cross-application conflict detection API endpoints."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.application import Application
from app.models.conflict import ConflictStatus, PolicyConflict
from app.models.policy import Policy
from app.services.cross_application_conflict_detection import (
    CrossApplicationConflictDetectionService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class DetectCrossAppConflictsRequest(BaseModel):
    """Request model for detecting cross-application conflicts."""

    application_ids: list[int] | None = None  # Optional: specific applications to compare


class CrossAppConflictResponse(BaseModel):
    """Response model for cross-application conflict."""

    id: int
    policy_a_id: int
    policy_b_id: int
    application_a_id: int
    application_a_name: str
    application_b_id: int
    application_b_name: str
    conflict_type: str
    description: str
    severity: str
    ai_recommendation: str | None
    status: str
    resolution_strategy: str | None
    resolution_notes: str | None

    class Config:
        from_attributes = True


class DetectCrossAppConflictsResponse(BaseModel):
    """Response model for detect cross-application conflicts endpoint."""

    conflicts_detected: int
    conflicts: list[CrossAppConflictResponse]


@router.post("/detect", response_model=DetectCrossAppConflictsResponse)
def detect_cross_application_conflicts(
    request: DetectCrossAppConflictsRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> Any:
    """
    Detect contradictory policies across multiple applications.

    This endpoint analyzes policies from different applications and identifies
    conflicts where the same resource has contradictory authorization rules.
    """
    logger.info(f"Detecting cross-application conflicts for tenant {tenant_id}")

    service = CrossApplicationConflictDetectionService(db)

    try:
        conflicts = service.detect_cross_application_conflicts(
            tenant_id=tenant_id,
            application_ids=request.application_ids,
        )

        # Enrich conflicts with application information
        enriched_conflicts = []
        for conflict in conflicts:
            policy_a = db.query(Policy).filter(Policy.id == conflict.policy_a_id).first()
            policy_b = db.query(Policy).filter(Policy.id == conflict.policy_b_id).first()

            if not policy_a or not policy_b:
                continue

            app_a = db.query(Application).filter(Application.id == policy_a.application_id).first()
            app_b = db.query(Application).filter(Application.id == policy_b.application_id).first()

            if not app_a or not app_b:
                continue

            enriched_conflicts.append(
                CrossAppConflictResponse(
                    id=conflict.id,
                    policy_a_id=conflict.policy_a_id,
                    policy_b_id=conflict.policy_b_id,
                    application_a_id=app_a.id,
                    application_a_name=app_a.name,
                    application_b_id=app_b.id,
                    application_b_name=app_b.name,
                    conflict_type=conflict.conflict_type.value,
                    description=conflict.description,
                    severity=conflict.severity,
                    ai_recommendation=conflict.ai_recommendation,
                    status=conflict.status.value,
                    resolution_strategy=conflict.resolution_strategy,
                    resolution_notes=conflict.resolution_notes,
                )
            )

        return DetectCrossAppConflictsResponse(
            conflicts_detected=len(enriched_conflicts),
            conflicts=enriched_conflicts,
        )

    except Exception as e:
        logger.error(f"Error detecting cross-application conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[CrossAppConflictResponse])
def list_cross_application_conflicts(
    status: str | None = Query(None, description="Filter by status (pending, resolved)"),
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> Any:
    """
    List all cross-application conflicts.

    Returns conflicts where policies from different applications have contradictory rules.
    """
    logger.info(f"Listing cross-application conflicts for tenant {tenant_id}")

    service = CrossApplicationConflictDetectionService(db)

    try:
        conflicts = service.get_cross_application_conflicts(
            tenant_id=tenant_id,
            status=status,
        )

        # Enrich conflicts with application information
        enriched_conflicts = []
        for conflict in conflicts:
            policy_a = db.query(Policy).filter(Policy.id == conflict.policy_a_id).first()
            policy_b = db.query(Policy).filter(Policy.id == conflict.policy_b_id).first()

            if not policy_a or not policy_b:
                continue

            app_a = db.query(Application).filter(Application.id == policy_a.application_id).first()
            app_b = db.query(Application).filter(Application.id == policy_b.application_id).first()

            if not app_a or not app_b:
                continue

            enriched_conflicts.append(
                CrossAppConflictResponse(
                    id=conflict.id,
                    policy_a_id=conflict.policy_a_id,
                    policy_b_id=conflict.policy_b_id,
                    application_a_id=app_a.id,
                    application_a_name=app_a.name,
                    application_b_id=app_b.id,
                    application_b_name=app_b.name,
                    conflict_type=conflict.conflict_type.value,
                    description=conflict.description,
                    severity=conflict.severity,
                    ai_recommendation=conflict.ai_recommendation,
                    status=conflict.status.value,
                    resolution_strategy=conflict.resolution_strategy,
                    resolution_notes=conflict.resolution_notes,
                )
            )

        return enriched_conflicts

    except Exception as e:
        logger.error(f"Error listing cross-application conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conflict_id}", response_model=CrossAppConflictResponse)
def get_cross_application_conflict(
    conflict_id: int,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> Any:
    """
    Get a specific cross-application conflict by ID.
    """
    conflict = db.query(PolicyConflict).filter(PolicyConflict.id == conflict_id).first()

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    if tenant_id and conflict.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Conflict not found")

    # Verify this is a cross-application conflict
    policy_a = db.query(Policy).filter(Policy.id == conflict.policy_a_id).first()
    policy_b = db.query(Policy).filter(Policy.id == conflict.policy_b_id).first()

    if not policy_a or not policy_b:
        raise HTTPException(status_code=404, detail="Associated policies not found")

    if policy_a.application_id == policy_b.application_id:
        raise HTTPException(status_code=400, detail="This is not a cross-application conflict")

    app_a = db.query(Application).filter(Application.id == policy_a.application_id).first()
    app_b = db.query(Application).filter(Application.id == policy_b.application_id).first()

    if not app_a or not app_b:
        raise HTTPException(status_code=404, detail="Associated applications not found")

    return CrossAppConflictResponse(
        id=conflict.id,
        policy_a_id=conflict.policy_a_id,
        policy_b_id=conflict.policy_b_id,
        application_a_id=app_a.id,
        application_a_name=app_a.name,
        application_b_id=app_b.id,
        application_b_name=app_b.name,
        conflict_type=conflict.conflict_type.value,
        description=conflict.description,
        severity=conflict.severity,
        ai_recommendation=conflict.ai_recommendation,
        status=conflict.status.value,
        resolution_strategy=conflict.resolution_strategy,
        resolution_notes=conflict.resolution_notes,
    )


class ApplyUnifiedPolicyRequest(BaseModel):
    """Request model for applying a unified policy."""

    unified_policy: dict  # The unified policy to apply
    target_application_ids: list[int]  # Applications to apply the policy to


@router.post("/{conflict_id}/apply-unified-policy")
def apply_unified_policy(
    conflict_id: int,
    request: ApplyUnifiedPolicyRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
) -> Any:
    """
    Apply a unified policy to resolve a cross-application conflict.

    This endpoint creates a new policy based on the unified policy definition
    and applies it to the specified applications.
    """
    conflict = db.query(PolicyConflict).filter(PolicyConflict.id == conflict_id).first()

    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    if tenant_id and conflict.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Conflict not found")

    try:
        # Create the unified policy for each target application
        created_policies = []

        for app_id in request.target_application_ids:
            # Verify application exists and belongs to tenant
            app = db.query(Application).filter(Application.id == app_id).first()
            if not app:
                raise HTTPException(status_code=404, detail=f"Application {app_id} not found")

            if tenant_id and app.tenant_id != tenant_id:
                raise HTTPException(status_code=403, detail=f"Application {app_id} not accessible")

            # Create new policy
            new_policy = Policy(
                subject=request.unified_policy.get("subject", ""),
                resource=request.unified_policy.get("resource", ""),
                action=request.unified_policy.get("action", ""),
                conditions=request.unified_policy.get("conditions"),
                description=request.unified_policy.get("description", "Unified policy"),
                application_id=app_id,
                tenant_id=tenant_id,
                status="approved",  # Auto-approve unified policies
            )

            db.add(new_policy)
            created_policies.append(new_policy)

        # Mark conflict as resolved
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolution_strategy = "unified_policy"
        conflict.resolution_notes = f"Applied unified policy to {len(request.target_application_ids)} application(s)"

        db.commit()

        return {
            "success": True,
            "message": f"Unified policy applied to {len(created_policies)} application(s)",
            "conflict_id": conflict_id,
            "created_policy_ids": [p.id for p in created_policies],
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error applying unified policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
