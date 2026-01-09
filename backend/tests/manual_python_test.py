"""Manual test script to verify Python scanner works correctly."""
from app.services.python_scanner_service import PythonScannerService


def test_python_scanner_manual():
    """Manual test of Python scanner functionality."""
    scanner = PythonScannerService()

    # Sample Flask code with authorization
    flask_code = """
from flask import Flask, render_template
from flask_login import login_required
from flask_security import roles_required

app = Flask(__name__)

@app.route('/admin')
@login_required
@roles_required('admin')
def admin_panel():
    '''Only admins can access this panel.'''
    return render_template('admin.html')

@app.route('/approve/<int:expense_id>')
@login_required
def approve_expense(expense_id):
    '''Managers can approve expenses under $5000.'''
    from models import Expense
    expense = Expense.query.get(expense_id)

    if current_user.has_role('manager') and expense.amount < 5000:
        expense.approved = True
        db.session.commit()
        return {'status': 'approved'}

    return {'status': 'denied'}, 403
"""

    print("Testing Python Scanner Service...")
    print("=" * 80)

    # Test 1: Detection
    print("\n1. Testing authorization code detection...")
    has_auth = scanner.has_authorization_code(flask_code)
    print(f"   ✓ Has authorization code: {has_auth}")
    assert has_auth, "Failed to detect authorization code!"

    # Test 2: Extraction
    print("\n2. Testing authorization details extraction...")
    details = scanner.extract_authorization_details(flask_code, "app.py")
    print(f"   ✓ Found {len(details)} authorization details")

    for detail in details:
        print(f"     - {detail['type']}: {detail['pattern']} at line {detail['line_start']}")

    assert len(details) > 0, "Failed to extract authorization details!"

    # Test 3: Decorator detection
    print("\n3. Testing Flask decorator detection...")
    decorators = [d for d in details if d["type"] == "decorator"]
    print(f"   ✓ Found {len(decorators)} decorators")

    decorator_patterns = [d["pattern"] for d in decorators]
    assert "@login_required" in decorator_patterns, "Missing @login_required"
    assert "@roles_required" in decorator_patterns, "Missing @roles_required"
    print("   ✓ All expected decorators found")

    # Test 4: Method call detection
    print("\n4. Testing method call detection...")
    method_calls = [d for d in details if d["type"] == "method_call"]
    print(f"   ✓ Found {len(method_calls)} method calls")

    method_patterns = [d["pattern"] for d in method_calls]
    if "has_role" in method_patterns:
        print("   ✓ Detected has_role() method call")

    # Test 5: Prompt enhancement
    print("\n5. Testing prompt enhancement...")
    base_prompt = "Extract policies. Return your response as a JSON array"
    enhanced = scanner.enhance_prompt_with_python_context(base_prompt, details)

    assert "Flask Decorators:" in enhanced, "Missing Flask context in prompt"
    assert "@login_required" in enhanced, "Missing decorator in enhanced prompt"
    print("   ✓ Prompt enhanced with Python-specific context")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("Python scanner is working correctly!")
    print("=" * 80)


if __name__ == "__main__":
    test_python_scanner_manual()
