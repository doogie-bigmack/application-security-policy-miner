"""Translation verification API endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.models.policy import Policy
from app.services.translation_service import TranslationService
from app.services.translation_verification_service import TranslationVerificationService

router = APIRouter()
logger = structlog.get_logger(__name__)


class VerifyTranslationRequest(BaseModel):
    """Request to verify a policy translation."""

    original_code: str = Field(..., description="Original authorization code")
    format: str = Field(..., description="Target format (rego, cedar, json)")


class VerifyTranslationResponse(BaseModel):
    """Response from translation verification."""

    status: str = Field(..., description="Verification status")
    message: str = Field(..., description="Human-readable status message")
    equivalence_percentage: float = Field(..., description="Percentage of matching test results")
    total_tests: int = Field(..., description="Total number of test cases")
    passed: int = Field(..., description="Number of passed tests")
    failed: int = Field(..., description="Number of failed tests")
    test_results: list = Field(..., description="Detailed test results")
    differences: list = Field(..., description="List of differences found")


@router.post("/policies/{policy_id}/verify-translation", response_model=VerifyTranslationResponse)
async def verify_policy_translation(
    policy_id: int,
    request: VerifyTranslationRequest,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """
    Verify semantic equivalence between original code and translated policy.

    Generates comprehensive test cases and executes them against both
    original authorization code and translated policy to verify they
    produce identical authorization decisions.

    Args:
        policy_id: ID of the policy to verify
        request: Verification request with original code and format
        db: Database session
        tenant_id: Optional tenant ID for multi-tenancy

    Returns:
        Verification results with test cases and equivalence analysis
    """
    logger.info(
        "Verifying policy translation",
        policy_id=policy_id,
        format=request.format,
        tenant_id=tenant_id,
    )

    # Fetch policy
    query = db.query(Policy).filter(Policy.id == policy_id)
    if tenant_id:
        query = query.filter(Policy.tenant_id == tenant_id)
    policy = query.first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Translate the policy first
    translation_service = TranslationService()
    try:
        if request.format == "rego":
            translated_policy = await translation_service.translate_to_rego(policy)
        elif request.format == "cedar":
            translated_policy = await translation_service.translate_to_cedar(policy)
        elif request.format == "json":
            translated_policy = translation_service.translate_to_json(policy)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {request.format}. Must be rego, cedar, or json",
            )
    except Exception as e:
        logger.error("Translation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

    # Verify the translation
    verification_service = TranslationVerificationService()
    try:
        verification_result = await verification_service.verify_translation(
            policy=policy,
            original_code=request.original_code,
            translated_policy=translated_policy,
            format=request.format,
        )
    except Exception as e:
        logger.error("Verification failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

    if verification_result["status"] == "error":
        raise HTTPException(status_code=500, detail=verification_result["message"])

    # Return formatted response
    return VerifyTranslationResponse(
        status=verification_result["status"],
        message=verification_result["message"],
        equivalence_percentage=verification_result["results"]["equivalence_percentage"],
        total_tests=verification_result["results"]["total_tests"],
        passed=verification_result["results"]["passed"],
        failed=verification_result["results"]["failed"],
        test_results=verification_result["results"]["test_results"],
        differences=verification_result["results"]["differences"],
    )
