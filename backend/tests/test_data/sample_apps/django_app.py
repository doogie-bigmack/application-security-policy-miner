from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_expenses(request):
    """List all expenses - requires authentication"""
    expenses = Expense.objects.all()
    return Response(ExpenseSerializer(expenses, many=True).data)

@api_view(['POST'])
@permission_required('expenses.add_expense', raise_exception=True)
def create_expense(request):
    """Create expense - requires add_expense permission"""
    serializer = ExpenseSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['PUT'])
def approve_expense(request, expense_id):
    """Approve expense - managers for < $5000, directors for higher"""
    expense = Expense.objects.get(id=expense_id)

    if not request.user.groups.filter(name='Manager').exists():
        return Response({'error': 'Manager role required'}, status=403)

    if expense.amount > 5000 and not request.user.groups.filter(name='Director').exists():
        return Response({'error': 'Director role required for amounts over $5,000'}, status=403)

    expense.approved = True
    expense.save()
    return Response(ExpenseSerializer(expense).data)

@login_required
@require_http_methods(["DELETE"])
def delete_expense(request, expense_id):
    """Delete expense - admin only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Admin access required'}, status=403)

    Expense.objects.filter(id=expense_id).delete()
    return JsonResponse({'status': 'deleted'})

@permission_required('expenses.view_sensitive_data')
def view_financial_report(request):
    """View financial reports - requires view_sensitive_data permission"""
    if request.user.department != 'Finance':
        return JsonResponse({'error': 'Finance department only'}, status=403)

    report = generate_financial_report()
    return JsonResponse(report)
