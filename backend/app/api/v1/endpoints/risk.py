"""Risk analysis API endpoints."""
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.policy import Policy, RiskLevel

logger = logging.getLogger(__name__)

router = APIRouter()


class RiskDistribution(BaseModel):
    """Risk distribution statistics."""

    high: int
    medium: int
    low: int
    unscored: int


class RiskMetrics(BaseModel):
    """Overall risk metrics."""

    total_policies: int
    average_risk_score: float
    average_complexity: float
    average_impact: float
    average_confidence: float
    distribution: RiskDistribution


class RiskThresholds(BaseModel):
    """Risk threshold configuration."""

    high_threshold: float = 70.0  # >= 70 is high risk
    medium_threshold: float = 40.0  # >= 40 is medium risk
    # < 40 is low risk


@router.get("/metrics", response_model=RiskMetrics)
async def get_risk_metrics(db: Session = Depends(get_db)) -> RiskMetrics:
    """Get overall risk metrics and distribution.

    Args:
        db: Database session

    Returns:
        Risk metrics including distribution and averages
    """
    # Count policies by risk level
    high_count = db.query(Policy).filter(Policy.risk_level == RiskLevel.HIGH).count()
    medium_count = db.query(Policy).filter(Policy.risk_level == RiskLevel.MEDIUM).count()
    low_count = db.query(Policy).filter(Policy.risk_level == RiskLevel.LOW).count()
    unscored_count = db.query(Policy).filter(Policy.risk_level.is_(None)).count()

    total = db.query(Policy).count()

    # Calculate averages (excluding None values)
    avg_risk = db.query(func.avg(Policy.risk_score)).filter(Policy.risk_score.isnot(None)).scalar()
    avg_complexity = (
        db.query(func.avg(Policy.complexity_score)).filter(Policy.complexity_score.isnot(None)).scalar()
    )
    avg_impact = db.query(func.avg(Policy.impact_score)).filter(Policy.impact_score.isnot(None)).scalar()
    avg_confidence = (
        db.query(func.avg(Policy.confidence_score)).filter(Policy.confidence_score.isnot(None)).scalar()
    )

    return RiskMetrics(
        total_policies=total,
        average_risk_score=round(avg_risk or 0.0, 2),
        average_complexity=round(avg_complexity or 0.0, 2),
        average_impact=round(avg_impact or 0.0, 2),
        average_confidence=round(avg_confidence or 0.0, 2),
        distribution=RiskDistribution(
            high=high_count,
            medium=medium_count,
            low=low_count,
            unscored=unscored_count,
        ),
    )


@router.get("/policies/by-level/{risk_level}")
async def get_policies_by_risk_level(
    risk_level: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get policies filtered by risk level.

    Args:
        risk_level: Risk level (high/medium/low/unscored)
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of policies with the specified risk level
    """
    query = db.query(Policy)

    if risk_level == "unscored":
        query = query.filter(Policy.risk_level.is_(None))
    else:
        try:
            risk_enum = RiskLevel(risk_level)
            query = query.filter(Policy.risk_level == risk_enum)
        except ValueError:
            return {"policies": [], "total": 0, "error": f"Invalid risk level: {risk_level}"}

    total = query.count()
    policies = query.offset(skip).limit(limit).all()

    return {
        "policies": [
            {
                "id": p.id,
                "subject": p.subject,
                "resource": p.resource,
                "action": p.action,
                "risk_score": p.risk_score,
                "risk_level": p.risk_level.value if p.risk_level else None,
                "complexity_score": p.complexity_score,
                "impact_score": p.impact_score,
                "confidence_score": p.confidence_score,
                "historical_score": p.historical_score,
                "status": p.status.value,
                "repository_id": p.repository_id,
            }
            for p in policies
        ],
        "total": total,
    }


@router.get("/thresholds", response_model=RiskThresholds)
async def get_risk_thresholds() -> RiskThresholds:
    """Get current risk thresholds.

    Returns:
        Risk threshold configuration
    """
    return RiskThresholds()


@router.put("/thresholds", response_model=RiskThresholds)
async def update_risk_thresholds(thresholds: RiskThresholds) -> RiskThresholds:
    """Update risk thresholds.

    Args:
        thresholds: New threshold configuration

    Returns:
        Updated threshold configuration
    """
    # TODO: Store thresholds in database or configuration
    # For now, just return the provided thresholds
    logger.info(
        "Risk thresholds updated",
        extra={
            "high_threshold": thresholds.high_threshold,
            "medium_threshold": thresholds.medium_threshold,
        },
    )
    return thresholds
