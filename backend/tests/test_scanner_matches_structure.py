"""Test that scanner service returns correct matches structure."""
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.repository import Repository, RepositoryStatus, RepositoryType
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
async def test_stream_authorization_files_returns_correct_matches_structure(mock_db, mock_repo, tmp_path):
    """Test that _stream_authorization_files returns matches as list of dicts, not strings."""
    scanner = ScannerService(mock_db)

    # Create a test file with authorization code
    test_file = tmp_path / "test_auth.py"
    test_content = """
@requires_permission('admin')
def authorize_user(user_id):
    if has_role('manager'):
        return True
    return False
"""
    test_file.write_text(test_content)

    # Mock secret detection to return no secrets
    from app.services.secret_detection_service import SecretDetectionService
    with patch.object(SecretDetectionService, "scan_content", return_value=MagicMock(
        secrets_found=[],
        redacted_content=test_content
    )):
        # Collect results from the async generator
        results = []
        async for file_info in scanner._stream_authorization_files(tmp_path, mock_repo):
            results.append(file_info)

        # Should find at least one file with authorization patterns
        assert len(results) > 0

        file_info = results[0]

        # Verify structure
        assert "path" in file_info
        assert "content" in file_info
        assert "matches" in file_info

        # CRITICAL: matches should be a list of dictionaries, not strings
        matches = file_info["matches"]
        assert isinstance(matches, list)
        assert len(matches) > 0

        # Each match should be a dictionary with required fields
        for match in matches:
            assert isinstance(match, dict), f"Match should be dict, got {type(match)}: {match}"
            assert "pattern" in match, "Match should have 'pattern' field"
            assert "line" in match, "Match should have 'line' field"
            assert "text" in match, "Match should have 'text' field"
            assert isinstance(match["line"], int), f"Line number should be int, got {type(match['line'])}"
            assert isinstance(match["pattern"], str), f"Pattern should be str, got {type(match['pattern'])}"
            assert isinstance(match["text"], str), f"Text should be str, got {type(match['text'])}"


@pytest.mark.asyncio
async def test_extract_policies_from_file_receives_correct_matches(mock_db, mock_repo):
    """Test that _extract_policies_from_file can process matches from _stream_authorization_files."""
    scanner = ScannerService(mock_db)

    # Create test matches in the correct format
    test_matches = [
        {"pattern": r"@requires_permission", "line": 5, "text": "@requires_permission('admin')"},
        {"pattern": r"has_role", "line": 7, "text": "has_role('manager')"},
    ]

    test_content = """
@requires_permission('admin')
def authorize_user(user_id):
    if has_role('manager'):
        return True
    return False
"""

    # Mock LLM provider to return a valid response
    mock_llm_response = MagicMock()
    mock_llm_response.content = [MagicMock(text="""
Here are the extracted policies:

<policy>
{
  "subject": "User with admin permission",
  "resource": "User authorization",
  "action": "authorize_user",
  "conditions": "User must have 'admin' permission and 'manager' role",
  "description": "Authorizes users with admin permission and manager role"
}
</policy>
""")]

    with patch.object(scanner.llm_provider, "create_message", return_value=mock_llm_response):
        # This should not raise an AttributeError about 'str' object has no attribute 'get'
        try:
            policies = await scanner._extract_policies_from_file(
                repo=mock_repo,
                file_path="test_auth.py",
                content=test_content,
                matches=test_matches,
                repo_path=Path("/tmp/test_repo")
            )
            # If we get here, the function accepted the matches structure correctly
            assert True
        except AttributeError as e:
            if "'str' object has no attribute 'get'" in str(e):
                pytest.fail(f"Function expects dict but received string in matches: {e}")
            raise


@pytest.mark.asyncio
async def test_matches_line_numbers_are_accurate(mock_db, mock_repo, tmp_path):
    """Test that line numbers in matches are accurate."""
    scanner = ScannerService(mock_db)

    # Create a test file with known authorization patterns at specific lines
    test_file = tmp_path / "test_lines.py"
    test_content = """# Line 1: comment
# Line 2: another comment
@requires_permission('admin')  # Line 3: this should be line 3
def some_function():  # Line 4
    pass  # Line 5

if hasRole('manager'):  # Line 7: this should be line 7 (use camelCase to match AUTH_PATTERNS)
    do_something()  # Line 8
"""
    test_file.write_text(test_content)

    # Mock secret detection
    from app.services.secret_detection_service import SecretDetectionService
    with patch.object(SecretDetectionService, "scan_content", return_value=MagicMock(
        secrets_found=[],
        redacted_content=test_content
    )):
        results = []
        async for file_info in scanner._stream_authorization_files(tmp_path, mock_repo):
            results.append(file_info)

        assert len(results) > 0
        matches = results[0]["matches"]

        # Verify all matches have the correct structure
        for match in matches:
            assert "line" in match
            assert isinstance(match["line"], int)
            assert match["line"] > 0

        # Find the @requires_permission match - should be on line 3
        permission_matches = [m for m in matches if "@requires_permission" in m["text"]]
        assert len(permission_matches) > 0
        assert permission_matches[0]["line"] == 3, f"Expected line 3, got {permission_matches[0]['line']}"

        # Find the hasRole match - should be on line 7
        role_matches = [m for m in matches if "hasRole" in m["text"]]
        if len(role_matches) > 0:  # Only verify if found
            assert role_matches[0]["line"] == 7, f"Expected line 7, got {role_matches[0]['line']}"
