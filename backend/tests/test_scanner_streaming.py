"""Tests for streaming batch processing in scanner service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.repository import Repository, RepositoryStatus, RepositoryType
from app.models.scan_progress import ScanProgress, ScanStatus
from app.services.scanner_service import ScannerService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_repo():
    """Create a mock repository."""
    repo = Repository(
        id=1,
        name="Test Repo",
        repository_type=RepositoryType.GIT,
        source_url="https://github.com/test/repo.git",
        status=RepositoryStatus.CONNECTED,
        tenant_id="test-tenant",
    )
    return repo


@pytest.mark.asyncio
async def test_batch_processing_processes_all_files(mock_db, mock_repo):
    """Test that batch processing handles all files, not just first batch."""
    scanner = ScannerService(mock_db)

    # Mock database queries
    mock_db.query.return_value.filter.return_value.first.return_value = mock_repo

    # Create 150 mock files (should create 3 batches of 50)
    mock_auth_files = [
        {
            "path": f"file{i}.py",
            "content": "def authorize(): pass",
            "matches": [{"pattern": "authorize", "line": 1, "text": "authorize"}],
        }
        for i in range(150)
    ]

    # Mock scanner methods
    with patch.object(scanner, "_clone_repository", new_callable=AsyncMock) as mock_clone, \
         patch.object(scanner, "_find_authorization_files", new_callable=AsyncMock) as mock_find, \
         patch.object(scanner, "_extract_policies_from_file", new_callable=AsyncMock) as mock_extract:

        mock_clone.return_value = "/tmp/test_repo"
        mock_find.return_value = mock_auth_files
        mock_extract.return_value = [MagicMock()]  # One policy per file

        result = await scanner.scan_repository(1, "test-tenant")

        # Verify all files were processed
        assert result["files_scanned"] == 150
        assert result["batches_processed"] == 3
        assert mock_extract.call_count == 150  # Should call extract for all 150 files

        # Verify scan progress was created and updated
        add_calls = [call for call in mock_db.add.call_args_list]
        assert len(add_calls) > 0  # ScanProgress was added
        assert mock_db.commit.call_count > 0


@pytest.mark.asyncio
async def test_batch_processing_updates_progress(mock_db, mock_repo):
    """Test that batch processing updates progress in real-time."""
    scanner = ScannerService(mock_db)

    # Mock database queries
    mock_db.query.return_value.filter.return_value.first.return_value = mock_repo

    # Create 100 mock files (should create 2 batches of 50)
    mock_auth_files = [
        {
            "path": f"file{i}.py",
            "content": "def authorize(): pass",
            "matches": [{"pattern": "authorize", "line": 1, "text": "authorize"}],
        }
        for i in range(100)
    ]

    # Track scan progress updates
    scan_progress = None

    def add_side_effect(obj):
        nonlocal scan_progress
        if isinstance(obj, ScanProgress):
            scan_progress = obj

    mock_db.add.side_effect = add_side_effect

    # Mock scanner methods
    with patch.object(scanner, "_clone_repository", new_callable=AsyncMock) as mock_clone, \
         patch.object(scanner, "_find_authorization_files", new_callable=AsyncMock) as mock_find, \
         patch.object(scanner, "_extract_policies_from_file", new_callable=AsyncMock) as mock_extract:

        mock_clone.return_value = "/tmp/test_repo"
        mock_find.return_value = mock_auth_files
        mock_extract.return_value = [MagicMock()]

        result = await scanner.scan_repository(1, "test-tenant")

        # Verify scan progress was created
        assert scan_progress is not None
        assert scan_progress.total_files == 100
        assert scan_progress.total_batches == 2

        # Verify progress updates happened (commit called multiple times during scanning)
        assert mock_db.commit.call_count > 2  # Initial setup, batch updates, final commit


@pytest.mark.asyncio
async def test_batch_processing_handles_errors_gracefully(mock_db, mock_repo):
    """Test that batch processing continues after errors in individual files."""
    scanner = ScannerService(mock_db)

    # Mock database queries
    mock_db.query.return_value.filter.return_value.first.return_value = mock_repo

    # Create 10 mock files
    mock_auth_files = [
        {
            "path": f"file{i}.py",
            "content": "def authorize(): pass",
            "matches": [{"pattern": "authorize", "line": 1, "text": "authorize"}],
        }
        for i in range(10)
    ]

    # Mock scanner methods
    with patch.object(scanner, "_clone_repository", new_callable=AsyncMock) as mock_clone, \
         patch.object(scanner, "_find_authorization_files", new_callable=AsyncMock) as mock_find, \
         patch.object(scanner, "_extract_policies_from_file", new_callable=AsyncMock) as mock_extract:

        mock_clone.return_value = "/tmp/test_repo"
        mock_find.return_value = mock_auth_files

        # Make every 3rd file fail
        call_count = [0]

        async def extract_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 0:
                raise Exception("Extraction failed")
            return [MagicMock()]

        mock_extract.side_effect = extract_side_effect

        result = await scanner.scan_repository(1, "test-tenant")

        # Verify scan completed despite errors
        assert result["status"] == "completed"
        assert result["files_scanned"] == 10
        assert result["errors_count"] == 3  # Files 3, 6, 9 failed
        assert result["policies_extracted"] == 7  # 10 - 3 errors


@pytest.mark.asyncio
async def test_scan_progress_status_transitions(mock_db, mock_repo):
    """Test that scan progress status transitions correctly."""
    scanner = ScannerService(mock_db)

    # Mock database queries
    mock_db.query.return_value.filter.return_value.first.return_value = mock_repo

    mock_auth_files = [
        {
            "path": "file1.py",
            "content": "def authorize(): pass",
            "matches": [{"pattern": "authorize", "line": 1, "text": "authorize"}],
        }
    ]

    # Track scan progress object
    scan_progress = None

    def add_side_effect(obj):
        nonlocal scan_progress
        if isinstance(obj, ScanProgress):
            scan_progress = obj

    mock_db.add.side_effect = add_side_effect

    # Mock scanner methods
    with patch.object(scanner, "_clone_repository", new_callable=AsyncMock) as mock_clone, \
         patch.object(scanner, "_find_authorization_files", new_callable=AsyncMock) as mock_find, \
         patch.object(scanner, "_extract_policies_from_file", new_callable=AsyncMock) as mock_extract:

        mock_clone.return_value = "/tmp/test_repo"
        mock_find.return_value = mock_auth_files
        mock_extract.return_value = [MagicMock()]

        await scanner.scan_repository(1, "test-tenant")

        # Verify status transitions: QUEUED -> PROCESSING -> COMPLETED
        assert scan_progress is not None
        assert scan_progress.status == ScanStatus.COMPLETED
        assert scan_progress.completed_at is not None
