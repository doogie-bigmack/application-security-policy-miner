"""Integration test for Java scanning."""
import shutil
import tempfile
from pathlib import Path

import pytest
from git import Repo

from app.services.java_scanner_service import JavaScannerService


@pytest.fixture
def java_scanner():
    """Create Java scanner service."""
    return JavaScannerService()


@pytest.fixture
def sample_java_repo():
    """Create a temporary Java repository with authorization code."""
    # Create temporary directory
    tmpdir = tempfile.mkdtemp()
    repo_path = Path(tmpdir) / "test-java-repo"
    repo_path.mkdir()

    # Create Java source files
    src_dir = repo_path / "src/main/java/com/example/security"
    src_dir.mkdir(parents=True)

    # UserController.java - Spring Security
    user_controller = src_dir / "UserController.java"
    user_controller.write_text('''package com.example.security;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN') and #id != authentication.principal.id")
    public ResponseEntity<?> deleteUser(@PathVariable Long id) {
        userService.delete(id);
        return ResponseEntity.ok().build();
    }
}
''')

    # ExpenseService.java - Apache Shiro + method calls
    expense_service = src_dir / "ExpenseService.java"
    expense_service.write_text('''package com.example.security;

import org.apache.shiro.authz.annotation.RequiresRoles;

public class ExpenseService {

    @RequiresRoles("manager")
    public void approveExpense(Expense expense) {
        expense.setStatus(ExpenseStatus.APPROVED);
        expenseRepository.save(expense);
    }

    public boolean canAccess(User user, Resource resource) {
        return user.hasPermission("resource:read") && user.hasRole("MANAGER");
    }
}
''')

    # Initialize git repo
    git_repo = Repo.init(repo_path)
    git_repo.config_writer().set_value("user", "name", "Test User").release()
    git_repo.config_writer().set_value("user", "email", "test@example.com").release()
    git_repo.index.add(["src"])
    git_repo.index.commit("Initial commit")

    yield repo_path

    # Cleanup
    shutil.rmtree(tmpdir)


def test_java_scanner_finds_spring_security(java_scanner, sample_java_repo):
    """Test that Java scanner finds Spring Security annotations."""
    user_controller = sample_java_repo / "src/main/java/com/example/security/UserController.java"
    content = user_controller.read_text()

    # Verify it detects authorization code
    assert java_scanner.has_authorization_code(content)

    # Extract details
    details = java_scanner.extract_authorization_details(content, str(user_controller))

    # Should find @PreAuthorize annotations
    spring_security = [d for d in details if d["category"] == "spring_security"]
    assert len(spring_security) >= 2

    # Check for specific patterns
    preauthorize = [d for d in spring_security if d["pattern"] == "@PreAuthorize"]
    assert len(preauthorize) == 2

    # Verify line numbers are captured
    assert all(d["line_start"] > 0 for d in details)


def test_java_scanner_finds_apache_shiro(java_scanner, sample_java_repo):
    """Test that Java scanner finds Apache Shiro annotations."""
    expense_service = sample_java_repo / "src/main/java/com/example/security/ExpenseService.java"
    content = expense_service.read_text()

    # Verify it detects authorization code
    assert java_scanner.has_authorization_code(content)

    # Extract details
    details = java_scanner.extract_authorization_details(content, str(expense_service))

    # Should find Apache Shiro annotations
    shiro = [d for d in details if d["category"] == "apache_shiro"]
    assert len(shiro) >= 1

    # Check for @RequiresRoles
    requires_roles = [d for d in shiro if d["pattern"] == "@RequiresRoles"]
    assert len(requires_roles) == 1


def test_java_scanner_finds_method_calls(java_scanner, sample_java_repo):
    """Test that Java scanner finds authorization method calls."""
    expense_service = sample_java_repo / "src/main/java/com/example/security/ExpenseService.java"
    content = expense_service.read_text()

    # Extract details
    details = java_scanner.extract_authorization_details(content, str(expense_service))

    # Should find method calls
    method_calls = [d for d in details if d["type"] == "method_call"]
    assert len(method_calls) >= 2

    # Check for hasPermission and hasRole
    has_permission = [d for d in method_calls if "hasPermission" in d["text"]]
    has_role = [d for d in method_calls if "hasRole" in d["text"]]

    assert len(has_permission) >= 1
    assert len(has_role) >= 1


def test_prompt_enhancement_with_real_code(java_scanner, sample_java_repo):
    """Test prompt enhancement with real Java code."""
    user_controller = sample_java_repo / "src/main/java/com/example/security/UserController.java"
    content = user_controller.read_text()

    # Extract details
    details = java_scanner.extract_authorization_details(content, str(user_controller))

    # Build enhanced prompt
    base_prompt = "Analyze this code.\n\nReturn your response as a JSON array of policies."
    enhanced_prompt = java_scanner.enhance_prompt_with_java_context(base_prompt, details)

    # Verify context is added
    assert "Java Authorization Context" in enhanced_prompt
    assert "Spring Security Annotations" in enhanced_prompt
    assert "@PreAuthorize" in enhanced_prompt

    # Verify base prompt is still present
    assert "Return your response as a JSON array of policies" in enhanced_prompt
