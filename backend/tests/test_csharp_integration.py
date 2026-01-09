"""Integration tests for C# scanner with real repository."""
import tempfile
from pathlib import Path

import pytest
from git import Repo
from sqlalchemy.orm import Session

from app.models.repository import Repository, RepositoryType
from app.services.scanner_service import ScannerService


@pytest.fixture
def db_session():
    """Create test database session."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def csharp_test_repo():
    """Create a temporary C# repository with authorization code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test_csharp_repo"
        repo_path.mkdir()

        # Create a C# file with ASP.NET authorization
        controller_file = repo_path / "Controllers" / "UserController.cs"
        controller_file.parent.mkdir(parents=True)
        controller_file.write_text(
            """using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace MyApp.Controllers
{
    [Authorize]
    public class UserController : Controller
    {
        [Authorize(Roles = "Admin")]
        public IActionResult Delete(int id)
        {
            // Delete user logic
            return Ok();
        }

        [AllowAnonymous]
        public IActionResult Login()
        {
            return View();
        }

        public IActionResult UpdateProfile(User user)
        {
            if (User.IsInRole("Admin") || user.Id == GetCurrentUserId())
            {
                // Update logic
                return Ok();
            }
            return Forbid();
        }
    }
}"""
        )

        # Create another C# file with policy-based authorization
        service_file = repo_path / "Services" / "ExpenseService.cs"
        service_file.parent.mkdir(parents=True)
        service_file.write_text(
            """using System.Security.Claims;

namespace MyApp.Services
{
    public class ExpenseService
    {
        public bool CanApprove(ClaimsPrincipal user, Expense expense)
        {
            if (user.IsInRole("Manager") && expense.Amount < 5000)
            {
                return true;
            }

            if (user.IsInRole("Director"))
            {
                return true;
            }

            return false;
        }

        public bool HasPermission(ClaimsPrincipal user, string permission)
        {
            return user.HasClaim("Permission", permission);
        }
    }
}"""
        )

        # Initialize git repo
        git_repo = Repo.init(repo_path)
        git_repo.index.add(["*"])
        git_repo.index.commit("Initial commit with C# authorization code")

        yield str(repo_path)


def test_csharp_scanner_integration(db_session: Session, csharp_test_repo: str):
    """Test that C# scanner correctly processes a real repository."""
    # Create repository record
    repo = Repository(
        name="Test C# Repo",
        repository_type=RepositoryType.GIT,
        connection_config={"url": csharp_test_repo},
        tenant_id="test-tenant",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    # Create scanner and process repo
    scanner = ScannerService(db_session)

    # Find authorization files (should detect .cs files)
    auth_files = scanner._find_authorization_files(csharp_test_repo)

    # Should find our 2 C# files
    cs_files = [f for f in auth_files if f["file_path"].endswith(".cs")]
    assert len(cs_files) == 2

    # Check UserController.cs
    user_controller = next((f for f in cs_files if "UserController.cs" in f["file_path"]), None)
    assert user_controller is not None
    assert len(user_controller["matches"]) > 0

    # Should detect [Authorize] attributes
    patterns = [m["pattern"] for m in user_controller["matches"]]
    assert any("[Authorize" in p for p in patterns)


def test_csharp_scanner_extracts_details(db_session: Session, csharp_test_repo: str):
    """Test that C# scanner extracts detailed authorization info."""
    scanner = ScannerService(db_session)

    # Read the UserController.cs file
    controller_path = Path(csharp_test_repo) / "Controllers" / "UserController.cs"
    content = controller_path.read_text()

    # Use C# scanner directly
    csharp_details = scanner.csharp_scanner.extract_authorization_details(
        content, "UserController.cs"
    )

    # Should find multiple authorization patterns
    assert len(csharp_details) > 0

    # Should find [Authorize] attributes
    attributes = [d for d in csharp_details if d["type"] == "attribute"]
    assert len(attributes) >= 2  # [Authorize] and [Authorize(Roles = "Admin")]

    # Should find IsInRole method calls
    method_calls = [d for d in csharp_details if d["type"] == "method_call"]
    assert len(method_calls) >= 1


def test_csharp_scanner_line_numbers_accurate(db_session: Session, csharp_test_repo: str):
    """Test that C# scanner reports accurate line numbers."""
    scanner = ScannerService(db_session)

    controller_path = Path(csharp_test_repo) / "Controllers" / "UserController.cs"
    content = controller_path.read_text()

    csharp_details = scanner.csharp_scanner.extract_authorization_details(
        content, "UserController.cs"
    )

    # Check that line numbers are reasonable
    for detail in csharp_details:
        assert detail["line_start"] > 0
        assert detail["line_end"] >= detail["line_start"]
        assert detail["line_start"] <= len(content.split("\n"))


def test_csharp_scanner_prompt_enhancement(db_session: Session, csharp_test_repo: str):
    """Test that C# scanner enhances prompts with context."""
    scanner = ScannerService(db_session)

    controller_path = Path(csharp_test_repo) / "Controllers" / "UserController.cs"
    content = controller_path.read_text()

    csharp_details = scanner.csharp_scanner.extract_authorization_details(
        content, "UserController.cs"
    )

    # Build matches in the format expected by _build_extraction_prompt
    matches = [
        {
            "pattern": detail.get("pattern", ""),
            "line": detail.get("line_start", 0),
            "text": detail.get("text", ""),
            "csharp_detail": detail,
        }
        for detail in csharp_details
    ]

    # Build prompt
    prompt = scanner._build_extraction_prompt("UserController.cs", content, matches)

    # Should contain C#-specific context
    assert "C#/.NET Authorization Context" in prompt
    assert "ASP.NET Core Authorization Attributes" in prompt or "Authorization Method Calls" in prompt
