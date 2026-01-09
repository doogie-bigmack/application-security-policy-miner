"""Unit tests for Java scanner service."""
import pytest

from app.services.java_scanner_service import JavaScannerService


@pytest.fixture
def java_scanner():
    """Create Java scanner service."""
    return JavaScannerService()


def test_detect_spring_security_annotations(java_scanner):
    """Test detection of Spring Security annotations."""
    code = """
    @RestController
    public class UserController {

        @PreAuthorize("hasRole('ADMIN')")
        public ResponseEntity<User> deleteUser(@PathVariable Long id) {
            userService.delete(id);
            return ResponseEntity.ok().build();
        }

        @Secured("ROLE_MANAGER")
        public List<User> getAllUsers() {
            return userService.findAll();
        }
    }
    """

    assert java_scanner.has_authorization_code(code)
    details = java_scanner.extract_authorization_details(code, "UserController.java")

    # Should find 2 Spring Security annotations
    assert len(details) >= 2

    # Check for @PreAuthorize
    preauthorize = [d for d in details if d["pattern"] == "@PreAuthorize"]
    assert len(preauthorize) == 1
    assert preauthorize[0]["category"] == "spring_security"
    assert "hasRole('ADMIN')" in preauthorize[0]["text"]

    # Check for @Secured
    secured = [d for d in details if d["pattern"] == "@Secured"]
    assert len(secured) == 1
    assert secured[0]["category"] == "spring_security"


def test_detect_apache_shiro_annotations(java_scanner):
    """Test detection of Apache Shiro annotations."""
    code = """
    public class AccountService {

        @RequiresRoles("admin")
        public void deleteAccount(Long accountId) {
            accountRepository.delete(accountId);
        }

        @RequiresPermissions("account:read")
        public Account getAccount(Long id) {
            return accountRepository.findById(id);
        }
    }
    """

    assert java_scanner.has_authorization_code(code)
    details = java_scanner.extract_authorization_details(code, "AccountService.java")

    # Should find 2 Shiro annotations
    assert len(details) >= 2

    # Check for @RequiresRoles
    roles = [d for d in details if d["pattern"] == "@RequiresRoles"]
    assert len(roles) == 1
    assert roles[0]["category"] == "apache_shiro"

    # Check for @RequiresPermissions
    perms = [d for d in details if d["pattern"] == "@RequiresPermissions"]
    assert len(perms) == 1
    assert perms[0]["category"] == "apache_shiro"


def test_detect_method_calls(java_scanner):
    """Test detection of authorization method calls."""
    code = """
    public class ExpenseService {

        public void approveExpense(Expense expense, User user) {
            if (user.hasRole("MANAGER") && expense.getAmount() < 5000) {
                expense.setStatus(ExpenseStatus.APPROVED);
                expenseRepository.save(expense);
            }
        }

        public boolean canAccess(User user, Resource resource) {
            return user.hasPermission("resource:read");
        }
    }
    """

    assert java_scanner.has_authorization_code(code)
    details = java_scanner.extract_authorization_details(code, "ExpenseService.java")

    # Should find hasRole and hasPermission method calls
    method_calls = [d for d in details if d["type"] == "method_call"]
    assert len(method_calls) >= 2

    # Check for hasRole
    has_role = [d for d in method_calls if "hasRole" in d["text"]]
    assert len(has_role) >= 1

    # Check for hasPermission
    has_perm = [d for d in method_calls if "hasPermission" in d["text"]]
    assert len(has_perm) >= 1


def test_detect_conditionals(java_scanner):
    """Test detection of authorization conditionals."""
    code = """
    public class PolicyService {

        public void executePolicy(User user, Action action) {
            if (user.getRole().equals("ADMIN") || user.isAuthenticated()) {
                action.execute();
            }
        }

        public boolean checkPermission(User user) {
            if (user.hasAuthority("WRITE_PERMISSION")) {
                return true;
            }
            return false;
        }
    }
    """

    assert java_scanner.has_authorization_code(code)
    details = java_scanner.extract_authorization_details(code, "PolicyService.java")

    # Should find method calls (hasAuthority is detected as a method call)
    method_calls = [d for d in details if d["type"] == "method_call"]
    assert len(method_calls) >= 1


def test_no_authorization_code(java_scanner):
    """Test that non-authorization code is not detected."""
    code = """
    public class CalculatorService {

        public int add(int a, int b) {
            return a + b;
        }

        public int multiply(int a, int b) {
            return a * b;
        }
    }
    """

    assert not java_scanner.has_authorization_code(code)
    details = java_scanner.extract_authorization_details(code, "CalculatorService.java")
    assert len(details) == 0


def test_complex_spring_security(java_scanner):
    """Test complex Spring Security patterns."""
    code = """
    @RestController
    @RequestMapping("/api/expenses")
    public class ExpenseController {

        @PostMapping("/{id}/approve")
        @PreAuthorize("hasRole('MANAGER') and #expense.amount < 5000")
        public ResponseEntity<Expense> approveExpense(
            @PathVariable Long id,
            @RequestBody Expense expense
        ) {
            expenseService.approve(expense);
            return ResponseEntity.ok(expense);
        }

        @GetMapping
        @RolesAllowed({"ADMIN", "MANAGER", "USER"})
        public List<Expense> getAllExpenses() {
            return expenseService.findAll();
        }
    }
    """

    assert java_scanner.has_authorization_code(code)
    details = java_scanner.extract_authorization_details(code, "ExpenseController.java")

    # Should find @PreAuthorize and @RolesAllowed
    assert len(details) >= 2

    preauth = [d for d in details if d["pattern"] == "@PreAuthorize"]
    assert len(preauth) == 1
    assert "hasRole('MANAGER')" in preauth[0]["text"]
    assert "expense.amount" in preauth[0]["text"]


def test_prompt_enhancement(java_scanner):
    """Test Java-specific prompt enhancement."""
    base_prompt = """Analyze this code.

Return your response as a JSON array of policies."""

    details = [
        {
            "category": "spring_security",
            "pattern": "@PreAuthorize",
            "line_start": 10,
            "text": "@PreAuthorize(\"hasRole('ADMIN')\")",
        },
        {
            "category": "method_calls",
            "pattern": "hasPermission",
            "line_start": 20,
            "text": "user.hasPermission('write')",
        },
    ]

    enhanced_prompt = java_scanner.enhance_prompt_with_java_context(base_prompt, details)

    # Should contain Java context
    assert "Java Authorization Context" in enhanced_prompt
    assert "Spring Security Annotations" in enhanced_prompt
    assert "@PreAuthorize" in enhanced_prompt
    assert "Authorization Method Calls" in enhanced_prompt
    assert "hasPermission" in enhanced_prompt


def test_line_numbers_accurate(java_scanner):
    """Test that line numbers are accurate."""
    code = """package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
public class TestController {

    @PreAuthorize("hasRole('ADMIN')")
    public void adminOnly() {
        // admin code
    }
}
"""

    details = java_scanner.extract_authorization_details(code, "TestController.java")

    # @PreAuthorize should be on line 8 (0-indexed line 7)
    preauth = [d for d in details if d["pattern"] == "@PreAuthorize"]
    assert len(preauth) == 1
    assert preauth[0]["line_start"] == 8


def test_multiple_annotations_on_same_method(java_scanner):
    """Test detection of multiple annotations on same method."""
    code = """
    public class SecureService {

        @PreAuthorize("hasRole('USER')")
        @PostAuthorize("returnObject.owner == authentication.name")
        public Document getDocument(Long id) {
            return documentService.findById(id);
        }
    }
    """

    assert java_scanner.has_authorization_code(code)
    details = java_scanner.extract_authorization_details(code, "SecureService.java")

    # Should find both @PreAuthorize and @PostAuthorize
    assert len(details) >= 2

    preauth = [d for d in details if d["pattern"] == "@PreAuthorize"]
    postauth = [d for d in details if d["pattern"] == "@PostAuthorize"]

    assert len(preauth) == 1
    assert len(postauth) == 1
