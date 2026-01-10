"""
Reference Application with Known Authorization Policies

This file contains a reference application with explicitly documented authorization
policies. It will be used to test the accuracy of the Policy Miner's extraction.

KNOWN POLICIES (Ground Truth):
===============================

Policy 1: View Expenses
- WHO: Authenticated users (any role)
- WHAT: Expense list (read)
- HOW: View/Read
- WHEN: User is authenticated

Policy 2: Create Expense
- WHO: Users with EMPLOYEE role
- WHAT: Expense (create)
- HOW: Create/Write
- WHEN: User has EMPLOYEE role

Policy 3: Update Own Expense
- WHO: Expense owner
- WHAT: Own expense (update)
- HOW: Update/Write
- WHEN: User is the expense owner AND expense is not approved

Policy 4: Approve Small Expense
- WHO: Users with MANAGER role
- WHAT: Expense approval (update)
- HOW: Approve
- WHEN: User has MANAGER role AND expense amount < $5,000

Policy 5: Approve Large Expense
- WHO: Users with DIRECTOR role
- WHAT: Expense approval (update)
- HOW: Approve
- WHEN: User has DIRECTOR role AND expense amount >= $5,000

Policy 6: Reject Expense
- WHO: Users with MANAGER or DIRECTOR role
- WHAT: Expense rejection (update)
- HOW: Reject
- WHEN: User has MANAGER or DIRECTOR role

Policy 7: Delete Own Expense
- WHO: Expense owner
- WHAT: Own expense (delete)
- HOW: Delete
- WHEN: User is the expense owner AND expense is not approved

Policy 8: Delete Any Expense
- WHO: Users with ADMIN role
- WHAT: Any expense (delete)
- HOW: Delete
- WHEN: User has ADMIN role

Policy 9: View Financial Reports
- WHO: Users in Finance department
- WHAT: Financial reports (read)
- HOW: View/Read
- WHEN: User department is "Finance"

Policy 10: Export Expense Data
- WHO: Users with MANAGER, DIRECTOR, or ADMIN role
- WHAT: Expense data export (read)
- HOW: Export/Download
- WHEN: User has MANAGER, DIRECTOR, or ADMIN role

Policy 11: View Audit Log
- WHO: Users with ADMIN role
- WHAT: Audit log (read)
- HOW: View/Read
- WHEN: User has ADMIN role

Policy 12: Modify Expense Policy
- WHO: Users with ADMIN role
- WHAT: Expense policy configuration (update)
- HOW: Update/Configure
- WHEN: User has ADMIN role

Policy 13: Approve Urgent Expense
- WHO: Users with DIRECTOR role
- WHAT: Urgent expense approval (update)
- HOW: Fast-track approve
- WHEN: User has DIRECTOR role AND expense is marked urgent

Policy 14: View Department Expenses
- WHO: Department managers
- WHAT: Department expenses (read)
- HOW: View/Read
- WHEN: User has MANAGER role AND user department matches expense department

Policy 15: Override Rejection
- WHO: Users with DIRECTOR role
- WHAT: Rejected expense (update)
- HOW: Override/Re-approve
- WHEN: User has DIRECTOR role AND expense was previously rejected

Total Known Policies: 15
"""

from flask import Flask, jsonify, request, abort
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime

app = Flask(__name__)


def require_role(role):
    """Decorator to require specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401, description="Authentication required")
            if role not in current_user.roles:
                abort(403, description=f"{role} role required")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_any_role(*roles):
    """Decorator to require any of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401, description="Authentication required")
            if not any(role in current_user.roles for role in roles):
                abort(403, description=f"One of these roles required: {', '.join(roles)}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Policy 1: View Expenses - Authenticated users can view expense list
@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    """Get all expenses - requires authentication."""
    expenses = Expense.query.all()
    return jsonify([e.to_dict() for e in expenses])


# Policy 2: Create Expense - EMPLOYEE role required
@app.route('/api/expenses', methods=['POST'])
@require_role('EMPLOYEE')
def create_expense():
    """Create expense - requires EMPLOYEE role."""
    data = request.json
    expense = Expense(**data, owner_id=current_user.id)
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense.to_dict()), 201


# Policy 3: Update Own Expense - Owner only, not approved
@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def update_expense(expense_id):
    """Update expense - owner only, not approved."""
    expense = Expense.query.get_or_404(expense_id)

    # Check if user is the owner
    if expense.owner_id != current_user.id:
        abort(403, description="Can only update your own expenses")

    # Check if expense is not approved
    if expense.approved:
        abort(403, description="Cannot update approved expenses")

    data = request.json
    for key, value in data.items():
        setattr(expense, key, value)

    db.session.commit()
    return jsonify(expense.to_dict())


# Policy 4 & 5: Approve Expense - MANAGER for < $5000, DIRECTOR for >= $5000
@app.route('/api/expenses/<int:expense_id>/approve', methods=['POST'])
@require_any_role('MANAGER', 'DIRECTOR')
def approve_expense(expense_id):
    """Approve expense - MANAGER for < $5000, DIRECTOR for >= $5000."""
    expense = Expense.query.get_or_404(expense_id)

    # Policy 4: Small expenses (< $5000) - MANAGER can approve
    if expense.amount < 5000:
        if 'MANAGER' not in current_user.roles and 'DIRECTOR' not in current_user.roles:
            abort(403, description="MANAGER or DIRECTOR role required for expenses < $5,000")

    # Policy 5: Large expenses (>= $5000) - Only DIRECTOR can approve
    if expense.amount >= 5000:
        if 'DIRECTOR' not in current_user.roles:
            abort(403, description="DIRECTOR role required for expenses >= $5,000")

    expense.approved = True
    expense.approved_by = current_user.id
    expense.approved_at = datetime.utcnow()
    db.session.commit()

    return jsonify(expense.to_dict())


# Policy 6: Reject Expense - MANAGER or DIRECTOR
@app.route('/api/expenses/<int:expense_id>/reject', methods=['POST'])
@require_any_role('MANAGER', 'DIRECTOR')
def reject_expense(expense_id):
    """Reject expense - MANAGER or DIRECTOR role required."""
    expense = Expense.query.get_or_404(expense_id)

    data = request.json
    expense.rejected = True
    expense.rejected_by = current_user.id
    expense.rejection_reason = data.get('reason', '')
    expense.rejected_at = datetime.utcnow()
    db.session.commit()

    return jsonify(expense.to_dict())


# Policy 7: Delete Own Expense - Owner only, not approved
@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_own_expense(expense_id):
    """Delete expense - owner only, not approved."""
    expense = Expense.query.get_or_404(expense_id)

    # Check if user is the owner
    if expense.owner_id != current_user.id:
        abort(403, description="Can only delete your own expenses")

    # Check if expense is not approved
    if expense.approved:
        abort(403, description="Cannot delete approved expenses")

    db.session.delete(expense)
    db.session.commit()

    return '', 204


# Policy 8: Delete Any Expense - ADMIN role
@app.route('/api/admin/expenses/<int:expense_id>', methods=['DELETE'])
@require_role('ADMIN')
def delete_any_expense(expense_id):
    """Delete any expense - ADMIN role required."""
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()

    return '', 204


# Policy 9: View Financial Reports - Finance department
@app.route('/api/reports/financial', methods=['GET'])
@login_required
def financial_report():
    """View financial reports - Finance department only."""
    if current_user.department != 'Finance':
        abort(403, description="Finance department access required")

    report = generate_financial_report()
    return jsonify(report)


# Policy 10: Export Expense Data - MANAGER, DIRECTOR, or ADMIN
@app.route('/api/expenses/export', methods=['GET'])
@require_any_role('MANAGER', 'DIRECTOR', 'ADMIN')
def export_expenses():
    """Export expense data - MANAGER, DIRECTOR, or ADMIN role required."""
    expenses = Expense.query.all()
    csv_data = generate_csv_export(expenses)
    return csv_data, 200, {'Content-Type': 'text/csv'}


# Policy 11: View Audit Log - ADMIN role
@app.route('/api/audit-log', methods=['GET'])
@require_role('ADMIN')
def view_audit_log():
    """View audit log - ADMIN role required."""
    audit_entries = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return jsonify([entry.to_dict() for entry in audit_entries])


# Policy 12: Modify Expense Policy - ADMIN role
@app.route('/api/admin/expense-policy', methods=['PUT'])
@require_role('ADMIN')
def modify_expense_policy():
    """Modify expense policy configuration - ADMIN role required."""
    data = request.json
    policy = ExpensePolicy.query.first()

    for key, value in data.items():
        setattr(policy, key, value)

    db.session.commit()
    return jsonify(policy.to_dict())


# Policy 13: Approve Urgent Expense - DIRECTOR role for urgent
@app.route('/api/expenses/<int:expense_id>/approve-urgent', methods=['POST'])
@require_role('DIRECTOR')
def approve_urgent_expense(expense_id):
    """Fast-track approve urgent expense - DIRECTOR role required."""
    expense = Expense.query.get_or_404(expense_id)

    if not expense.is_urgent:
        abort(400, description="Expense is not marked as urgent")

    expense.approved = True
    expense.approved_by = current_user.id
    expense.approved_at = datetime.utcnow()
    expense.fast_tracked = True
    db.session.commit()

    return jsonify(expense.to_dict())


# Policy 14: View Department Expenses - Department managers
@app.route('/api/expenses/department/<string:department>', methods=['GET'])
@require_role('MANAGER')
def view_department_expenses(department):
    """View department expenses - MANAGER role and matching department."""
    # Check if user's department matches
    if current_user.department != department:
        abort(403, description="Can only view expenses from your own department")

    expenses = Expense.query.filter_by(department=department).all()
    return jsonify([e.to_dict() for e in expenses])


# Policy 15: Override Rejection - DIRECTOR role
@app.route('/api/expenses/<int:expense_id>/override-rejection', methods=['POST'])
@require_role('DIRECTOR')
def override_rejection(expense_id):
    """Override rejected expense and re-approve - DIRECTOR role required."""
    expense = Expense.query.get_or_404(expense_id)

    if not expense.rejected:
        abort(400, description="Expense has not been rejected")

    # Override rejection and approve
    expense.rejected = False
    expense.approved = True
    expense.approved_by = current_user.id
    expense.approved_at = datetime.utcnow()
    expense.override_reason = request.json.get('reason', '')
    db.session.commit()

    return jsonify(expense.to_dict())


if __name__ == '__main__':
    app.run(debug=True)
