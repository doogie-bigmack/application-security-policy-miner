"""Service for detecting and managing duplicate policies across applications."""

from datetime import UTC, datetime

import structlog
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.duplicate_policy_group import (
    DuplicateGroupStatus,
    DuplicatePolicyGroup,
    DuplicatePolicyGroupMember,
)
from app.models.policy import Policy

logger = structlog.get_logger(__name__)


class DeduplicationService:
    """Service for detecting duplicate policies across applications."""

    def detect_duplicates(
        self,
        db: Session,
        min_similarity: float = 0.85,  # High threshold for duplicates
        tenant_id: str | None = None,
        repository_id: int | None = None,
    ) -> list[DuplicatePolicyGroup]:
        """Detect duplicate policies across applications.

        This method finds groups of policies that are semantically very similar
        (likely duplicates) and creates DuplicatePolicyGroup records for review.

        Args:
            db: Database session
            min_similarity: Minimum similarity score (0-1) to consider policies as duplicates
            tenant_id: Optional tenant ID for filtering
            repository_id: Optional repository ID for filtering

        Returns:
            List of newly created duplicate policy groups

        """
        logger.info(
            "starting_duplicate_detection",
            min_similarity=min_similarity,
            tenant_id=tenant_id,
            repository_id=repository_id,
        )

        # Get all policies with embeddings
        query = select(Policy).where(Policy.embedding.is_not(None))

        if tenant_id:
            query = query.where(Policy.tenant_id == tenant_id)
        if repository_id:
            query = query.where(Policy.repository_id == repository_id)

        result = db.execute(query)
        policies = result.scalars().all()

        logger.info("policies_loaded_for_deduplication", count=len(policies))

        # Track which policies are already in groups
        processed_policy_ids = set()
        duplicate_groups = []

        # For each policy, find similar policies
        for policy in policies:
            if policy.id in processed_policy_ids:
                continue

            # Find similar policies using pgvector
            query_text = """
                SELECT
                    id,
                    1 - (embedding <=> :target_embedding::vector) as similarity
                FROM policies
                WHERE id != :policy_id
                AND embedding IS NOT NULL
                AND (1 - (embedding <=> :target_embedding::vector)) >= :min_similarity
            """

            if tenant_id:
                query_text += " AND tenant_id = :tenant_id"

            query_text += """
                ORDER BY embedding <=> :target_embedding::vector
                LIMIT :limit
            """

            params = {
                "target_embedding": policy.embedding,
                "policy_id": policy.id,
                "min_similarity": min_similarity,
                "limit": 50,
            }

            if tenant_id:
                params["tenant_id"] = tenant_id

            result = db.execute(text(query_text), params)
            similar_rows = result.fetchall()

            # Fetch full policy objects
            similar_policies = []
            for row in similar_rows:
                similar_policy = db.query(Policy).filter(Policy.id == row[0]).first()
                if similar_policy and similar_policy.id not in processed_policy_ids:
                    similar_policies.append((similar_policy, float(row[1])))

            # If we found duplicates, create a group
            if similar_policies:
                group_policies = [policy] + [p for p, _ in similar_policies]
                similarity_scores = [1.0] + [score for _, score in similar_policies]

                # Calculate group statistics
                avg_similarity = sum(similarity_scores) / len(similarity_scores)
                min_similarity_in_group = min(similarity_scores)

                # Create duplicate group
                duplicate_group = DuplicatePolicyGroup(
                    tenant_id=tenant_id or policy.tenant_id,
                    status=DuplicateGroupStatus.DETECTED,
                    description=f"Duplicate policy group: {policy.subject} can {policy.action} {policy.resource}",
                    avg_similarity_score=avg_similarity,
                    min_similarity_score=min_similarity_in_group,
                    policy_count=len(group_policies),
                )

                db.add(duplicate_group)
                db.flush()  # Get the group ID

                # Add policies to the group
                for group_policy, similarity_score in zip(group_policies, similarity_scores):
                    member = DuplicatePolicyGroupMember(
                        group_id=duplicate_group.id,
                        policy_id=group_policy.id,
                        similarity_to_group=similarity_score,
                    )
                    db.add(member)
                    processed_policy_ids.add(group_policy.id)

                duplicate_groups.append(duplicate_group)

                logger.info(
                    "duplicate_group_created",
                    group_id=duplicate_group.id,
                    policy_count=len(group_policies),
                    avg_similarity=avg_similarity,
                )

        db.commit()

        logger.info(
            "duplicate_detection_complete",
            groups_created=len(duplicate_groups),
            policies_in_groups=len(processed_policy_ids),
        )

        return duplicate_groups

    def consolidate_duplicates(
        self,
        db: Session,
        group_id: int,
        consolidated_policy_id: int,
        notes: str | None = None,
    ) -> DuplicatePolicyGroup:
        """Consolidate a duplicate group by selecting one policy as the centralized version.

        Args:
            db: Database session
            group_id: ID of the duplicate group
            consolidated_policy_id: ID of the policy to use as the centralized version
            notes: Optional notes about the consolidation decision

        Returns:
            Updated duplicate policy group

        Raises:
            ValueError: If group not found or policy not in group

        """
        # Get the group
        result = db.execute(
            select(DuplicatePolicyGroup).where(DuplicatePolicyGroup.id == group_id)
        )
        group = result.scalar_one_or_none()

        if not group:
            raise ValueError(f"Duplicate group {group_id} not found")

        # Verify the policy is in the group
        member_result = db.execute(
            select(DuplicatePolicyGroupMember).where(
                DuplicatePolicyGroupMember.group_id == group_id,
                DuplicatePolicyGroupMember.policy_id == consolidated_policy_id,
            )
        )
        member = member_result.scalar_one_or_none()

        if not member:
            raise ValueError(
                f"Policy {consolidated_policy_id} is not in duplicate group {group_id}"
            )

        # Update the group
        group.status = DuplicateGroupStatus.CONSOLIDATED
        group.consolidated_policy_id = consolidated_policy_id
        group.consolidation_notes = notes
        group.consolidated_at = datetime.now(UTC)

        db.commit()
        db.refresh(group)

        logger.info(
            "duplicates_consolidated",
            group_id=group_id,
            consolidated_policy_id=consolidated_policy_id,
        )

        return group

    def dismiss_duplicates(
        self,
        db: Session,
        group_id: int,
        notes: str | None = None,
    ) -> DuplicatePolicyGroup:
        """Dismiss a duplicate group as a false positive.

        Args:
            db: Database session
            group_id: ID of the duplicate group
            notes: Optional notes about why this is not a duplicate

        Returns:
            Updated duplicate policy group

        Raises:
            ValueError: If group not found

        """
        # Get the group
        result = db.execute(
            select(DuplicatePolicyGroup).where(DuplicatePolicyGroup.id == group_id)
        )
        group = result.scalar_one_or_none()

        if not group:
            raise ValueError(f"Duplicate group {group_id} not found")

        # Update the group
        group.status = DuplicateGroupStatus.DISMISSED
        group.consolidation_notes = notes

        db.commit()
        db.refresh(group)

        logger.info("duplicates_dismissed", group_id=group_id)

        return group

    def get_duplicate_groups(
        self,
        db: Session,
        tenant_id: str | None = None,
        status: DuplicateGroupStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DuplicatePolicyGroup]:
        """Get duplicate policy groups.

        Args:
            db: Database session
            tenant_id: Optional tenant ID for filtering
            status: Optional status filter
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of duplicate policy groups

        """
        query = select(DuplicatePolicyGroup)

        if tenant_id:
            query = query.where(DuplicatePolicyGroup.tenant_id == tenant_id)
        if status:
            query = query.where(DuplicatePolicyGroup.status == status)

        query = query.order_by(DuplicatePolicyGroup.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = db.execute(query)
        groups = result.scalars().all()

        return list(groups)

    def get_duplicate_group_with_policies(
        self,
        db: Session,
        group_id: int,
    ) -> tuple[DuplicatePolicyGroup, list[tuple[Policy, float]]] | None:
        """Get a duplicate group with all its policies.

        Args:
            db: Database session
            group_id: ID of the duplicate group

        Returns:
            Tuple of (group, list of (policy, similarity_score)) or None if not found

        """
        # Get the group
        result = db.execute(
            select(DuplicatePolicyGroup).where(DuplicatePolicyGroup.id == group_id)
        )
        group = result.scalar_one_or_none()

        if not group:
            return None

        # Get members with their policies
        members_result = db.execute(
            select(DuplicatePolicyGroupMember, Policy)
            .join(Policy, DuplicatePolicyGroupMember.policy_id == Policy.id)
            .where(DuplicatePolicyGroupMember.group_id == group_id)
            .order_by(DuplicatePolicyGroupMember.similarity_to_group.desc())
        )
        members = members_result.all()

        policies_with_scores = [
            (policy, member.similarity_to_group)
            for member, policy in members
        ]

        return group, policies_with_scores


# Singleton instance for import
deduplication_service = DeduplicationService()
