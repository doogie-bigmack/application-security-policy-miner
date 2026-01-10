"""Schemas for duplicate policy detection."""

from pydantic import BaseModel, Field


class DuplicateStatistics(BaseModel):
    """Statistics about duplicate policies."""

    total_policies: int = Field(..., description="Total number of policies")
    total_duplicates: int = Field(..., description="Total number of duplicate policies")
    duplicate_groups: int = Field(..., description="Number of duplicate groups")
    potential_savings_count: int = Field(..., description="Number of policies that could be eliminated")
    potential_savings_percentage: float = Field(..., description="Percentage reduction possible")


class ApplicationSummary(BaseModel):
    """Summary of an application."""

    id: int
    name: str
    business_unit_id: int | None = None


class SamplePolicy(BaseModel):
    """Sample policy representation."""

    subject: str
    resource: str
    action: str
    conditions: str | None = None


class DuplicateGroup(BaseModel):
    """A group of duplicate policies across applications."""

    policy_ids: list[int] = Field(..., description="List of policy IDs in this duplicate group")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Average similarity score")
    application_count: int = Field(..., description="Number of applications with this duplicate")
    potential_savings: int = Field(..., description="Number of duplicate policies that could be removed")
    sample_policy: SamplePolicy = Field(..., description="Sample policy from the group")
    applications: list[ApplicationSummary] = Field(..., description="Applications affected by this duplicate")


class ConsolidateRequest(BaseModel):
    """Request to consolidate duplicate policies."""

    policy_ids: list[int] = Field(..., min_length=2, description="List of policy IDs to consolidate")
    keep_policy_id: int = Field(..., description="ID of the policy to keep")


class ConsolidateResponse(BaseModel):
    """Response from consolidating duplicate policies."""

    kept_policy_id: int = Field(..., description="ID of the policy that was kept")
    removed_policy_ids: list[int] = Field(..., description="IDs of policies that were removed")
    removed_count: int = Field(..., description="Number of policies removed")
