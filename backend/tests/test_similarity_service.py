"""Test similar policy detection service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.embedding_service import EmbeddingService
from app.services.similarity_service import SimilarityService


@pytest.fixture
def mock_policy():
    """Create mock policy object."""
    policy = MagicMock()
    policy.id = 1
    policy.subject = "Manager"
    policy.resource = "Expense Report"
    policy.action = "approve"
    policy.conditions = "amount < $5000"
    policy.description = "Managers can approve expense reports under $5000"
    policy.embedding = [0.1] * 1536  # Mock embedding vector
    return policy


@pytest.fixture
def mock_similar_policy():
    """Create mock similar policy object."""
    policy = MagicMock()
    policy.id = 2
    policy.subject = "Senior Manager"
    policy.resource = "Expense Report"
    policy.action = "approve"
    policy.conditions = "amount < $10000"
    policy.description = "Senior managers can approve expense reports under $10000"
    policy.embedding = [0.15] * 1536  # Slightly different embedding
    return policy


class TestEmbeddingService:
    """Test embedding generation service."""

    def test_generate_policy_text(self):
        """Test policy text generation for embedding."""
        service = EmbeddingService()

        text = service.generate_policy_text(
            subject="Manager",
            resource="Expense Report",
            action="approve",
            conditions="amount < $5000",
            description="Test policy",
        )

        assert "Subject: Manager" in text
        assert "Resource: Expense Report" in text
        assert "Action: approve" in text
        assert "Conditions: amount < $5000" in text
        assert "Description: Test policy" in text

    def test_generate_policy_text_minimal(self):
        """Test policy text generation with minimal fields."""
        service = EmbeddingService()

        text = service.generate_policy_text(
            subject="User",
            resource="Document",
            action="read",
        )

        assert "Subject: User" in text
        assert "Resource: Document" in text
        assert "Action: read" in text
        assert "Conditions" not in text
        assert "Description" not in text

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.OpenAI")
    async def test_generate_embedding(self, mock_openai_class):
        """Test embedding generation."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Mock settings
        with patch("app.services.embedding_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"

            service = EmbeddingService()
            service.client = mock_client

            embedding = await service.generate_embedding("Test text")

            assert embedding is not None
            assert len(embedding) == 1536
            assert all(x == 0.1 for x in embedding)
            mock_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embedding_no_client(self):
        """Test embedding generation without configured client."""
        with patch("app.services.embedding_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = None

            service = EmbeddingService()
            service.client = None

            embedding = await service.generate_embedding("Test text")

            assert embedding is None

    @pytest.mark.asyncio
    @patch("app.services.embedding_service.OpenAI")
    async def test_generate_embedding_error(self, mock_openai_class):
        """Test embedding generation with API error."""
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        with patch("app.services.embedding_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"

            service = EmbeddingService()
            service.client = mock_client

            embedding = await service.generate_embedding("Test text")

            assert embedding is None


class TestSimilarityService:
    """Test similarity detection service."""

    @pytest.mark.asyncio
    async def test_find_similar_policies_no_policy(self, mock_policy):
        """Test find similar when policy doesn't exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = SimilarityService()
        similar = await service.find_similar_policies(
            db=mock_db,
            policy_id=999,
            limit=10,
        )

        assert similar == []

    @pytest.mark.asyncio
    async def test_find_similar_policies_no_embedding(self, mock_policy):
        """Test find similar when policy has no embedding."""
        mock_policy.embedding = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_policy
        mock_db.execute.return_value = mock_result

        service = SimilarityService()
        similar = await service.find_similar_policies(
            db=mock_db,
            policy_id=1,
            limit=10,
        )

        assert similar == []

    @pytest.mark.asyncio
    async def test_find_similar_policies_success(self, mock_policy, mock_similar_policy):
        """Test successful similar policy finding."""
        mock_db = AsyncMock()

        # Mock first query (get target policy)
        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none.return_value = mock_policy

        # Mock second query (find similar policies)
        mock_result_2 = MagicMock()
        mock_result_2.fetchall.return_value = [(2, 0.85)]  # policy_id=2, similarity=0.85

        # Mock third query (get similar policy details)
        mock_result_3 = MagicMock()
        mock_result_3.scalar_one_or_none.return_value = mock_similar_policy

        mock_db.execute.side_effect = [mock_result_1, mock_result_2, mock_result_3]

        service = SimilarityService()
        similar = await service.find_similar_policies(
            db=mock_db,
            policy_id=1,
            limit=10,
            min_similarity=0.7,
        )

        assert len(similar) == 1
        assert similar[0][0].id == 2
        assert similar[0][1] == 0.85

    @pytest.mark.asyncio
    @patch("app.services.similarity_service.EmbeddingService")
    async def test_find_similar_by_text(self, mock_embedding_service_class, mock_similar_policy):
        """Test finding similar policies by text criteria."""
        # Mock embedding service
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_policy_embedding.return_value = [0.1] * 1536
        mock_embedding_service_class.return_value = mock_embedding_service

        mock_db = AsyncMock()

        # Mock similarity search query
        mock_result_1 = MagicMock()
        mock_result_1.fetchall.return_value = [(2, 0.80)]

        # Mock get policy details query
        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none.return_value = mock_similar_policy

        mock_db.execute.side_effect = [mock_result_1, mock_result_2]

        service = SimilarityService()
        similar = await service.find_similar_by_text(
            db=mock_db,
            subject="Manager",
            resource="Expense Report",
            action="approve",
            conditions="amount < $5000",
            limit=10,
            min_similarity=0.7,
        )

        assert len(similar) == 1
        assert similar[0][0].id == 2
        assert similar[0][1] == 0.80
        mock_embedding_service.generate_policy_embedding.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.similarity_service.EmbeddingService")
    async def test_find_similar_by_text_no_embedding(self, mock_embedding_service_class):
        """Test finding similar policies when embedding generation fails."""
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_policy_embedding.return_value = None
        mock_embedding_service_class.return_value = mock_embedding_service

        mock_db = AsyncMock()

        service = SimilarityService()
        similar = await service.find_similar_by_text(
            db=mock_db,
            subject="Manager",
            resource="Expense Report",
            action="approve",
            limit=10,
        )

        assert similar == []
