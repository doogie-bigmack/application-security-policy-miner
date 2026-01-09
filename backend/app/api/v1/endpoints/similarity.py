"""Similarity detection endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.schemas.policy import Policy
from app.services.similarity_service import similarity_service

router = APIRouter()
logger = logging.getLogger(__name__)


class SimilarPolicyResponse(BaseModel):
    """Response model for similar policy with similarity score."""

    policy: Policy
    similarity_score: float = Field(..., ge=0, le=100, description="Similarity score (0-100%)")


class SimilarPoliciesResponse(BaseModel):
    """Response model for list of similar policies."""

    source_policy_id: int
    similar_policies: list[SimilarPolicyResponse]
    count: int


@router.get("/policies/{policy_id}/similar", response_model=SimilarPoliciesResponse)
def find_similar_policies(
    policy_id: int,
    limit: int = 10,
    min_similarity: float = 0.5,
    db: Session = Depends(get_db),
    tenant_id: str | None = Depends(get_tenant_id),
):
    """Find policies similar to the given policy.

    Uses vector embeddings to find semantically similar policies across all applications.

    Args:
        policy_id: ID of the policy to find similar policies for
        limit: Maximum number of similar policies to return (default: 10)
        min_similarity: Minimum similarity score 0-1 to include (default: 0.5 = 50%)
        tenant_id: Tenant ID for filtering (automatically extracted from JWT)

    Returns:
        List of similar policies with similarity scores
    """
    try:
        # Find similar policies
        similar_policies = similarity_service.find_similar_policies(
            db=db,
            policy_id=policy_id,
            limit=limit,
            min_similarity=min_similarity,
            tenant_id=tenant_id,
        )

        # Convert to response format
        similar_policy_responses = [
            SimilarPolicyResponse(
                policy=Policy.model_validate(policy),
                similarity_score=score,
            )
            for policy, score in similar_policies
        ]

        return SimilarPoliciesResponse(
            source_policy_id=policy_id,
            similar_policies=similar_policy_responses,
            count=len(similar_policy_responses),
        )

    except Exception as e:
        logger.error(f"Error finding similar policies for {policy_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to find similar policies: {str(e)}")
