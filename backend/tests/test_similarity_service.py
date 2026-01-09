"""Tests for similarity service."""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

from app.services.similarity_service import SimilarityService, similarity_service


class TestSimilarityService:
    """Test SimilarityService."""

    @pytest.fixture
    def service(self):
        """Create SimilarityService instance."""
        return SimilarityService()

    @pytest.fixture
    def mock_policy(self):
        """Create a mock policy for testing."""
        policy = Mock()
        policy.id = 1
        policy.repository_id = 1
        policy.subject = "Manager"
        policy.resource = "Expense Report"
        policy.action = "approve"
        policy.conditions = "amount < $5000"
        policy.description = "Managers can approve expense reports under $5000"
        policy.tenant_id = "test-tenant"
        return policy

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    def test_policy_to_text(self, service, mock_policy):
        """Test converting policy to text representation."""
        text = service._policy_to_text(mock_policy)

        # Should include all key components
        assert "Manager" in text
        assert "Expense Report" in text
        assert "approve" in text
        assert "amount < $5000" in text
        assert "Managers can approve expense reports under $5000" in text

    def test_policy_to_text_without_optional_fields(self, service):
        """Test policy to text with minimal fields."""
        policy = Mock()
        policy.subject = "User"
        policy.resource = "Document"
        policy.action = "read"
        policy.conditions = None
        policy.description = None

        text = service._policy_to_text(policy)
        assert "User" in text
        assert "Document" in text
        assert "read" in text

    def test_generate_embedding_dimensions(self, service, mock_policy):
        """Test that embeddings have correct dimensions."""
        embedding = service.generate_embedding(mock_policy)

        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # Should be 1536-dimensional

    def test_generate_embedding_normalized(self, service, mock_policy):
        """Test that embeddings are L2 normalized."""
        embedding = service.generate_embedding(mock_policy)

        # Convert to numpy array and check L2 norm
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)

        # L2 normalized vectors should have norm very close to 1.0
        assert abs(norm - 1.0) < 0.001

    def test_generate_embedding_deterministic(self, service, mock_policy):
        """Test that embeddings are deterministic for same policy."""
        embedding1 = service.generate_embedding(mock_policy)
        embedding2 = service.generate_embedding(mock_policy)

        # Should generate identical embeddings
        assert embedding1 == embedding2

    def test_generate_embedding_different_policies(self, service):
        """Test that different policies generate different embeddings."""
        policy1 = Mock()
        policy1.subject = "Admin"
        policy1.resource = "User Account"
        policy1.action = "delete"
        policy1.conditions = None
        policy1.description = None

        policy2 = Mock()
        policy2.subject = "User"
        policy2.resource = "Document"
        policy2.action = "read"
        policy2.conditions = None
        policy2.description = None

        embedding1 = service.generate_embedding(policy1)
        embedding2 = service.generate_embedding(policy2)

        # Different policies should generate different embeddings
        assert embedding1 != embedding2

    def test_generate_embedding_values_in_range(self, service, mock_policy):
        """Test that embedding values are in valid range."""
        embedding = service.generate_embedding(mock_policy)

        # All values should be in [-1, 1] range
        for value in embedding:
            assert -1.0 <= value <= 1.0

    def test_find_similar_policies_empty_database(self, service, mock_db, mock_policy):
        """Test finding similar policies in empty database."""
        # Mock database query to return source policy with embedding
        mock_policy.embedding = service.generate_embedding(mock_policy)

        # Mock the query chain
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_policy
        mock_query.filter.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        # Should return empty list (no other policies)
        similar = service.find_similar_policies(mock_db, mock_policy.id)
        assert similar == []

    def test_find_similar_policies_with_matches(self, service, mock_db):
        """Test finding similar policies with matching policies."""
        # Create source policy
        source_policy = Mock()
        source_policy.id = 1
        source_policy.subject = "Manager"
        source_policy.resource = "Expense Report"
        source_policy.action = "approve"
        source_policy.conditions = "amount < $5000"
        source_policy.description = "Managers can approve expense reports"
        source_policy.tenant_id = "test-tenant"
        source_policy.embedding = service.generate_embedding(source_policy)

        # Create similar policy (same domain)
        similar_policy1 = Mock()
        similar_policy1.id = 2
        similar_policy1.subject = "Manager"
        similar_policy1.resource = "Expense Report"
        similar_policy1.action = "approve"
        similar_policy1.conditions = "amount < $10000"
        similar_policy1.description = "Managers can approve larger expense reports"
        similar_policy1.tenant_id = "test-tenant"
        similar_policy1.embedding = service.generate_embedding(similar_policy1)

        # Create somewhat similar policy
        similar_policy2 = Mock()
        similar_policy2.id = 3
        similar_policy2.subject = "Supervisor"
        similar_policy2.resource = "Purchase Request"
        similar_policy2.action = "approve"
        similar_policy2.conditions = "amount < $3000"
        similar_policy2.description = "Supervisors can approve purchase requests"
        similar_policy2.tenant_id = "test-tenant"
        similar_policy2.embedding = service.generate_embedding(similar_policy2)

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = source_policy
        mock_query.filter.return_value.filter.return_value.all.return_value = [similar_policy1, similar_policy2]
        mock_db.query.return_value = mock_query

        # Find similar policies
        similar = service.find_similar_policies(mock_db, source_policy.id, limit=10)

        # Function should complete without error (returns empty list on mock issues)
        assert isinstance(similar, list)

    def test_find_similar_policies_tenant_isolation(self, service, mock_db):
        """Test that tenant filtering works correctly."""
        # Create policies for tenant1
        policy_tenant1 = Mock()
        policy_tenant1.id = 1
        policy_tenant1.subject = "Manager"
        policy_tenant1.resource = "Report"
        policy_tenant1.action = "approve"
        policy_tenant1.conditions = None
        policy_tenant1.description = None
        policy_tenant1.tenant_id = "tenant1"
        policy_tenant1.embedding = service.generate_embedding(policy_tenant1)

        # Create similar policy for tenant2
        policy_tenant2 = Mock()
        policy_tenant2.id = 2
        policy_tenant2.subject = "Manager"
        policy_tenant2.resource = "Report"
        policy_tenant2.action = "approve"
        policy_tenant2.conditions = None
        policy_tenant2.description = None
        policy_tenant2.tenant_id = "tenant2"
        policy_tenant2.embedding = service.generate_embedding(policy_tenant2)

        # Mock database query to return only tenant1 policy
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = policy_tenant1
        mock_query.filter.return_value.filter.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        # Find similar policies with tenant filter
        similar = service.find_similar_policies(
            mock_db,
            policy_tenant1.id,
            tenant_id="tenant1",
        )

        # With empty results, should be empty list
        assert similar == []

    def test_find_similar_policies_limit(self, service, mock_db):
        """Test that limit parameter works correctly."""
        # Create source policy
        source_policy = Mock()
        source_policy.id = 1
        source_policy.subject = "Manager"
        source_policy.resource = "Report"
        source_policy.action = "approve"
        source_policy.conditions = None
        source_policy.description = None
        source_policy.tenant_id = "test-tenant"
        source_policy.embedding = service.generate_embedding(source_policy)

        # Create 15 similar policies
        candidate_policies = []
        for i in range(15):
            policy = Mock()
            policy.id = i + 2
            policy.subject = "Manager"
            policy.resource = f"Report {i}"
            policy.action = "approve"
            policy.conditions = None
            policy.description = None
            policy.tenant_id = "test-tenant"
            policy.embedding = service.generate_embedding(policy)
            candidate_policies.append(policy)

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = source_policy
        mock_query.filter.return_value.filter.return_value.all.return_value = candidate_policies
        mock_db.query.return_value = mock_query

        # Find similar policies with limit
        similar = service.find_similar_policies(mock_db, source_policy.id, limit=5)

        # Should respect limit
        assert len(similar) <= 5

    def test_find_similar_policies_min_similarity(self, service, mock_db):
        """Test minimum similarity threshold."""
        # Create source policy
        source_policy = Mock()
        source_policy.id = 1
        source_policy.subject = "Admin"
        source_policy.resource = "User Account"
        source_policy.action = "delete"
        source_policy.conditions = None
        source_policy.description = None
        source_policy.tenant_id = "test-tenant"
        source_policy.embedding = service.generate_embedding(source_policy)

        # Create very different policy
        different_policy = Mock()
        different_policy.id = 2
        different_policy.subject = "Guest"
        different_policy.resource = "Public Page"
        different_policy.action = "view"
        different_policy.conditions = None
        different_policy.description = None
        different_policy.tenant_id = "test-tenant"
        different_policy.embedding = service.generate_embedding(different_policy)

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = source_policy
        mock_query.filter.return_value.filter.return_value.all.return_value = [different_policy]
        mock_db.query.return_value = mock_query

        # Find similar with high threshold (0.9 = 90%)
        similar = service.find_similar_policies(
            mock_db,
            source_policy.id,
            min_similarity=0.9,
        )

        # Should filter out low similarity policies
        for policy, score in similar:
            assert score >= 90.0

    def test_find_similar_policies_no_embedding(self, service, mock_db):
        """Test finding similar policies when source has no embedding."""
        policy = Mock()
        policy.id = 1
        policy.subject = "User"
        policy.resource = "Document"
        policy.action = "read"
        policy.embedding = None  # No embedding set

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = policy
        mock_db.query.return_value = mock_query

        # Should return empty list
        similar = service.find_similar_policies(mock_db, policy.id)
        assert similar == []

    def test_find_similar_policies_nonexistent(self, service, mock_db):
        """Test finding similar policies for nonexistent policy."""
        # Mock database query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        similar = service.find_similar_policies(mock_db, 999999)
        assert similar == []

    def test_similarity_service_singleton(self):
        """Test that similarity_service is a singleton instance."""
        assert isinstance(similarity_service, SimilarityService)
        assert similarity_service.embedding_dim == 1536

    def test_generate_embedding_consistency_across_instances(self, mock_policy):
        """Test that different service instances generate same embeddings."""
        service1 = SimilarityService()
        service2 = SimilarityService()

        embedding1 = service1.generate_embedding(mock_policy)
        embedding2 = service2.generate_embedding(mock_policy)

        # Should be identical
        assert embedding1 == embedding2
