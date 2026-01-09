"""Similarity service for finding similar policies."""

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import Policy
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)


class SimilarityService:
    """Service for finding similar policies using vector embeddings."""

    def __init__(self):
        """Initialize similarity service."""
        self.embedding_service = EmbeddingService()

    async def find_similar_policies(
        self,
        db: AsyncSession,
        policy_id: int,
        limit: int = 10,
        min_similarity: float = 0.7,
        tenant_id: str | None = None,
    ) -> list[tuple[Policy, float]]:
        """Find policies similar to the given policy.

        Args:
            db: Database session
            policy_id: ID of the policy to find similarities for
            limit: Maximum number of similar policies to return
            min_similarity: Minimum cosine similarity threshold (0-1)
            tenant_id: Tenant ID for filtering

        Returns:
            List of (policy, similarity_score) tuples, sorted by similarity descending

        """
        # Get the target policy
        result = await db.execute(
            select(Policy).where(Policy.id == policy_id)
        )
        target_policy = result.scalar_one_or_none()

        if not target_policy:
            logger.error("policy_not_found", policy_id=policy_id)
            return []

        if target_policy.embedding is None:
            logger.warning("policy_has_no_embedding", policy_id=policy_id)
            return []

        # Build query with pgvector cosine similarity
        # Using <=> operator for cosine distance (lower is more similar)
        # Convert to similarity: 1 - distance
        query = """
            SELECT
                id,
                1 - (embedding <=> :target_embedding::vector) as similarity
            FROM policies
            WHERE id != :policy_id
            AND embedding IS NOT NULL
        """

        # Add tenant filtering if provided
        if tenant_id:
            query += " AND tenant_id = :tenant_id"

        # Add similarity threshold and ordering
        query += """
            AND (1 - (embedding <=> :target_embedding::vector)) >= :min_similarity
            ORDER BY embedding <=> :target_embedding::vector
            LIMIT :limit
        """

        params = {
            "target_embedding": target_policy.embedding,
            "policy_id": policy_id,
            "min_similarity": min_similarity,
            "limit": limit,
        }

        if tenant_id:
            params["tenant_id"] = tenant_id

        # Execute raw SQL query
        result = await db.execute(text(query), params)
        rows = result.fetchall()

        logger.info(
            "similar_policies_found",
            policy_id=policy_id,
            count=len(rows),
            min_similarity=min_similarity,
        )

        # Fetch full policy objects
        similar_policies = []
        for row in rows:
            policy_result = await db.execute(
                select(Policy).where(Policy.id == row[0])
            )
            policy = policy_result.scalar_one_or_none()
            if policy:
                similar_policies.append((policy, float(row[1])))

        return similar_policies

    async def find_similar_by_text(
        self,
        db: AsyncSession,
        subject: str,
        resource: str,
        action: str,
        conditions: str | None = None,
        description: str | None = None,
        limit: int = 10,
        min_similarity: float = 0.7,
        tenant_id: str | None = None,
    ) -> list[tuple[Policy, float]]:
        """Find policies similar to the given criteria.

        Args:
            db: Database session
            subject: Policy subject
            resource: Policy resource
            action: Policy action
            conditions: Policy conditions
            description: Policy description
            limit: Maximum number of similar policies to return
            min_similarity: Minimum cosine similarity threshold (0-1)
            tenant_id: Tenant ID for filtering

        Returns:
            List of (policy, similarity_score) tuples, sorted by similarity descending

        """
        # Generate embedding for the search criteria
        embedding = await self.embedding_service.generate_policy_embedding(
            subject=subject,
            resource=resource,
            action=action,
            conditions=conditions,
            description=description,
        )

        if not embedding:
            logger.error("failed_to_generate_search_embedding")
            return []

        # Build query with pgvector cosine similarity
        query = """
            SELECT
                id,
                1 - (embedding <=> :target_embedding::vector) as similarity
            FROM policies
            WHERE embedding IS NOT NULL
        """

        # Add tenant filtering if provided
        if tenant_id:
            query += " AND tenant_id = :tenant_id"

        # Add similarity threshold and ordering
        query += """
            AND (1 - (embedding <=> :target_embedding::vector)) >= :min_similarity
            ORDER BY embedding <=> :target_embedding::vector
            LIMIT :limit
        """

        params = {
            "target_embedding": embedding,
            "min_similarity": min_similarity,
            "limit": limit,
        }

        if tenant_id:
            params["tenant_id"] = tenant_id

        # Execute raw SQL query
        result = await db.execute(text(query), params)
        rows = result.fetchall()

        logger.info(
            "similar_policies_found_by_text",
            count=len(rows),
            min_similarity=min_similarity,
        )

        # Fetch full policy objects
        similar_policies = []
        for row in rows:
            policy_result = await db.execute(
                select(Policy).where(Policy.id == row[0])
            )
            policy = policy_result.scalar_one_or_none()
            if policy:
                similar_policies.append((policy, float(row[1])))

        return similar_policies


# Singleton instance for import
similarity_service = SimilarityService()
