"""Auto-approval settings and tracking models."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from .repository import Base


class AutoApprovalSettings(Base):
    """Auto-approval settings per tenant."""

    __tablename__ = "auto_approval_settings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, unique=True, index=True)

    # Auto-approval configuration
    enabled = Column(Boolean, default=False, nullable=False)
    risk_threshold = Column(Float, default=30.0, nullable=False)  # Auto-approve if risk_score <= threshold
    min_historical_approvals = Column(Integer, default=3, nullable=False)  # Minimum similar approvals needed

    # Metrics
    total_auto_approvals = Column(Integer, default=0, nullable=False)
    total_policies_scanned = Column(Integer, default=0, nullable=False)
    auto_approval_rate = Column(Float, default=0.0, nullable=False)  # Percentage

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<AutoApprovalSettings tenant={self.tenant_id} enabled={self.enabled}>"


class AutoApprovalDecision(Base):
    """Track auto-approval decisions for audit trail."""

    __tablename__ = "auto_approval_decisions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    policy_id = Column(Integer, nullable=False, index=True)

    # Decision details
    auto_approved = Column(Boolean, nullable=False)
    reasoning = Column(Text, nullable=False)  # AI-generated explanation
    risk_score = Column(Float, nullable=False)
    similar_policies_count = Column(Integer, default=0, nullable=False)

    # Pattern matching results
    matched_patterns = Column(Text, nullable=True)  # JSON string of matched patterns

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        """String representation."""
        return f"<AutoApprovalDecision policy_id={self.policy_id} approved={self.auto_approved}>"
