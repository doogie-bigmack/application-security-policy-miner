"""Integration tests for database stored procedure scanning."""
import pytest
from unittest.mock import patch, Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.scanner_service import ScannerService
from app.models.repository import Repository, RepositoryType, RepositoryStatus
from app.models.scan_progress import ScanProgress, ScanStatus


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_database_repository():
    """Create a mock database repository."""
    repo = Mock(spec=Repository)
    repo.id = 1
    repo.name = "Test PostgreSQL"
    repo.repository_type = RepositoryType.DATABASE
    repo.connection_config = {
        "database_type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "testdb",
        "username": "testuser",
        "password": "testpass",
    }
    repo.status = RepositoryStatus.CONNECTED
    return repo


@pytest.mark.asyncio
async def test_scan_database_repository_integration(mock_db_session, mock_database_repository):
    """Test end-to-end database scanning."""
    # Setup mocks
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_database_repository
    mock_scan_progress = Mock(spec=ScanProgress)
    mock_scan_progress.id = 1
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    mock_db_session.query.return_value.filter.return_value.count.return_value = 0

    # Mock database scanner
    mock_scan_result = {
        "procedures_scanned": 5,
        "total_procedures": 10,
        "policies_extracted": 3,
        "policies": [],
    }

    scanner = ScannerService(mock_db_session)

    with patch.object(scanner.database_scanner, "scan_database", return_value=mock_scan_result):
        result = await scanner.scan_repository(
            repository_id=1,
            tenant_id="test-tenant",
            incremental=False,
        )

    # Verify result
    assert result["scan_type"] == "database"
    assert result["procedures_scanned"] == 5
    assert result["total_procedures"] == 10
    assert result["policies_extracted"] == 3
    assert result["errors"] == 0


@pytest.mark.asyncio
async def test_git_repository_still_works(mock_db_session):
    """Test that git repositories still work after database integration."""
    # Create a mock git repository
    git_repo = Mock(spec=Repository)
    git_repo.id = 2
    git_repo.name = "Test Git Repo"
    git_repo.repository_type = RepositoryType.GIT
    git_repo.source_url = "https://github.com/test/repo.git"
    git_repo.status = RepositoryStatus.CONNECTED

    mock_db_session.query.return_value.filter.return_value.first.return_value = git_repo
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    mock_db_session.query.return_value.filter.return_value.count.return_value = 0

    scanner = ScannerService(mock_db_session)

    # Mock git operations
    with patch.object(scanner, "_clone_repository", return_value="/tmp/test-repo"):
        with patch("app.services.scanner_service.Repo"):
            with patch.object(scanner, "_get_last_scan_commit", return_value=None):
                with patch.object(scanner, "_count_authorization_files", return_value=10):
                    with patch.object(scanner, "_stream_authorization_files", return_value=[]):
                        # This should not raise an error and should use the git scanning path
                        result = await scanner.scan_repository(
                            repository_id=2,
                            tenant_id="test-tenant",
                            incremental=False,
                        )

                        # Verify it's a git scan (not database scan)
                        assert "scan_type" in result
                        # Git scans don't have procedures_scanned field
                        assert "procedures_scanned" not in result
