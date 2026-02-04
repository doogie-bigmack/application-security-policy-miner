"""Schemas for duplicate policy groups."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.duplicate_policy_group import DuplicateGroupStatus
from app.schemas.policy import PolicyBase


class DuplicatePolicyGroupMemberBase(BaseModel):
    """Base schema for duplicate policy group member."""

    policy_id: int
    similarity_to_group: float = Field(ge=0.0, le=1.0, description="Similarity score to group (0-1)")


class DuplicatePolicyGroupMemberWithPolicy(DuplicatePolicyGroupMemberBase):
    """Duplicate policy group member with policy details."""

    policy: PolicyBase

    class Config:
        """Pydantic config."""

        from_attributes = True


class DuplicatePolicyGroupBase(BaseModel):
    """Base schema for duplicate policy group."""

    status: DuplicateGroupStatus
    group_name: str | None = None
    description: str | None = None
    avg_similarity_score: float = Field(ge=0.0, le=1.0, description="Average similarity score (0-1)")
    min_similarity_score: float = Field(ge=0.0, le=1.0, description="Minimum similarity score (0-1)")
    policy_count: int = Field(ge=2, description="Number of policies in group")


class DuplicatePolicyGroupCreate(BaseModel):
    """Schema for creating duplicate policy group."""

    group_name: str | None = None
    description: str | None = None


class DuplicatePolicyGroupResponse(DuplicatePolicyGroupBase):
    """Schema for duplicate policy group response."""

    id: int
    tenant_id: str
    consolidated_policy_id: int | None = None
    consolidation_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    consolidated_at: datetime | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class DuplicatePolicyGroupWithPolicies(DuplicatePolicyGroupResponse):
    """Schema for duplicate policy group with all policies."""

    policies: list[DuplicatePolicyGroupMemberWithPolicy]


class DuplicateDetectionRequest(BaseModel):
    """Schema for duplicate detection request."""

    min_similarity: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score to consider policies as duplicates (0-1)",
    )
    repository_id: int | None = Field(
        default=None,
        description="Optional repository ID to limit detection scope",
    )


class DuplicateDetectionResponse(BaseModel):
    """Schema for duplicate detection response."""

    groups_created: int
    policies_in_groups: int
    groups: list[DuplicatePolicyGroupResponse]


class ConsolidateRequest(BaseModel):
    """Schema for consolidating duplicates."""

    consolidated_policy_id: int = Field(description="ID of the policy to use as centralized version")
    notes: str | None = Field(default=None, description="Optional notes about consolidation decision")


class DismissRequest(BaseModel):
    """Schema for dismissing duplicates."""

    notes: str | None = Field(default=None, description="Optional notes about why this is not a duplicate")
