"""API endpoints for OPA verification (lasagna architecture)."""
import logging
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.services.opa_verification_service import OPAVerificationService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class CreateBaselineRequest(BaseModel):
    """Request to create OPA verification baseline."""

    application_id: str = Field(..., description="Application ID")
    policy_id: str = Field(..., description="Policy ID being centralized")
    inline_checks_count: int = Field(..., ge=0, description="Number of inline authorization checks detected")


class MarkRefactoringAppliedRequest(BaseModel):
    """Request to mark refactoring as applied."""

    code_advisory_id: str | None = Field(None, description="Code advisory ID that was applied")


class VerifyOPAIntegrationRequest(BaseModel):
    """Request to verify OPA integration."""

    opa_endpoint_url: str = Field(..., description="OPA endpoint URL to test")
    timeout_seconds: int = Field(5, ge=1, le=30, description="Timeout for connection test")


class UpdateOPACallsDetectedRequest(BaseModel):
    """Request to update OPA call detection results."""

    calls_detected: bool = Field(..., description="Whether OPA calls were detected at runtime")
    inline_checks_remaining: int = Field(..., ge=0, description="Number of inline checks still present")


class UpdateDecisionEnforcementRequest(BaseModel):
    """Request to update decision enforcement verification."""

    decision_enforced: bool = Field(..., description="Whether OPA decisions are being enforced")
    verification_notes: str | None = Field(None, description="Human-readable verification notes")


class MeasureLatencyRequest(BaseModel):
    """Request to record latency comparison."""

    inline_latency_ms: float = Field(..., ge=0, description="Average latency of inline checks (ms)")
    opa_latency_ms: float = Field(..., ge=0, description="Average latency of OPA calls (ms)")


class OPAVerificationResponse(BaseModel):
    """OPA verification response model."""

    id: str
    tenant_id: str
    application_id: str
    policy_id: str
    baseline_inline_checks: int | None
    baseline_scan_date: str | None
    code_advisory_id: str | None
    refactoring_applied: bool
    refactoring_applied_at: str | None
    verification_status: str
    verification_date: str | None
    opa_calls_detected: bool
    inline_checks_remaining: int | None
    spaghetti_reduction_percentage: float | None
    opa_endpoint_url: str | None
    opa_connection_verified: bool
    opa_decision_enforced: bool
    inline_latency_ms: float | None
    opa_latency_ms: float | None
    latency_overhead_ms: float | None
    latency_overhead_percentage: float | None
    verification_notes: str | None
    created_at: str
    updated_at: str
    is_fully_migrated: bool
    migration_completeness: float

    class Config:
        """Pydantic config."""

        from_attributes = True


class OPAVerificationStatistics(BaseModel):
    """OPA verification statistics."""

    total_verifications: int
    fully_migrated: int
    in_progress: int
    pending: int
    average_spaghetti_reduction_percentage: float
    average_latency_overhead_ms: float


@router.post("/baseline/", response_model=OPAVerificationResponse, status_code=201)
async def create_verification_baseline(
    request: CreateBaselineRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> OPAVerificationResponse:
    """
    Create a baseline measurement before migration.

    This captures the current state of inline authorization checks
    before migrating to centralized PBAC (OPA).
    """
    logger.info(
        "Creating OPA verification baseline",
        extra={
            "tenant_id": tenant_id,
            "application_id": request.application_id,
            "inline_checks": request.inline_checks_count,
        },
    )

    service = OPAVerificationService(db)
    verification = await service.create_baseline(
        tenant_id=tenant_id,
        application_id=request.application_id,
        policy_id=request.policy_id,
        inline_checks_count=request.inline_checks_count,
    )

    return OPAVerificationResponse.model_validate(verification)


@router.put("/{verification_id}/refactoring-applied/", response_model=OPAVerificationResponse)
async def mark_refactoring_applied(
    verification_id: str,
    request: MarkRefactoringAppliedRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> OPAVerificationResponse:
    """
    Mark that refactoring has been applied to the application.

    This indicates that the code has been modified to replace inline
    authorization checks with calls to centralized PBAC (OPA).
    """
    service = OPAVerificationService(db)

    # Verify tenant ownership
    verification = await service.get_verification(verification_id, tenant_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    verification = await service.mark_refactoring_applied(
        verification_id=verification_id,
        code_advisory_id=request.code_advisory_id,
    )

    return OPAVerificationResponse.model_validate(verification)


@router.post("/{verification_id}/verify-integration/")
async def verify_opa_integration(
    verification_id: str,
    request: VerifyOPAIntegrationRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """
    Verify that the application can successfully connect to OPA.

    Tests connectivity to the OPA endpoint and measures latency.
    """
    service = OPAVerificationService(db)

    # Verify tenant ownership
    verification = await service.get_verification(verification_id, tenant_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    result = await service.verify_opa_integration(
        verification_id=verification_id,
        opa_endpoint_url=request.opa_endpoint_url,
        timeout_seconds=request.timeout_seconds,
    )

    return result


@router.put("/{verification_id}/opa-calls-detected/", response_model=OPAVerificationResponse)
async def update_opa_calls_detected(
    verification_id: str,
    request: UpdateOPACallsDetectedRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> OPAVerificationResponse:
    """
    Update verification with runtime detection results.

    Records whether OPA calls were detected at runtime and how many
    inline checks remain after migration.
    """
    service = OPAVerificationService(db)

    # Verify tenant ownership
    verification = await service.get_verification(verification_id, tenant_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    verification = await service.verify_opa_calls_detected(
        verification_id=verification_id,
        calls_detected=request.calls_detected,
        inline_checks_remaining=request.inline_checks_remaining,
    )

    return OPAVerificationResponse.model_validate(verification)


@router.put("/{verification_id}/decision-enforcement/", response_model=OPAVerificationResponse)
async def update_decision_enforcement(
    verification_id: str,
    request: UpdateDecisionEnforcementRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> OPAVerificationResponse:
    """
    Verify that the application enforces OPA decisions.

    This confirms that the application respects authorization decisions
    returned by OPA and doesn't bypass them.
    """
    service = OPAVerificationService(db)

    # Verify tenant ownership
    verification = await service.get_verification(verification_id, tenant_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    verification = await service.verify_decision_enforcement(
        verification_id=verification_id,
        decision_enforced=request.decision_enforced,
        verification_notes=request.verification_notes,
    )

    return OPAVerificationResponse.model_validate(verification)


@router.put("/{verification_id}/latency/", response_model=OPAVerificationResponse)
async def measure_latency_comparison(
    verification_id: str,
    request: MeasureLatencyRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> OPAVerificationResponse:
    """
    Record latency comparison between inline and centralized authorization.

    Measures the performance impact of migrating from inline checks to
    centralized PBAC (OPA).
    """
    service = OPAVerificationService(db)

    # Verify tenant ownership
    verification = await service.get_verification(verification_id, tenant_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    verification = await service.measure_latency_comparison(
        verification_id=verification_id,
        inline_latency_ms=request.inline_latency_ms,
        opa_latency_ms=request.opa_latency_ms,
    )

    return OPAVerificationResponse.model_validate(verification)


@router.get("/{verification_id}/", response_model=OPAVerificationResponse)
async def get_verification(
    verification_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> OPAVerificationResponse:
    """Get a specific OPA verification record."""
    service = OPAVerificationService(db)
    verification = await service.get_verification(verification_id, tenant_id)

    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    return OPAVerificationResponse.model_validate(verification)


@router.get("/", response_model=list[OPAVerificationResponse])
async def list_verifications(
    application_id: str | None = Query(None, description="Filter by application ID"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> list[OPAVerificationResponse]:
    """
    List OPA verification records with optional filtering.

    Supports filtering by application and verification status.
    """
    service = OPAVerificationService(db)
    verifications = await service.list_verifications(
        tenant_id=tenant_id,
        application_id=application_id,
        status=status,
        limit=limit,
    )

    return [OPAVerificationResponse.model_validate(v) for v in verifications]


@router.get("/statistics/", response_model=OPAVerificationStatistics)
async def get_verification_statistics(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> OPAVerificationStatistics:
    """
    Get aggregate statistics for tenant's OPA verifications.

    Returns metrics like total verifications, fully migrated count,
    average spaghetti reduction, and average latency overhead.
    """
    service = OPAVerificationService(db)
    stats = await service.get_verification_statistics(tenant_id=tenant_id)

    return OPAVerificationStatistics(**stats)


@router.get("/export/report/")
async def export_migration_report(
    application_id: str | None = Query(None, description="Filter by application ID"),
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> StreamingResponse:
    """
    Export spaghetti-to-lasagna migration report as CSV.

    Generates a comprehensive report showing migration progress,
    spaghetti reduction metrics, and performance impact for all verifications.
    """
    logger.info(
        "Exporting migration report",
        extra={
            "tenant_id": tenant_id,
            "application_id": application_id,
            "status": status,
        },
    )

    service = OPAVerificationService(db)
    verifications = await service.list_verifications(
        tenant_id=tenant_id,
        application_id=application_id,
        status=status,
        limit=10000,  # Large limit for export
    )

    # Generate CSV report
    output = StringIO()

    # CSV header
    headers = [
        "Verification ID",
        "Application ID",
        "Policy ID",
        "Status",
        "Baseline Inline Checks",
        "Inline Checks Remaining",
        "Spaghetti Reduction %",
        "Refactoring Applied",
        "OPA Calls Detected",
        "OPA Connection Verified",
        "OPA Decision Enforced",
        "Migration Complete",
        "Migration Completeness %",
        "Inline Latency (ms)",
        "OPA Latency (ms)",
        "Latency Overhead (ms)",
        "Latency Overhead %",
        "OPA Endpoint",
        "Baseline Scan Date",
        "Refactoring Applied Date",
        "Verification Date",
        "Created At",
        "Notes",
    ]
    output.write(",".join(headers) + "\n")

    # CSV rows
    for v in verifications:
        row = [
            v.id,
            str(v.application_id),
            str(v.policy_id),
            v.verification_status,
            str(v.baseline_inline_checks or ""),
            str(v.inline_checks_remaining or ""),
            f"{v.spaghetti_reduction_percentage:.2f}" if v.spaghetti_reduction_percentage is not None else "",
            "Yes" if v.refactoring_applied else "No",
            "Yes" if v.opa_calls_detected else "No",
            "Yes" if v.opa_connection_verified else "No",
            "Yes" if v.opa_decision_enforced else "No",
            "Yes" if v.is_fully_migrated else "No",
            f"{v.migration_completeness:.2f}",
            f"{v.inline_latency_ms:.2f}" if v.inline_latency_ms is not None else "",
            f"{v.opa_latency_ms:.2f}" if v.opa_latency_ms is not None else "",
            f"{v.latency_overhead_ms:.2f}" if v.latency_overhead_ms is not None else "",
            f"{v.latency_overhead_percentage:.2f}" if v.latency_overhead_percentage is not None else "",
            v.opa_endpoint_url or "",
            v.baseline_scan_date.isoformat() if v.baseline_scan_date else "",
            v.refactoring_applied_at.isoformat() if v.refactoring_applied_at else "",
            v.verification_date.isoformat() if v.verification_date else "",
            v.created_at.isoformat() if v.created_at else "",
            (v.verification_notes or "").replace(",", ";").replace("\n", " "),  # Escape commas and newlines
        ]
        output.write(",".join(row) + "\n")

    # Reset buffer position
    output.seek(0)

    logger.info(
        f"Generated migration report with {len(verifications)} verifications",
        extra={"tenant_id": tenant_id},
    )

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=spaghetti-to-lasagna-migration-report-{tenant_id}.csv"
        },
    )
