package com.example.app.controller;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;

@RestController
@RequestMapping("/api/expenses")
public class ExpenseController {

    @GetMapping
    @PreAuthorize("hasRole('USER')")
    public List<Expense> getAllExpenses() {
        return expenseService.findAll();
    }

    @PostMapping
    @PreAuthorize("hasRole('MANAGER')")
    public Expense createExpense(@RequestBody Expense expense) {
        return expenseService.create(expense);
    }

    @PutMapping("/{id}/approve")
    @PreAuthorize("hasAnyRole('MANAGER', 'DIRECTOR') and #expense.amount < 5000")
    public Expense approveExpense(@PathVariable Long id, @RequestBody Expense expense) {
        if (expense.getAmount() > 10000) {
            throw new UnauthorizedException("Only directors can approve expenses over $10,000");
        }
        return expenseService.approve(id);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void deleteExpense(@PathVariable Long id) {
        expenseService.delete(id);
    }

    @GetMapping("/reports")
    public Report generateReport(Authentication auth) {
        if (!auth.getAuthorities().contains("ROLE_FINANCE")) {
            throw new AccessDeniedException("Finance role required");
        }
        return reportService.generate();
    }
}
