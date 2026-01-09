"""Tests for streaming file processing performance."""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.repository import Repository, RepositoryStatus, RepositoryType
from app.services.scanner_service import ScannerService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.query = Mock()
    return db


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = Mock(spec=Repository)
    repo.id = 1
    repo.tenant_id = "test-tenant"
    repo.source_url = "https://github.com/test/repo.git"
    repo.repository_type = RepositoryType.GIT
    repo.status = RepositoryStatus.CONNECTED
    repo.connection_config = None
    repo.last_scan_at = None
    return repo


@pytest.fixture
def scanner_service(mock_db):
    """Create a scanner service instance."""
    with patch('app.services.scanner_service.get_llm_provider'):
        service = ScannerService(mock_db)
        return service


def test_memory_usage_tracking(scanner_service):
    """Test that memory usage is tracked correctly."""
    # Get initial memory
    initial_memory = scanner_service._get_memory_usage_mb()
    assert initial_memory > 0
    assert isinstance(initial_memory, float)

    # Get memory delta
    delta = scanner_service._get_memory_delta_mb()
    assert isinstance(delta, float)
    assert delta >= 0  # Delta should be non-negative at start


@pytest.mark.asyncio
async def test_count_authorization_files(scanner_service, tmp_path):
    """Test counting files without loading them into memory."""
    # Create test files
    (tmp_path / "test1.py").write_text("def has_role(): pass")
    (tmp_path / "test2.java").write_text("@PreAuthorize class Foo {}")
    (tmp_path / "test3.txt").write_text("not a code file")  # Should be skipped
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("git config")  # Should be skipped

    # Count files
    count = await scanner_service._count_authorization_files(tmp_path)

    # Should count only .py and .java files
    assert count == 2


@pytest.mark.asyncio
async def test_stream_authorization_files_yields_files(scanner_service, tmp_path, mock_repository):
    """Test that streaming yields files one at a time."""
    # Create test files with authorization patterns that match AUTH_PATTERNS
    (tmp_path / "test1.py").write_text("def hasRole(x): return True\nif user.hasRole('admin'): pass")
    (tmp_path / "test2.java").write_text("@PreAuthorize('hasRole') class Foo {}")
    (tmp_path / "test3.py").write_text("just a comment")  # No auth pattern

    files = []
    async for file_info in scanner_service._stream_authorization_files(tmp_path, mock_repository):
        files.append(file_info)

    # Should yield 2 files (test3.py has no auth patterns)
    assert len(files) == 2
    assert all(isinstance(f, dict) for f in files)
    assert all("path" in f and "content" in f and "matches" in f for f in files)


@pytest.mark.asyncio
async def test_stream_skips_non_code_files(scanner_service, tmp_path, mock_repository):
    """Test that non-code files (wrong extensions) are skipped."""
    # Create files with various extensions
    (tmp_path / "test.txt").write_text("def hasRole(): pass")  # Not a supported extension
    (tmp_path / "test.md").write_text("def hasRole(): pass")  # Not a supported extension
    (tmp_path / "test.py").write_text("def hasRole(): pass\nif user.hasRole('admin'): pass")  # Valid

    files = []
    async for file_info in scanner_service._stream_authorization_files(tmp_path, mock_repository):
        files.append(file_info)

    # Should only find the .py file
    assert len(files) == 1
    assert "test.py" in files[0]["path"]


@pytest.mark.asyncio
async def test_streaming_scan_processes_batches(scanner_service, mock_db, mock_repository, tmp_path):
    """Test that streaming scan processes files in batches."""
    # Setup mocks
    mock_db.query.return_value.filter.return_value.first.return_value = mock_repository

    # Create mock scan progress
    mock_scan_progress = Mock()
    mock_scan_progress.id = 1
    mock_db.add.return_value = None
    mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1)

    # Mock _clone_repository
    with patch.object(scanner_service, '_clone_repository', return_value=tmp_path):
        # Create test files
        for i in range(5):
            (tmp_path / f"test{i}.py").write_text(f"@login_required\ndef view{i}(): pass")

        # Mock _extract_policies_from_file
        with patch.object(scanner_service, '_extract_policies_from_file', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = []  # Return empty list of policies

            # Run scan
            result = await scanner_service.scan_repository(1, "test-tenant")

            # Verify result includes performance metrics
            assert "performance" in result
            assert "duration_seconds" in result["performance"]
            assert "start_memory_mb" in result["performance"]
            assert "peak_memory_mb" in result["performance"]
            assert "end_memory_mb" in result["performance"]
            assert "memory_delta_mb" in result["performance"]
            assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_memory_stays_within_threshold(scanner_service, mock_db, mock_repository, tmp_path):
    """Test that memory usage stays within reasonable limits during streaming."""
    # Setup mocks
    mock_db.query.return_value.filter.return_value.first.return_value = mock_repository

    # Mock _clone_repository
    with patch.object(scanner_service, '_clone_repository', return_value=tmp_path):
        # Create many test files to simulate large repository
        for i in range(100):
            (tmp_path / f"test{i}.py").write_text(f"@login_required\ndef view{i}(): pass")

        # Mock _extract_policies_from_file
        with patch.object(scanner_service, '_extract_policies_from_file', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = []

            # Track memory during scan
            initial_memory = scanner_service._get_memory_usage_mb()

            result = await scanner_service.scan_repository(1, "test-tenant")

            peak_memory = result["performance"]["peak_memory_mb"]
            memory_increase = peak_memory - initial_memory

            # Memory increase should be reasonable (< 500MB for streaming)
            # This is a soft check - actual threshold depends on environment
            assert memory_increase < 500, f"Memory increased by {memory_increase}MB, expected < 500MB"
            assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_batch_processing_clears_memory(scanner_service, tmp_path, mock_repository):
    """Test that batches are cleared to free memory."""
    # Create test files with valid authorization patterns
    for i in range(60):  # More than BATCH_SIZE (50)
        (tmp_path / f"test{i}.py").write_text(f"def hasRole(): pass\nif user.hasRole('admin'): view{i}()")

    files_yielded = 0
    async for file_info in scanner_service._stream_authorization_files(tmp_path, mock_repository):
        files_yielded += 1

    # Should yield all 60 files
    assert files_yielded == 60
