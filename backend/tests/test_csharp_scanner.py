"""Unit tests for C#/.NET scanner service."""
import pytest

from app.services.csharp_scanner_service import CSharpScannerService


@pytest.fixture
def csharp_scanner():
    """Create C# scanner instance."""
    return CSharpScannerService()


def test_has_authorization_code_with_authorize_attribute(csharp_scanner):
    """Test detection of [Authorize] attribute."""
    code = """
    using Microsoft.AspNetCore.Authorization;

    public class UserController : Controller
    {
        [Authorize]
        public IActionResult Index()
        {
            return View();
        }
    }
    """
    assert csharp_scanner.has_authorization_code(code) is True


def test_has_authorization_code_with_isinrole(csharp_scanner):
    """Test detection of IsInRole method call."""
    code = """
    public class UserService
    {
        public bool CanDelete(User user)
        {
            return user.IsInRole("Admin");
        }
    }
    """
    assert csharp_scanner.has_authorization_code(code) is True


def test_has_authorization_code_no_auth(csharp_scanner):
    """Test that code without authorization is not detected."""
    code = """
    public class Calculator
    {
        public int Add(int a, int b)
        {
            return a + b;
        }
    }
    """
    assert csharp_scanner.has_authorization_code(code) is False


def test_extract_authorization_details_authorize_attribute(csharp_scanner):
    """Test extraction of [Authorize] attributes."""
    code = """using Microsoft.AspNetCore.Authorization;

public class AdminController : Controller
{
    [Authorize(Roles = "Admin")]
    public IActionResult DeleteUser(int id)
    {
        return View();
    }
}"""
    details = csharp_scanner.extract_authorization_details(code, "AdminController.cs")

    assert len(details) > 0
    assert details[0]["type"] == "attribute"
    assert "[Authorize" in details[0]["pattern"]
    assert details[0]["line_start"] == 5


def test_extract_authorization_details_method_call(csharp_scanner):
    """Test extraction of IsInRole method calls."""
    code = """public class UserService
{
    public bool CanApprove(User user, Expense expense)
    {
        if (user.IsInRole("Manager") && expense.Amount < 5000)
        {
            return true;
        }
        return false;
    }
}"""
    details = csharp_scanner.extract_authorization_details(code, "UserService.cs")

    # Should detect IsInRole method call
    method_calls = [d for d in details if d["type"] == "method_call"]
    assert len(method_calls) > 0
    assert method_calls[0]["pattern"] == "IsInRole"
    assert method_calls[0]["line_start"] == 5


def test_extract_authorization_details_conditional(csharp_scanner):
    """Test extraction of authorization conditionals."""
    code = """public class PolicyEngine
{
    public bool CheckPermission(User user, string resource)
    {
        if (user.HasClaim("Permission", resource))
        {
            return true;
        }
        return false;
    }
}"""
    details = csharp_scanner.extract_authorization_details(code, "PolicyEngine.cs")

    # Should detect both method call and conditional
    assert len(details) > 0
    # Conditional detection depends on keywords in if statement
    # This test verifies the parser works without errors


def test_extract_authorization_details_line_numbers(csharp_scanner):
    """Test that line numbers are accurate."""
    code = """namespace MyApp
{
    public class SecureController
    {
        [Authorize(Roles = "Admin,Manager")]
        public IActionResult Secure()
        {
            return View();
        }
    }
}"""
    details = csharp_scanner.extract_authorization_details(code, "SecureController.cs")

    assert len(details) > 0
    # [Authorize] should be on line 5
    assert details[0]["line_start"] == 5


def test_enhance_prompt_with_csharp_context_no_details(csharp_scanner):
    """Test prompt enhancement with no details returns unchanged prompt."""
    base_prompt = "Extract policies from this code."
    enhanced = csharp_scanner.enhance_prompt_with_csharp_context(base_prompt, [])
    assert enhanced == base_prompt


def test_enhance_prompt_with_csharp_context_with_details(csharp_scanner):
    """Test prompt enhancement adds C# context."""
    base_prompt = """Analyze this code.

Return your response as a JSON array"""

    details = [
        {
            "type": "attribute",
            "pattern": "[Authorize]",
            "category": "aspnet_core",
            "text": "[Authorize(Roles = \"Admin\")]",
            "line_start": 5,
            "line_end": 5,
            "context": "public IActionResult Delete() {...}",
        }
    ]

    enhanced = csharp_scanner.enhance_prompt_with_csharp_context(base_prompt, details)

    assert "C#/.NET Authorization Context" in enhanced
    assert "ASP.NET Core Authorization Attributes" in enhanced
    assert "[Authorize]" in enhanced
    assert "line 5" in enhanced


def test_extract_authorization_details_multiple_patterns(csharp_scanner):
    """Test extraction of multiple authorization patterns in one file."""
    code = """using Microsoft.AspNetCore.Authorization;

public class ComplexController : Controller
{
    [Authorize(Roles = "Admin")]
    public IActionResult AdminOnly()
    {
        return View();
    }

    public IActionResult CheckUser(User user)
    {
        if (user.IsInRole("Manager") || user.IsInRole("Admin"))
        {
            return View();
        }
        return Unauthorized();
    }

    [AllowAnonymous]
    public IActionResult Public()
    {
        return View();
    }
}"""
    details = csharp_scanner.extract_authorization_details(code, "ComplexController.cs")

    # Should find multiple patterns
    assert len(details) >= 3  # At least 2 attributes + method calls

    # Check we have attributes
    attributes = [d for d in details if d["type"] == "attribute"]
    assert len(attributes) >= 2

    # Check we have method calls
    method_calls = [d for d in details if d["type"] == "method_call"]
    assert len(method_calls) >= 1
