"""Embedding service for policy similarity search."""

import structlog
from openai import OpenAI

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings for policies."""

    def __init__(self):
        """Initialize embedding service."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if hasattr(settings, "OPENAI_API_KEY") and settings.OPENAI_API_KEY else None
        self.model = "text-embedding-3-small"  # 1536 dimensions
        self.dimensions = 1536

    def generate_policy_text(
        self,
        subject: str,
        resource: str,
        action: str,
        conditions: str | None = None,
        description: str | None = None,
    ) -> str:
        """Generate text representation of policy for embedding.

        Args:
            subject: Policy subject (Who)
            resource: Policy resource (What)
            action: Policy action (How)
            conditions: Policy conditions (When)
            description: Policy description

        Returns:
            Formatted text representation

        """
        parts = [
            f"Subject: {subject}",
            f"Resource: {resource}",
            f"Action: {action}",
        ]

        if conditions:
            parts.append(f"Conditions: {conditions}")

        if description:
            parts.append(f"Description: {description}")

        return " | ".join(parts)

    async def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for given text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if service unavailable

        """
        if not self.client:
            logger.warning("OpenAI client not configured, skipping embedding generation")
            return None

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            embedding = response.data[0].embedding
            logger.info("embedding_generated", text_length=len(text), embedding_dim=len(embedding))
            return embedding

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e), text_length=len(text))
            return None

    async def generate_policy_embedding(
        self,
        subject: str,
        resource: str,
        action: str,
        conditions: str | None = None,
        description: str | None = None,
    ) -> list[float] | None:
        """Generate embedding for a policy.

        Args:
            subject: Policy subject (Who)
            resource: Policy resource (What)
            action: Policy action (How)
            conditions: Policy conditions (When)
            description: Policy description

        Returns:
            Embedding vector or None if service unavailable

        """
        text = self.generate_policy_text(subject, resource, action, conditions, description)
        return await self.generate_embedding(text)
