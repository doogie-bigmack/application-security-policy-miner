import React from 'react';
import { useAuth } from './hooks/useAuth';
import { Navigate } from 'react-router-dom';

// Protected route component
const ProtectedRoute: React.FC<{ children: React.ReactNode; requiredRole?: string }> = ({
    children,
    requiredRole
}) => {
    const { user, isAuthenticated } = useAuth();

    if (!isAuthenticated) {
        return <Navigate to="/login" />;
    }

    if (requiredRole && !user?.roles.includes(requiredRole)) {
        return <Navigate to="/unauthorized" />;
    }

    return <>{children}</>;
};

// Expense List Component
const ExpenseList: React.FC = () => {
    const { user } = useAuth();

    // Only authenticated users can view expenses
    if (!user) {
        return <Navigate to="/login" />;
    }

    return (
        <div>
            <h1>Expenses</h1>
            {/* Expense list content */}
        </div>
    );
};

// Create Expense Component
const CreateExpense: React.FC = () => {
    const { user } = useAuth();

    // Only managers can create expenses
    if (!user?.roles.includes('MANAGER')) {
        return <div>Manager access required</div>;
    }

    return (
        <form>
            {/* Create expense form */}
        </form>
    );
};

// Approve Expense Component
const ApproveExpense: React.FC<{ expense: Expense }> = ({ expense }) => {
    const { user } = useAuth();

    const canApprove = () => {
        if (!user) return false;

        // Managers can approve up to $5000
        if (user.roles.includes('MANAGER') && expense.amount <= 5000) {
            return true;
        }

        // Directors can approve any amount
        if (user.roles.includes('DIRECTOR')) {
            return true;
        }

        return false;
    };

    if (!canApprove()) {
        return null;
    }

    return (
        <button onClick={() => handleApprove(expense.id)}>
            Approve
        </button>
    );
};

// Delete Expense Button
const DeleteExpenseButton: React.FC<{ expenseId: number }> = ({ expenseId }) => {
    const { user } = useAuth();

    // Only admins can delete
    if (!user?.roles.includes('ADMIN')) {
        return null;
    }

    return (
        <button onClick={() => handleDelete(expenseId)}>
            Delete
        </button>
    );
};

// Financial Report Component
const FinancialReport: React.FC = () => {
    const { user } = useAuth();

    // Only Finance department can view
    if (user?.department !== 'Finance') {
        return <div>Finance department access required</div>;
    }

    return (
        <div>
            <h1>Financial Report</h1>
            {/* Report content */}
        </div>
    );
};

export default function App() {
    return (
        <Routes>
            <Route path="/expenses" element={<ProtectedRoute><ExpenseList /></ProtectedRoute>} />
            <Route path="/expenses/create" element={<ProtectedRoute requiredRole="MANAGER"><CreateExpense /></ProtectedRoute>} />
            <Route path="/reports/financial" element={<ProtectedRoute><FinancialReport /></ProtectedRoute>} />
        </Routes>
    );
}
