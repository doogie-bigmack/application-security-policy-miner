from flask import Flask, jsonify, request, abort
from flask_login import login_required, current_user
from functools import wraps

app = Flask(__name__)

def require_role(role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if role not in current_user.roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_any_role(*roles):
    """Decorator to require any of the specified roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not any(role in current_user.roles for role in roles):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    """Get all expenses - requires authentication"""
    expenses = Expense.query.all()
    return jsonify([e.to_dict() for e in expenses])

@app.route('/api/expenses', methods=['POST'])
@require_role('MANAGER')
def create_expense():
    """Create expense - requires MANAGER role"""
    data = request.json
    expense = Expense(**data)
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense.to_dict()), 201

@app.route('/api/expenses/<int:expense_id>/approve', methods=['PUT'])
@require_any_role('MANAGER', 'DIRECTOR')
def approve_expense(expense_id):
    """Approve expense - MANAGER for < $5000, DIRECTOR for higher"""
    expense = Expense.query.get_or_404(expense_id)

    if expense.amount > 5000 and 'DIRECTOR' not in current_user.roles:
        return jsonify({'error': 'Director role required for amounts over $5,000'}), 403

    expense.approved = True
    db.session.commit()
    return jsonify(expense.to_dict())

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@require_role('ADMIN')
def delete_expense(expense_id):
    """Delete expense - requires ADMIN role"""
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return '', 204

@app.route('/api/reports/financial', methods=['GET'])
def financial_report():
    """Generate financial report - Finance department only"""
    if not current_user.is_authenticated:
        abort(401)

    if current_user.department != 'Finance':
        return jsonify({'error': 'Finance department access required'}), 403

    report = generate_report()
    return jsonify(report)
