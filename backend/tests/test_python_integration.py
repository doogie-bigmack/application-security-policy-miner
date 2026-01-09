"""Integration tests for Python scanner with real repository."""
import tempfile
from pathlib import Path

import pytest
from git import Repo
from sqlalchemy.orm import Session

from app.models.repository import Repository, RepositoryType
from app.services.scanner_service import ScannerService


@pytest.fixture
def sample_python_repo():
    """Create a temporary git repository with Python authorization code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create a Flask app with authorization
        flask_app = repo_path / "app.py"
        flask_app.write_text("""
from flask import Flask, render_template
from flask_login import login_required
from flask_security import roles_required, permissions_required

app = Flask(__name__)

@app.route('/admin')
@login_required
@roles_required('admin')
def admin_panel():
    '''Admin panel - only admins can access.'''
    return render_template('admin.html')

@app.route('/reports')
@login_required
@permissions_required('view_reports')
def view_reports():
    '''View reports - requires view_reports permission.'''
    return render_template('reports.html')

@app.route('/approve/<int:expense_id>')
@login_required
def approve_expense(expense_id):
    '''Approve expense - managers only, amount < $5000.'''
    from models import Expense
    expense = Expense.query.get(expense_id)

    if current_user.has_role('manager') and expense.amount < 5000:
        expense.approved = True
        db.session.commit()
        return {'status': 'approved'}

    return {'status': 'denied'}, 403
""")

        # Create a Django views file
        django_views = repo_path / "views.py"
        django_views.write_text("""
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

@login_required
@permission_required('app.view_dashboard')
def dashboard(request):
    '''Dashboard view - requires authentication and permission.'''
    return render(request, 'dashboard.html')

@login_required
def process_payment(request, payment_id):
    '''Process payment - requires manager role.'''
    from .models import Payment
    payment = Payment.objects.get(id=payment_id)

    if request.user.has_permission('process_payment'):
        if request.user.role == 'manager' or request.user.is_superuser:
            payment.status = 'processed'
            payment.save()
            return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'denied'}, status=403)
""")

        # Create a FastAPI app
        fastapi_main = repo_path / "main.py"
        fastapi_main.write_text("""
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer, OAuth2PasswordBearer

app = FastAPI()
security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    '''Get current authenticated user from token.'''
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

async def require_admin(user = Security(get_current_user)):
    '''Require admin role for endpoint access.'''
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin required")
    return user

@app.get("/admin/users")
async def list_users(admin = Depends(require_admin)):
    '''List all users - admin only.'''
    return {"users": get_all_users()}

@app.post("/expenses/{expense_id}/approve")
async def approve_expense(expense_id: int, user = Depends(get_current_user)):
    '''Approve expense - manager only, amount < $10000.'''
    expense = get_expense(expense_id)

    if user.has_permission('approve_expense'):
        if user.role == 'manager' and expense.amount < 10000:
            expense.status = 'approved'
            return {"status": "approved"}

    raise HTTPException(status_code=403, detail="Not authorized")
""")

        # Initialize git repository
        git_repo = Repo.init(repo_path)
        git_repo.index.add(["app.py", "views.py", "main.py"])
        git_repo.index.commit("Initial commit with Python authorization code")

        yield str(repo_path)


@pytest.mark.asyncio
async def test_scan_python_flask_repository(sample_python_repo, db: Session):
    """Test scanning a Python Flask repository."""
    # Create repository record
    repo = Repository(
        name="Test Python Flask App",
        type=RepositoryType.GIT,
        connection_config={"url": sample_python_repo},
        tenant_id="test-tenant",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Scan repository
    scanner = ScannerService(db)
    result = await scanner.scan_repository(repo.id, tenant_id="test-tenant")

    # Verify scan results
    assert result["status"] == "completed"
    assert result["policies_created"] > 0

    # Check that Flask decorators were detected
    policies = db.query(scanner.db.query(Policy).filter(Policy.repository_id == repo.id).all())

    # Should find policies with Flask patterns
    flask_policies = [p for p in policies if 'flask' in p.description.lower() or 'login_required' in p.description.lower()]
    assert len(flask_policies) > 0


@pytest.mark.asyncio
async def test_scan_python_django_repository(sample_python_repo, db: Session):
    """Test scanning a Python Django repository."""
    # Create repository record
    repo = Repository(
        name="Test Python Django App",
        type=RepositoryType.GIT,
        connection_config={"url": sample_python_repo},
        tenant_id="test-tenant",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Scan repository
    scanner = ScannerService(db)
    result = await scanner.scan_repository(repo.id, tenant_id="test-tenant")

    # Verify scan results
    assert result["status"] == "completed"
    assert result["policies_created"] > 0


@pytest.mark.asyncio
async def test_scan_python_fastapi_repository(sample_python_repo, db: Session):
    """Test scanning a Python FastAPI repository."""
    # Create repository record
    repo = Repository(
        name="Test Python FastAPI App",
        type=RepositoryType.GIT,
        connection_config={"url": sample_python_repo},
        tenant_id="test-tenant",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Scan repository
    scanner = ScannerService(db)
    result = await scanner.scan_repository(repo.id, tenant_id="test-tenant")

    # Verify scan results
    assert result["status"] == "completed"
    assert result["policies_created"] > 0


@pytest.mark.asyncio
async def test_python_tree_sitter_detection(sample_python_repo, db: Session):
    """Test that tree-sitter correctly detects Python authorization patterns."""
    from app.services.python_scanner_service import PythonScannerService

    scanner = PythonScannerService()

    # Read Flask app file
    flask_code = (Path(sample_python_repo) / "app.py").read_text()

    # Should detect authorization code
    assert scanner.has_authorization_code(flask_code)

    # Extract details
    details = scanner.extract_authorization_details(flask_code, "app.py")

    # Should find Flask decorators
    assert len(details) > 0

    decorator_patterns = [d["pattern"] for d in details if d["type"] == "decorator"]
    assert "@login_required" in decorator_patterns
    assert "@roles_required" in decorator_patterns
