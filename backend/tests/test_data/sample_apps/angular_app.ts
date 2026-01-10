import { Component, Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot } from '@angular/router';
import { Observable } from 'rxjs';

// Auth Guard Service
@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
    constructor(private router: Router, private authService: AuthService) {}

    canActivate(route: ActivatedRouteSnapshot): boolean {
        const user = this.authService.currentUser;

        if (!user) {
            this.router.navigate(['/login']);
            return false;
        }

        const requiredRole = route.data['role'];
        if (requiredRole && !user.roles.includes(requiredRole)) {
            this.router.navigate(['/unauthorized']);
            return false;
        }

        return true;
    }
}

// Expense List Component
@Component({
    selector: 'app-expense-list',
    template: `
        <div *ngIf="isAuthenticated; else notAuthenticated">
            <h1>Expenses</h1>
            <!-- Expense list -->
        </div>
        <ng-template #notAuthenticated>
            <p>Please log in to view expenses</p>
        </ng-template>
    `
})
export class ExpenseListComponent {
    get isAuthenticated(): boolean {
        return this.authService.isAuthenticated();
    }

    constructor(private authService: AuthService) {}
}

// Create Expense Component
@Component({
    selector: 'app-create-expense',
    template: `
        <div *ngIf="canCreate; else noAccess">
            <h1>Create Expense</h1>
            <form (ngSubmit)="onSubmit()">
                <!-- Form fields -->
            </form>
        </div>
        <ng-template #noAccess>
            <p>Manager access required</p>
        </ng-template>
    `
})
export class CreateExpenseComponent {
    get canCreate(): boolean {
        const user = this.authService.currentUser;
        return user?.roles.includes('MANAGER') || false;
    }

    constructor(private authService: AuthService) {}

    onSubmit(): void {
        // Submit logic
    }
}

// Approve Expense Component
@Component({
    selector: 'app-approve-expense',
    template: `
        <button *ngIf="canApprove()" (click)="approve()">
            Approve
        </button>
    `
})
export class ApproveExpenseComponent {
    expense: Expense;

    constructor(private authService: AuthService) {}

    canApprove(): boolean {
        const user = this.authService.currentUser;
        if (!user) return false;

        // Managers can approve up to $5000
        if (user.roles.includes('MANAGER') && this.expense.amount <= 5000) {
            return true;
        }

        // Directors can approve any amount
        if (user.roles.includes('DIRECTOR')) {
            return true;
        }

        return false;
    }

    approve(): void {
        // Approval logic
    }
}

// Delete Expense Directive
@Component({
    selector: 'app-delete-expense',
    template: `
        <button *ngIf="isAdmin" (click)="delete()">
            Delete
        </button>
    `
})
export class DeleteExpenseComponent {
    get isAdmin(): boolean {
        return this.authService.currentUser?.roles.includes('ADMIN') || false;
    }

    constructor(private authService: AuthService) {}

    delete(): void {
        // Delete logic
    }
}

// Financial Report Component
@Component({
    selector: 'app-financial-report',
    template: `
        <div *ngIf="hasAccess; else noAccess">
            <h1>Financial Report</h1>
            <!-- Report content -->
        </div>
        <ng-template #noAccess>
            <p>Finance department access required</p>
        </ng-template>
    `
})
export class FinancialReportComponent {
    get hasAccess(): boolean {
        const user = this.authService.currentUser;
        return user?.department === 'Finance';
    }

    constructor(private authService: AuthService) {}
}

// Routes configuration
const routes = [
    {
        path: 'expenses',
        component: ExpenseListComponent,
        canActivate: [AuthGuard]
    },
    {
        path: 'expenses/create',
        component: CreateExpenseComponent,
        canActivate: [AuthGuard],
        data: { role: 'MANAGER' }
    },
    {
        path: 'reports/financial',
        component: FinancialReportComponent,
        canActivate: [AuthGuard]
    }
];
