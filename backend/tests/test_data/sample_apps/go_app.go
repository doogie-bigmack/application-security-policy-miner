package handlers

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

// Middleware to require authentication
func RequireAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user := GetUserFromContext(r.Context())
		if user == nil {
			http.Error(w, "Authentication required", http.StatusUnauthorized)
			return
		}
		next(w, r)
	}
}

// Middleware to require specific role
func RequireRole(role string) func(http.HandlerFunc) http.HandlerFunc {
	return func(next http.HandlerFunc) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
			user := GetUserFromContext(r.Context())
			if user == nil {
				http.Error(w, "Authentication required", http.StatusUnauthorized)
				return
			}
			if !user.HasRole(role) {
				http.Error(w, role+" role required", http.StatusForbidden)
				return
			}
			next(w, r)
		}
	}
}

// Middleware to require any of specified roles
func RequireAnyRole(roles ...string) func(http.HandlerFunc) http.HandlerFunc {
	return func(next http.HandlerFunc) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
			user := GetUserFromContext(r.Context())
			if user == nil {
				http.Error(w, "Authentication required", http.StatusUnauthorized)
				return
			}
			hasRole := false
			for _, role := range roles {
				if user.HasRole(role) {
					hasRole = true
					break
				}
			}
			if !hasRole {
				http.Error(w, "Insufficient permissions", http.StatusForbidden)
				return
			}
			next(w, r)
		}
	}
}

// GET /api/expenses - requires authentication
func GetExpenses(w http.ResponseWriter, r *http.Request) {
	expenses, err := expenseService.GetAll()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	json.NewEncoder(w).Encode(expenses)
}

// POST /api/expenses - requires MANAGER role
func CreateExpense(w http.ResponseWriter, r *http.Request) {
	var expense Expense
	if err := json.NewDecoder(r.Body).Decode(&expense); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	created, err := expenseService.Create(&expense)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(created)
}

// PUT /api/expenses/{id}/approve - requires MANAGER or DIRECTOR role
func ApproveExpense(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, _ := strconv.Atoi(vars["id"])

	user := GetUserFromContext(r.Context())
	expense, err := expenseService.GetByID(id)
	if err != nil {
		http.Error(w, "Expense not found", http.StatusNotFound)
		return
	}

	// Managers can approve up to $5000, directors for higher
	if expense.Amount > 5000 && !user.HasRole("DIRECTOR") {
		http.Error(w, "Director role required for amounts over $5,000", http.StatusForbidden)
		return
	}

	expense.Approved = true
	updated, err := expenseService.Update(expense)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(updated)
}

// DELETE /api/expenses/{id} - requires ADMIN role
func DeleteExpense(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, _ := strconv.Atoi(vars["id"])

	if err := expenseService.Delete(id); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// GET /api/reports/financial - Finance department only
func FinancialReport(w http.ResponseWriter, r *http.Request) {
	user := GetUserFromContext(r.Context())

	if user.Department != "Finance" {
		http.Error(w, "Finance department access required", http.StatusForbidden)
		return
	}

	report, err := reportService.GenerateFinancialReport()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(report)
}

// Register routes
func RegisterRoutes(r *mux.Router) {
	r.HandleFunc("/api/expenses", RequireAuth(GetExpenses)).Methods("GET")
	r.HandleFunc("/api/expenses", RequireRole("MANAGER")(CreateExpense)).Methods("POST")
	r.HandleFunc("/api/expenses/{id}/approve", RequireAnyRole("MANAGER", "DIRECTOR")(ApproveExpense)).Methods("PUT")
	r.HandleFunc("/api/expenses/{id}", RequireRole("ADMIN")(DeleteExpense)).Methods("DELETE")
	r.HandleFunc("/api/reports/financial", RequireAuth(FinancialReport)).Methods("GET")
}
