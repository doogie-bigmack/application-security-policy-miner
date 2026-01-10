"""Policy API endpoints."""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_email, get_tenant_id
from app.models.policy import Evidence, Policy, SourceType
from app.models.repository import Repository
from app.schemas.policy import Policy as PolicySchema
from app.schemas.policy import PolicyList, PolicyUpdate
from app.services.audit_service import AuditService
from app.services.evidence_validation_service import EvidenceValidationService
from app.services.translation_service import TranslationService

logger = logging.getLogger(__name__)

router = APIRouter()


class SourceFileResponse(BaseModel):
    """Response model for source file content."""

    file_path: str
    content: str
    total_lines: int
    line_start: int
    line_end: int


@router.get("/", response_model=PolicyList)
async def list_policies(
    repository_id: int | None = None,
    source_type: SourceType | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> PolicyList:
    """List all policies with optional filtering.

    Args:
        repository_id: Filter by repository ID
        source_type: Filter by source type (frontend/backend/database/unknown)
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of policies
    """
    query = db.query(Policy)

    if repository_id:
        query = query.filter(Policy.repository_id == repository_id)

    if source_type:
        query = query.filter(Policy.source_type == source_type)

    total = query.count()
    policies = query.offset(skip).limit(limit).all()

    return PolicyList(policies=policies, total=total)


@router.get("/{policy_id}", response_model=PolicySchema)
async def get_policy(policy_id: int, db: Session = Depends(get_db)) -> PolicySchema:
    """Get a single policy by ID.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Policy details
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    return policy


@router.put("/{policy_id}", response_model=PolicySchema)
async def update_policy(
    policy_id: int, policy_update: PolicyUpdate, db: Session = Depends(get_db)
) -> PolicySchema:
    """Update a policy.

    Args:
        policy_id: Policy ID
        policy_update: Updated policy data
        db: Database session

    Returns:
        Updated policy
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Update only provided fields
    update_data = policy_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)

    logger.info(f"Policy {policy_id} updated", extra={"policy_id": policy_id})

    return policy


class ApprovalRequest(BaseModel):
    """Request body for policy approval/rejection."""

    comment: str | None = None


@router.put("/{policy_id}/approve")
async def approve_policy(
    policy_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    user_email: str | None = Depends(get_current_user_email),
    tenant_id: int | None = Depends(get_tenant_id),
) -> dict:
    """Approve a policy.

    Args:
        policy_id: Policy ID
        request: Approval request with optional comment
        db: Database session
        user_email: Authenticated user email
        tenant_id: Authenticated tenant ID

    Returns:
        Success message
    """
    from datetime import UTC, datetime

    from app.models.policy import PolicyStatus

    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.status = PolicyStatus.APPROVED
    policy.approval_comment = request.comment
    policy.reviewed_by = user_email or "anonymous"
    policy.reviewed_at = datetime.now(UTC)
    db.commit()

    # Log approval decision to audit trail
    if tenant_id:
        AuditService.log_policy_approval(
            db=db,
            tenant_id=tenant_id,
            policy_id=policy_id,
            user_email=user_email or "anonymous",
        )

    return {"status": "success", "message": "Policy approved"}


@router.put("/{policy_id}/reject")
async def reject_policy(
    policy_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    user_email: str | None = Depends(get_current_user_email),
    tenant_id: int | None = Depends(get_tenant_id),
) -> dict:
    """Reject a policy.

    Args:
        policy_id: Policy ID
        request: Rejection request with optional comment
        db: Database session
        user_email: Authenticated user email
        tenant_id: Authenticated tenant ID

    Returns:
        Success message
    """
    from datetime import UTC, datetime

    from app.models.policy import PolicyStatus

    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.status = PolicyStatus.REJECTED
    policy.approval_comment = request.comment
    policy.reviewed_by = user_email or "anonymous"
    policy.reviewed_at = datetime.now(UTC)
    db.commit()

    # Log rejection decision to audit trail
    if tenant_id:
        AuditService.log_policy_rejection(
            db=db,
            tenant_id=tenant_id,
            policy_id=policy_id,
            user_email=user_email or "anonymous",
        )

    return {"status": "success", "message": "Policy rejected"}


class BulkApprovalRequest(BaseModel):
    """Request body for bulk policy approval."""

    policy_ids: list[int]
    comment: str | None = None


class BulkApprovalResponse(BaseModel):
    """Response for bulk policy approval."""

    total_requested: int
    approved: int
    failed: int
    failed_policy_ids: list[int]


@router.post("/bulk/approve", response_model=BulkApprovalResponse)
async def bulk_approve_policies(
    request: BulkApprovalRequest,
    db: Session = Depends(get_db),
    user_email: str | None = Depends(get_current_user_email),
    tenant_id: int | None = Depends(get_tenant_id),
) -> BulkApprovalResponse:
    """Approve multiple policies at once.

    Args:
        request: Bulk approval request with policy IDs and optional comment
        db: Database session
        user_email: Authenticated user email
        tenant_id: Authenticated tenant ID

    Returns:
        Summary of bulk approval operation
    """
    from datetime import UTC, datetime

    from app.models.policy import PolicyStatus

    approved = 0
    failed = 0
    failed_policy_ids = []

    for policy_id in request.policy_ids:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()

        if not policy:
            failed += 1
            failed_policy_ids.append(policy_id)
            continue

        policy.status = PolicyStatus.APPROVED
        policy.approval_comment = request.comment
        policy.reviewed_by = user_email or "anonymous"
        policy.reviewed_at = datetime.now(UTC)
        approved += 1

        # Log approval decision to audit trail
        if tenant_id:
            AuditService.log_policy_approval(
                db=db,
                tenant_id=tenant_id,
                policy_id=policy_id,
                user_email=user_email or "anonymous",
            )

    db.commit()

    return BulkApprovalResponse(
        total_requested=len(request.policy_ids),
        approved=approved,
        failed=failed,
        failed_policy_ids=failed_policy_ids,
    )


@router.get("/{policy_id}/history")
async def get_policy_history(policy_id: int, db: Session = Depends(get_db)) -> dict:
    """Get change history for a policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        List of policy changes
    """
    from app.models.policy_change import PolicyChange

    # Check if policy exists
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Get all changes for this policy
    changes = (
        db.query(PolicyChange)
        .filter(PolicyChange.policy_id == policy_id)
        .order_by(PolicyChange.detected_at.desc())
        .all()
    )

    return {
        "policy_id": policy_id,
        "changes": [
            {
                "id": change.id,
                "change_type": change.change_type,
                "before": {
                    "subject": change.before_subject,
                    "resource": change.before_resource,
                    "action": change.before_action,
                    "conditions": change.before_conditions,
                },
                "after": {
                    "subject": change.after_subject,
                    "resource": change.after_resource,
                    "action": change.after_action,
                    "conditions": change.after_conditions,
                },
                "description": change.description,
                "diff_summary": change.diff_summary,
                "detected_at": change.detected_at.isoformat() if change.detected_at else None,
            }
            for change in changes
        ],
        "total": len(changes),
    }


@router.delete("/{policy_id}")
async def delete_policy(policy_id: int, db: Session = Depends(get_db)) -> dict:
    """Delete a policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Success message
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    db.delete(policy)
    db.commit()

    return {"status": "success", "message": "Policy deleted"}


@router.get("/evidence/{evidence_id}/source", response_model=SourceFileResponse)
async def get_source_file(evidence_id: int, db: Session = Depends(get_db)) -> SourceFileResponse:
    """Get source file content for an evidence item.

    Args:
        evidence_id: Evidence ID
        db: Database session

    Returns:
        Source file content with metadata
    """
    # Get evidence
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Get associated policy and repository
    policy = db.query(Policy).filter(Policy.id == evidence.policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    repository = db.query(Repository).filter(Repository.id == policy.repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Build path to cloned repository
    repo_path = Path("/tmp/policy_miner_repos") / str(repository.id)
    file_path = repo_path / evidence.file_path

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Source file not found. Repository may need to be rescanned.",
        )

    # Read file content
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read source file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read source file: {str(e)}")

    # Count total lines
    total_lines = len(content.split("\n"))

    return SourceFileResponse(
        file_path=evidence.file_path,
        content=content,
        total_lines=total_lines,
        line_start=evidence.line_start,
        line_end=evidence.line_end,
    )


class PolicyExportResponse(BaseModel):
    """Response model for policy export."""

    format: str
    policy: str


@router.get("/{policy_id}/export/rego", response_model=PolicyExportResponse)
async def export_policy_rego(policy_id: int, db: Session = Depends(get_db)) -> PolicyExportResponse:
    """Export a policy as OPA Rego format.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Exported policy in Rego format
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        translation_service = TranslationService()
        rego_policy = await translation_service.translate_to_rego(policy)

        logger.info(f"Policy {policy_id} exported to Rego", extra={"policy_id": policy_id})

        return PolicyExportResponse(format="rego", policy=rego_policy)

    except Exception as e:
        logger.error(f"Failed to export policy to Rego: {e}", extra={"policy_id": policy_id})
        raise HTTPException(status_code=500, detail=f"Failed to export policy to Rego: {str(e)}")


@router.get("/{policy_id}/export/cedar", response_model=PolicyExportResponse)
async def export_policy_cedar(policy_id: int, db: Session = Depends(get_db)) -> PolicyExportResponse:
    """Export a policy as AWS Cedar format.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Exported policy in Cedar format
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        translation_service = TranslationService()
        cedar_policy = await translation_service.translate_to_cedar(policy)

        logger.info(f"Policy {policy_id} exported to Cedar", extra={"policy_id": policy_id})

        return PolicyExportResponse(format="cedar", policy=cedar_policy)

    except Exception as e:
        logger.error(f"Failed to export policy to Cedar: {e}", extra={"policy_id": policy_id})
        raise HTTPException(status_code=500, detail=f"Failed to export policy to Cedar: {str(e)}")


@router.get("/{policy_id}/export/json", response_model=PolicyExportResponse)
async def export_policy_json(policy_id: int, db: Session = Depends(get_db)) -> PolicyExportResponse:
    """Export a policy as JSON format.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Exported policy in JSON format
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        translation_service = TranslationService()
        json_policy = await translation_service.translate_to_json(policy)

        logger.info(f"Policy {policy_id} exported to JSON", extra={"policy_id": policy_id})

        return PolicyExportResponse(format="json", policy=json_policy)

    except Exception as e:
        logger.error(f"Failed to export policy to JSON: {e}", extra={"policy_id": policy_id})
        raise HTTPException(status_code=500, detail=f"Failed to export policy to JSON: {str(e)}")


@router.post("/evidence/{evidence_id}/validate")
async def validate_evidence(evidence_id: int, db: Session = Depends(get_db)) -> dict:
    """Validate a single evidence item against its source file.

    Args:
        evidence_id: Evidence ID
        db: Database session

    Returns:
        Validation result
    """
    # Get evidence and associated repository
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    policy = db.query(Policy).filter(Policy.id == evidence.policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    repository = db.query(Repository).filter(Repository.id == policy.repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get repository path
    repo_path = Path("/tmp/policy_miner_repos") / str(repository.id)

    # Validate evidence
    validation_service = EvidenceValidationService(db)
    result = validation_service.validate_evidence(evidence_id, str(repo_path))

    logger.info(f"Evidence {evidence_id} validation result: {result.get('status')}")

    return result


@router.post("/{policy_id}/validate-evidence")
async def validate_policy_evidence(policy_id: int, db: Session = Depends(get_db)) -> dict:
    """Validate all evidence items for a policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Validation summary
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    repository = db.query(Repository).filter(Repository.id == policy.repository_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get repository path
    repo_path = Path("/tmp/policy_miner_repos") / str(repository.id)

    # Validate all evidence for this policy
    validation_service = EvidenceValidationService(db)
    result = validation_service.validate_policy_evidence(policy_id, str(repo_path))

    logger.info(
        f"Policy {policy_id} evidence validation complete: {result.get('valid')}/{result.get('total')} valid"
    )

    return result
