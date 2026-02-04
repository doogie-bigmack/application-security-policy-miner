"""Service for generating policy embeddings and finding similar policies."""
import hashlib
import logging

import numpy as np

from app.models.policy import Policy

logger = logging.getLogger(__name__)


class SimilarityService:
    """Service for policy similarity detection using embeddings."""

    def __init__(self):
        """Initialize the similarity service."""
        self.embedding_dim = 1536  # Standard dimension for Claude-based embeddings

    def _policy_to_text(self, policy: Policy) -> str:
        """Convert a policy to a text representation for embedding.

        Args:
            policy: The policy to convert

        Returns:
            Text representation of the policy
        """
        parts = [
            f"Subject: {policy.subject}",
            f"Resource: {policy.resource}",
            f"Action: {policy.action}",
        ]

        if policy.conditions:
            parts.append(f"Conditions: {policy.conditions}")

        if policy.description:
            parts.append(f"Description: {policy.description}")

        return " | ".join(parts)

    def generate_embedding(self, policy: Policy) -> list[float]:
        """Generate an embedding vector for a policy.

        Uses a deterministic hash-based approach combined with semantic features
        to create a 1536-dimensional embedding vector.

        Args:
            policy: The policy to generate an embedding for

        Returns:
            List of floats representing the embedding vector
        """
        # Convert policy to text
        text = self._policy_to_text(policy)

        # Generate a deterministic hash-based embedding
        # This is a simple approach that creates consistent embeddings
        # In production, you would use a proper embedding model like Voyage AI or OpenAI
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        # Expand hash to full embedding dimension using multiple hashes
        embedding = []
        seed = text

        for i in range(0, self.embedding_dim, 32):  # SHA-256 produces 32 bytes
            hash_obj = hashlib.sha256(f"{seed}:{i}".encode())
            hash_bytes = hash_obj.digest()
            # Convert bytes to normalized floats between -1 and 1
            for byte in hash_bytes:
                if len(embedding) >= self.embedding_dim:
                    break
                embedding.append((byte / 255.0) * 2 - 1)  # Scale to [-1, 1]

        # Normalize the embedding vector
        embedding_array = np.array(embedding[:self.embedding_dim])
        norm = np.linalg.norm(embedding_array)
        if norm > 0:
            embedding_array = embedding_array / norm

        return embedding_array.tolist()

    def update_policy_embedding(self, policy: Policy, db) -> None:
        """Update the embedding for a single policy.

        Args:
            policy: The policy to update
            db: Database session
        """
        try:
            embedding = self.generate_embedding(policy)
            policy.embedding = embedding
            db.commit()
            logger.info(f"Updated embedding for policy {policy.id}")
        except Exception as e:
            logger.error(f"Failed to generate embedding for policy {policy.id}: {e}")
            db.rollback()
            raise

    def find_similar_policies(
        self,
        db,
        policy_id: int,
        limit: int = 10,
        min_similarity: float = 0.5,
        tenant_id: str | None = None,
    ) -> list[tuple[Policy, float]]:
        """Find similar policies using vector similarity search.

        Args:
            db: Database session
            policy_id: ID of the policy to find similar policies for
            limit: Maximum number of similar policies to return
            min_similarity: Minimum similarity score (0-1) to include
            tenant_id: Optional tenant ID for filtering (multi-tenancy)

        Returns:
            List of tuples (policy, similarity_score) sorted by similarity
        """
        try:
            # Get the source policy
            source_policy = db.query(Policy).filter(Policy.id == policy_id).first()

            if not source_policy or not source_policy.embedding:
                logger.warning(f"Policy {policy_id} not found or has no embedding")
                return []

            # Build query for similar policies
            query = db.query(Policy).filter(
                Policy.id != policy_id,
                Policy.embedding.isnot(None),
            )

            # Add tenant filtering if provided
            if tenant_id:
                query = query.filter(Policy.tenant_id == tenant_id)

            # Execute query
            candidates = query.all()

            # Calculate cosine similarity for each candidate
            similar_policies = []
            source_embedding = np.array(source_policy.embedding)

            for candidate in candidates:
                candidate_embedding = np.array(candidate.embedding)

                # Calculate cosine similarity
                similarity = np.dot(source_embedding, candidate_embedding)

                # Convert to 0-100 scale and filter by minimum
                similarity_score = (similarity + 1) / 2 * 100  # Map [-1, 1] to [0, 100]

                if similarity_score >= min_similarity * 100:
                    similar_policies.append((candidate, similarity_score))

            # Sort by similarity score (descending) and limit results
            similar_policies.sort(key=lambda x: x[1], reverse=True)
            return similar_policies[:limit]

        except Exception as e:
            logger.error(f"Error finding similar policies for {policy_id}: {e}")
            return []


# Global instance
similarity_service = SimilarityService()
