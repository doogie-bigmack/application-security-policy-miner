"""Unit tests for webhook endpoints."""
import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.webhooks import verify_github_signature
from app.main import app
from app.models.repository import Repository, RepositoryStatus, RepositoryType


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Mock database session."""
    return MagicMock(spec=Session)


def test_verify_github_signature_valid():
    """Test GitHub signature verification with valid signature."""
    payload = b'{"ref":"refs/heads/main"}'
    secret = "test-secret-key"

    # Generate valid signature
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    signature = f"sha256={mac.hexdigest()}"

    result = verify_github_signature(payload, signature, secret)
    assert result is True


def test_verify_github_signature_invalid():
    """Test GitHub signature verification with invalid signature."""
    payload = b'{"ref":"refs/heads/main"}'
    secret = "test-secret-key"
    signature = "sha256=invalid_signature"

    result = verify_github_signature(payload, signature, secret)
    assert result is False


def test_verify_github_signature_no_header():
    """Test GitHub signature verification with missing header."""
    payload = b'{"ref":"refs/heads/main"}'
    secret = "test-secret-key"

    result = verify_github_signature(payload, None, secret)
    assert result is False


def test_verify_github_signature_wrong_algorithm():
    """Test GitHub signature verification with wrong algorithm."""
    payload = b'{"ref":"refs/heads/main"}'
    secret = "test-secret-key"
    signature = "md5=somehash"

    result = verify_github_signature(payload, signature, secret)
    assert result is False


def test_verify_github_signature_malformed_header():
    """Test GitHub signature verification with malformed header."""
    payload = b'{"ref":"refs/heads/main"}'
    secret = "test-secret-key"
    signature = "invalid_format"

    result = verify_github_signature(payload, signature, secret)
    assert result is False


def test_generate_webhook_secret(client, db_session):
    """Test webhook secret generation endpoint."""
    # Create mock repository
    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = 1
    mock_repo.webhook_secret = None
    mock_repo.webhook_enabled = 0

    with patch("app.api.v1.webhooks.RepositoryService") as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.get_repository.return_value = mock_repo

        response = client.post("/api/v1/webhooks/1/generate-secret")

        assert response.status_code == 200
        data = response.json()
        assert "webhook_secret" in data
        assert "webhook_url" in data
        assert "instructions" in data
        assert data["webhook_url"] == "/api/v1/webhooks/github"
        assert len(data["webhook_secret"]) > 20  # Should be a long random string


def test_generate_webhook_secret_repository_not_found(client):
    """Test webhook secret generation for non-existent repository."""
    with patch("app.api.v1.webhooks.RepositoryService") as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.get_repository.return_value = None

        response = client.post("/api/v1/webhooks/999/generate-secret")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_github_webhook_push_event(client):
    """Test GitHub webhook with push event."""
    # Create mock repository
    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = 1
    mock_repo.tenant_id = "test-tenant"
    mock_repo.webhook_enabled = 1
    mock_repo.webhook_secret = "test-secret"
    mock_repo.source_url = "https://github.com/test/repo.git"

    # Mock database
    mock_db = MagicMock(spec=Session)
    mock_db.scalars.return_value.first.return_value = mock_repo

    # Mock scanner
    mock_scan_result = {"scan_id": 123, "status": "started"}

    with patch("app.api.v1.webhooks.get_db", return_value=mock_db), \
         patch("app.api.v1.webhooks.ScannerService") as mock_scanner_class:

        mock_scanner = mock_scanner_class.return_value
        mock_scanner.scan_repository = AsyncMock(return_value=mock_scan_result)

        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "clone_url": "https://github.com/test/repo.git",
                "full_name": "test/repo"
            }
        }

        response = client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["repository_id"] == 1
        assert data["scan_id"] == 123


def test_github_webhook_non_push_event(client):
    """Test GitHub webhook with non-push event."""
    payload = {
        "action": "opened",
        "repository": {
            "clone_url": "https://github.com/test/repo.git"
        }
    }

    response = client.post(
        "/api/v1/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"
    assert "push" in data["reason"].lower()


def test_github_webhook_repository_not_found(client):
    """Test GitHub webhook for repository not in database."""
    mock_db = MagicMock(spec=Session)
    mock_db.scalars.return_value.first.return_value = None

    with patch("app.api.v1.webhooks.get_db", return_value=mock_db):
        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "clone_url": "https://github.com/unknown/repo.git"
            }
        }

        response = client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push"}
        )

        assert response.status_code == 404


def test_github_webhook_disabled(client):
    """Test GitHub webhook when webhooks are disabled for repository."""
    mock_repo = MagicMock(spec=Repository)
    mock_repo.id = 1
    mock_repo.webhook_enabled = 0  # Disabled

    mock_db = MagicMock(spec=Session)
    mock_db.scalars.return_value.first.return_value = mock_repo

    with patch("app.api.v1.webhooks.get_db", return_value=mock_db):
        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "clone_url": "https://github.com/test/repo.git"
            }
        }

        response = client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert "disabled" in data["reason"].lower()
