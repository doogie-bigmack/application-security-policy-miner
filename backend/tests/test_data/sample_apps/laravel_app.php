<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use App\Models\Expense;

class ExpenseController extends Controller
{
    public function __construct()
    {
        // All routes require authentication
        $this->middleware('auth');

        // Specific role requirements
        $this->middleware('role:manager')->only(['store']);
        $this->middleware('role:manager,director')->only(['approve']);
        $this->middleware('role:admin')->only(['destroy']);
    }

    /**
     * GET /api/expenses
     * All authenticated users can view expenses
     */
    public function index()
    {
        $expenses = Expense::all();
        return response()->json($expenses);
    }

    /**
     * POST /api/expenses
     * Only managers can create expenses
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'amount' => 'required|numeric',
            'description' => 'required|string',
            'category' => 'required|string',
        ]);

        $expense = Expense::create($validated);
        return response()->json($expense, 201);
    }

    /**
     * PUT /api/expenses/{id}/approve
     * Managers can approve up to $5000, directors for higher
     */
    public function approve($id)
    {
        $expense = Expense::findOrFail($id);
        $user = Auth::user();

        // Check if user has manager or director role
        if (!$user->hasRole('manager') && !$user->hasRole('director')) {
            return response()->json(['error' => 'Manager or Director role required'], 403);
        }

        // Directors only for amounts over $5000
        if ($expense->amount > 5000 && !$user->hasRole('director')) {
            return response()->json(['error' => 'Director role required for amounts over $5,000'], 403);
        }

        $expense->approved = true;
        $expense->save();

        return response()->json($expense);
    }

    /**
     * DELETE /api/expenses/{id}
     * Only admins can delete
     */
    public function destroy($id)
    {
        $expense = Expense::findOrFail($id);
        $expense->delete();

        return response()->json(null, 204);
    }

    /**
     * GET /api/reports/financial
     * Finance department only
     */
    public function financialReport()
    {
        $user = Auth::user();

        if ($user->department !== 'Finance') {
            return response()->json(['error' => 'Finance department access required'], 403);
        }

        $report = $this->reportService->generateFinancialReport();
        return response()->json($report);
    }
}

// Middleware: app/Http/Middleware/RoleMiddleware.php
namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class RoleMiddleware
{
    /**
     * Handle an incoming request.
     */
    public function handle(Request $request, Closure $next, ...$roles)
    {
        if (!$request->user()) {
            return response()->json(['error' => 'Unauthenticated'], 401);
        }

        foreach ($roles as $role) {
            if ($request->user()->hasRole($role)) {
                return $next($request);
            }
        }

        return response()->json(['error' => 'Unauthorized - required role: ' . implode(' or ', $roles)], 403);
    }
}
