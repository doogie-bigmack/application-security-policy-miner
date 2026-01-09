"""Tests for Python scanner service."""

from app.services.python_scanner_service import PythonScannerService


class TestPythonScannerService:
    """Test cases for PythonScannerService."""

    def test_detect_flask_decorators(self):
        """Test detection of Flask decorators."""
        scanner = PythonScannerService()

        code = """
@app.route('/admin')
@login_required
@roles_required('admin')
def admin_panel():
    return render_template('admin.html')
"""

        assert scanner.has_authorization_code(code)
        details = scanner.extract_authorization_details(code, "views.py")

        assert len(details) > 0
        decorator_patterns = [d["pattern"] for d in details if d["type"] == "decorator"]
        assert "@login_required" in decorator_patterns
        assert "@roles_required" in decorator_patterns

    def test_detect_django_decorators(self):
        """Test detection of Django decorators."""
        scanner = PythonScannerService()

        code = """
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('app.view_dashboard')
def dashboard(request):
    return render(request, 'dashboard.html')
"""

        assert scanner.has_authorization_code(code)
        details = scanner.extract_authorization_details(code, "views.py")

        assert len(details) > 0
        decorator_patterns = [d["pattern"] for d in details if d["type"] == "decorator"]
        assert "@login_required" in decorator_patterns
        assert "@permission_required" in decorator_patterns

    def test_detect_fastapi_dependencies(self):
        """Test detection of FastAPI dependencies."""
        scanner = PythonScannerService()

        code = """
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, OAuth2PasswordBearer

security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/users")
def get_users(token: str = Security(oauth2_scheme)):
    return {"users": []}
"""

        # The code contains FastAPI patterns (Depends, Security, HTTPBearer, OAuth2PasswordBearer)
        assert scanner.has_authorization_code(code)

    def test_detect_method_calls(self):
        """Test detection of authorization method calls."""
        scanner = PythonScannerService()

        code = """
def approve_expense(user, expense):
    if user.has_permission('approve_expense'):
        if user.check_role('manager'):
            return True
    return False
"""

        assert scanner.has_authorization_code(code)
        details = scanner.extract_authorization_details(code, "permissions.py")

        assert len(details) > 0
        method_patterns = [d["pattern"] for d in details if d["type"] == "method_call"]
        assert "has_permission" in method_patterns
        assert "check_role" in method_patterns

    def test_detect_conditionals(self):
        """Test detection of authorization conditionals."""
        scanner = PythonScannerService()

        code = """
def process_request(request):
    if request.user.role == 'admin':
        return process_admin_request(request)
    elif request.user.has_permission('view'):
        return process_user_request(request)
    else:
        raise PermissionDenied()
"""

        assert scanner.has_authorization_code(code)
        details = scanner.extract_authorization_details(code, "views.py")

        assert len(details) > 0
        conditionals = [d for d in details if d["type"] == "conditional"]
        assert len(conditionals) > 0

    def test_line_numbers_accurate(self):
        """Test that line numbers are accurate."""
        scanner = PythonScannerService()

        code = """# Line 1
# Line 2
@login_required  # Line 3
def view():  # Line 4
    pass  # Line 5
"""

        details = scanner.extract_authorization_details(code, "views.py")

        assert len(details) > 0
        decorator = details[0]
        assert decorator["line_start"] == 3
        assert decorator["type"] == "decorator"

    def test_no_authorization_code(self):
        """Test file with no authorization code."""
        scanner = PythonScannerService()

        code = """
def add_numbers(a, b):
    return a + b

class Calculator:
    def multiply(self, a, b):
        return a * b
"""

        assert not scanner.has_authorization_code(code)
        details = scanner.extract_authorization_details(code, "utils.py")
        assert len(details) == 0

    def test_enhance_prompt_with_flask_context(self):
        """Test prompt enhancement with Flask context."""
        scanner = PythonScannerService()

        code = """
@login_required
@roles_required('admin')
def admin_view():
    pass
"""

        details = scanner.extract_authorization_details(code, "views.py")
        base_prompt = "Extract policies. Return your response as a JSON array"

        enhanced = scanner.enhance_prompt_with_python_context(base_prompt, details)

        assert "Flask Decorators:" in enhanced
        assert "@login_required" in enhanced
        assert "@roles_required" in enhanced
        assert "Return your response as a JSON array" in enhanced

    def test_enhance_prompt_with_django_context(self):
        """Test prompt enhancement with Django context."""
        scanner = PythonScannerService()

        code = """
@login_required
@permission_required('app.view_data')
def protected_view(request):
    pass
"""

        details = scanner.extract_authorization_details(code, "views.py")
        base_prompt = "Extract policies. Return your response as a JSON array"

        enhanced = scanner.enhance_prompt_with_python_context(base_prompt, details)

        assert "Django Decorators:" in enhanced
        assert "@login_required" in enhanced
        assert "@permission_required" in enhanced

    def test_context_includes_surrounding_code(self):
        """Test that context includes surrounding code."""
        scanner = PythonScannerService()

        code = """
class UserView:
    @login_required
    def get(self, request):
        return Response({'data': 'protected'})
"""

        details = scanner.extract_authorization_details(code, "views.py")

        assert len(details) > 0
        decorator = details[0]
        assert "context" in decorator
        assert len(decorator["context"]) > 0
        # Context should include function definition
        assert "def get" in decorator["context"]
