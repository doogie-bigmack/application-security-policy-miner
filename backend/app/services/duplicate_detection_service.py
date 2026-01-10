"""Service for detecting duplicate policies across applications."""

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.policy import Policy

logger = structlog.get_logger(__name__)


class DuplicateDetectionService:
    """Service for detecting duplicate policies across applications."""

    def find_duplicates_across_applications(
        self,
        db: Session,
        tenant_id: str | None = None,
        min_similarity: float = 0.95,  # Higher threshold for duplicates
        application_ids: list[int] | None = None,
    ) -> list[dict]:
        """Find duplicate policies across multiple applications.

        Args:
            db: Database session
            tenant_id: Optional tenant filter
            min_similarity: Minimum similarity score to consider duplicates (0-1)
            application_ids: Optional list of application IDs to search within

        Returns:
            List of duplicate groups with:
                - policies: List of duplicate policy objects
                - similarity_score: Average similarity score
                - applications: List of affected applications
                - potential_savings: Number of duplicate policies that could be consolidated

        """
        # Build query to get all policies with embeddings
        query = select(Policy).where(Policy.embedding.isnot(None))

        if tenant_id:
            query = query.where(Policy.tenant_id == tenant_id)

        if application_ids:
            query = query.where(Policy.application_id.in_(application_ids))

        # Only consider policies with application_id
        query = query.where(Policy.application_id.isnot(None))

        result = db.execute(query)
        all_policies = result.scalars().all()

        logger.info(
            "finding_duplicates",
            total_policies=len(all_policies),
            min_similarity=min_similarity,
            application_count=len(set(p.application_id for p in all_policies if p.application_id)),
        )

        # Group duplicates using pgvector cosine similarity
        duplicate_groups = []
        processed_policy_ids = set()

        for policy in all_policies:
            if policy.id in processed_policy_ids:
                continue

            # Find similar policies using vector similarity
            similar_query = """
                SELECT
                    id,
                    1 - (embedding <=> :target_embedding::vector) as similarity
                FROM policies
                WHERE id != :policy_id
                AND embedding IS NOT NULL
                AND application_id IS NOT NULL
                AND application_id != :application_id
                AND (1 - (embedding <=> :target_embedding::vector)) >= :min_similarity
            """

            params = {
                "target_embedding": policy.embedding,
                "policy_id": policy.id,
                "application_id": policy.application_id,
                "min_similarity": min_similarity,
            }

            if tenant_id:
                similar_query += " AND tenant_id = :tenant_id"
                params["tenant_id"] = tenant_id

            similar_query += " ORDER BY embedding <=> :target_embedding::vector LIMIT 100"

            # Execute raw SQL for pgvector similarity
            from sqlalchemy import text
            result = db.execute(text(similar_query), params)
            rows = result.fetchall()

            if rows:
                # Fetch similar policy objects
                similar_policy_ids = [row[0] for row in rows]
                scores = {row[0]: float(row[1]) for row in rows}

                similar_policies = db.execute(
                    select(Policy).where(Policy.id.in_(similar_policy_ids))
                ).scalars().all()

                # Filter out already processed policies
                cross_app_similar = [
                    p for p in similar_policies
                    if p.id not in processed_policy_ids
                ]

                if cross_app_similar:
                    # Create duplicate group
                    group_policies = [policy] + cross_app_similar
                    score_values = [scores[p.id] for p in cross_app_similar]
                    avg_similarity = sum(score_values) / len(score_values) if score_values else 1.0

                    # Get unique applications
                    app_ids = list(set(p.application_id for p in group_policies if p.application_id))

                    # Fetch application details
                    app_result = db.execute(
                        select(Application).where(Application.id.in_(app_ids))
                    )
                    applications = app_result.scalars().all()

                    duplicate_groups.append({
                        "policies": group_policies,
                        "policy_ids": [p.id for p in group_policies],
                        "similarity_score": avg_similarity,
                        "applications": applications,
                        "application_count": len(applications),
                        "potential_savings": len(group_policies) - 1,  # Keep 1, remove others
                        "sample_policy": {
                            "subject": policy.subject,
                            "resource": policy.resource,
                            "action": policy.action,
                            "conditions": policy.conditions,
                        },
                    })

                    # Mark all policies in this group as processed
                    for p in group_policies:
                        processed_policy_ids.add(p.id)

        # Sort by potential savings (descending)
        duplicate_groups.sort(key=lambda g: g["potential_savings"], reverse=True)

        logger.info(
            "duplicates_found",
            duplicate_groups=len(duplicate_groups),
            total_duplicate_policies=sum(len(g["policies"]) for g in duplicate_groups),
            potential_savings=sum(g["potential_savings"] for g in duplicate_groups),
        )

        return duplicate_groups

    def get_duplicate_statistics(
        self,
        db: Session,
        tenant_id: str | None = None,
        min_similarity: float = 0.95,
    ) -> dict:
        """Get statistics about duplicate policies.

        Args:
            db: Database session
            tenant_id: Optional tenant filter
            min_similarity: Minimum similarity score to consider duplicates

        Returns:
            Statistics dict with:
                - total_policies: Total number of policies
                - total_duplicates: Number of duplicate policies
                - duplicate_groups: Number of duplicate groups
                - potential_savings_count: Number of policies that could be eliminated
                - potential_savings_percentage: Percentage reduction possible

        """
        # Get total policy count
        total_query = select(func.count(Policy.id))
        if tenant_id:
            total_query = total_query.where(Policy.tenant_id == tenant_id)

        result = db.execute(total_query)
        total_policies = result.scalar()

        # Find duplicates
        duplicate_groups = self.find_duplicates_across_applications(
            db=db,
            tenant_id=tenant_id,
            min_similarity=min_similarity,
        )

        total_duplicates = sum(len(g["policies"]) for g in duplicate_groups)
        potential_savings = sum(g["potential_savings"] for g in duplicate_groups)
        savings_percentage = (potential_savings / total_policies * 100) if total_policies > 0 else 0

        return {
            "total_policies": total_policies,
            "total_duplicates": total_duplicates,
            "duplicate_groups": len(duplicate_groups),
            "potential_savings_count": potential_savings,
            "potential_savings_percentage": round(savings_percentage, 1),
        }

    def consolidate_duplicate_group(
        self,
        db: Session,
        policy_ids: list[int],
        keep_policy_id: int,
    ) -> dict:
        """Consolidate a group of duplicate policies by keeping one and removing others.

        Args:
            db: Database session
            policy_ids: List of all policy IDs in the duplicate group
            keep_policy_id: ID of the policy to keep

        Returns:
            Result dict with:
                - kept_policy_id: ID of the kept policy
                - removed_policy_ids: List of removed policy IDs
                - removed_count: Number of policies removed

        """
        if keep_policy_id not in policy_ids:
            raise ValueError(f"keep_policy_id {keep_policy_id} not in policy_ids")

        # Get the policy to keep
        result = db.execute(
            select(Policy).where(Policy.id == keep_policy_id)
        )
        kept_policy = result.scalar_one_or_none()

        if not kept_policy:
            raise ValueError(f"Policy {keep_policy_id} not found")

        # Remove other policies
        remove_ids = [pid for pid in policy_ids if pid != keep_policy_id]

        for policy_id in remove_ids:
            result = db.execute(
                select(Policy).where(Policy.id == policy_id)
            )
            policy = result.scalar_one_or_none()
            if policy:
                db.delete(policy)

        db.commit()

        logger.info(
            "consolidated_duplicate_group",
            kept_policy_id=keep_policy_id,
            removed_count=len(remove_ids),
        )

        return {
            "kept_policy_id": keep_policy_id,
            "removed_policy_ids": remove_ids,
            "removed_count": len(remove_ids),
        }


# Singleton instance
duplicate_detection_service = DuplicateDetectionService()
