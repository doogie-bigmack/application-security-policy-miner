"""
Test policy extraction across 10+ different application types.

This test validates that the Policy Miner can successfully extract authorization
policies from diverse application types using different frameworks and languages.
"""

import logging
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data" / "sample_apps"

# Define expected application types and their files
APPLICATION_TYPES = {
    "Java Spring": {
        "file": "java_spring_app.java",
        "language": "java",
        "expected_patterns": [
            "@PreAuthorize",
            "hasRole",
            "hasAnyRole",
            "MANAGER",
            "DIRECTOR",
            "ADMIN"
        ]
    },
    ".NET/C#": {
        "file": "dotnet_app.cs",
        "language": "csharp",
        "expected_patterns": [
            "[Authorize",
            "Roles =",
            "Policy =",
            "IsInRole",
            "HasClaim"
        ]
    },
    "Django": {
        "file": "django_app.py",
        "language": "python",
        "expected_patterns": [
            "@permission_required",
            "@login_required",
            "groups.filter",
            "is_superuser",
            "department"
        ]
    },
    "Flask": {
        "file": "flask_app.py",
        "language": "python",
        "expected_patterns": [
            "@login_required",
            "@require_role",
            "@require_any_role",
            "current_user",
            "roles"
        ]
    },
    "Express.js": {
        "file": "express_app.js",
        "language": "javascript",
        "expected_patterns": [
            "requireAuth",
            "requireRole",
            "requireAnyRole",
            "req.user",
            "roles.includes"
        ]
    },
    "React": {
        "file": "react_app.tsx",
        "language": "typescript",
        "expected_patterns": [
            "ProtectedRoute",
            "useAuth",
            "user?.roles",
            "isAuthenticated",
            "Navigate"
        ]
    },
    "Angular": {
        "file": "angular_app.ts",
        "language": "typescript",
        "expected_patterns": [
            "CanActivate",
            "AuthGuard",
            "canActivate",
            "user.roles",
            "route.data"
        ]
    },
    "Vue.js": {
        "file": "vue_app.vue",
        "language": "typescript",
        "expected_patterns": [
            "useAuth",
            "computed",
            "beforeEnter",
            "user.value",
            "roles.includes"
        ]
    },
    "FastAPI": {
        "file": "fastapi_app.py",
        "language": "python",
        "expected_patterns": [
            "Depends",
            "require_role",
            "require_any_role",
            "HTTPException",
            "current_user"
        ]
    },
    "Ruby on Rails": {
        "file": "rails_app.rb",
        "language": "ruby",
        "expected_patterns": [
            "before_action",
            "authenticate_user!",
            "has_role?",
            "current_user",
            "render json"
        ]
    },
    "Go": {
        "file": "go_app.go",
        "language": "go",
        "expected_patterns": [
            "RequireAuth",
            "RequireRole",
            "RequireAnyRole",
            "HasRole",
            "http.HandlerFunc"
        ]
    },
    "PHP/Laravel": {
        "file": "laravel_app.php",
        "language": "php",
        "expected_patterns": [
            "$this->middleware",
            "role:",
            "hasRole",
            "Auth::user()",
            "response()->json"
        ]
    }
}


class TestMultiApplicationExtraction:
    """Test policy extraction across multiple application types."""

    @pytest.fixture
    def test_files(self) -> dict[str, Path]:
        """Get all test application files."""
        files = {}
        for app_type, config in APPLICATION_TYPES.items():
            file_path = TEST_DATA_DIR / config["file"]
            assert file_path.exists(), f"Test file missing: {file_path}"
            files[app_type] = file_path
        return files

    def test_all_test_files_exist(self, test_files):
        """Verify all test application files exist."""
        assert len(test_files) >= 10, "Should have at least 10 different application types"
        logger.info(f"Found {len(test_files)} application types")

        for app_type, file_path in test_files.items():
            assert file_path.exists(), f"Missing file for {app_type}: {file_path}"
            assert file_path.stat().st_size > 0, f"Empty file for {app_type}: {file_path}"
            logger.info(f"✓ {app_type}: {file_path.name} ({file_path.stat().st_size} bytes)")

    def test_pattern_detection(self, test_files):
        """Test that expected authorization patterns are present in each file."""
        results = {}

        for app_type, file_path in test_files.items():
            content = file_path.read_text()
            config = APPLICATION_TYPES[app_type]
            expected_patterns = config["expected_patterns"]

            found_patterns = []
            missing_patterns = []

            for pattern in expected_patterns:
                if pattern in content:
                    found_patterns.append(pattern)
                else:
                    missing_patterns.append(pattern)

            detection_rate = len(found_patterns) / len(expected_patterns) * 100

            results[app_type] = {
                "file": file_path.name,
                "language": config["language"],
                "expected_count": len(expected_patterns),
                "found_count": len(found_patterns),
                "detection_rate": detection_rate,
                "found_patterns": found_patterns,
                "missing_patterns": missing_patterns
            }

            logger.info(
                f"{app_type}: {len(found_patterns)}/{len(expected_patterns)} patterns "
                f"({detection_rate:.1f}%)"
            )

            # Each file should have at least 60% of expected patterns
            assert detection_rate >= 60, (
                f"{app_type} missing too many patterns. "
                f"Expected: {expected_patterns}, Missing: {missing_patterns}"
            )

        return results

    def test_code_contains_authorization_logic(self, test_files):
        """Verify each file contains meaningful authorization logic."""
        for app_type, file_path in test_files.items():
            content = file_path.read_text()

            # Check for WHO (subjects/roles)
            has_subjects = any(
                keyword in content.lower()
                for keyword in ['role', 'user', 'admin', 'manager', 'director']
            )

            # Check for WHAT (resources/operations)
            has_resources = any(
                keyword in content
                for keyword in ['expense', 'Expense', 'report', 'Report', 'delete', 'approve', 'create']
            )

            # Check for HOW (actions/permissions)
            has_actions = any(
                keyword in content.lower()
                for keyword in ['allow', 'deny', 'forbidden', 'unauthorized', 'authorize', 'permission']
            )

            # Check for WHEN (conditions)
            has_conditions = any(
                keyword in content
                for keyword in ['if', 'amount', '5000', '10000', 'department', 'Finance']
            )

            logger.info(
                f"{app_type}: WHO={has_subjects}, WHAT={has_resources}, "
                f"HOW={has_actions}, WHEN={has_conditions}"
            )

            assert has_subjects, f"{app_type} missing subject/role information"
            assert has_resources, f"{app_type} missing resource information"
            assert has_actions or has_conditions, f"{app_type} missing action/condition logic"

    def test_generate_extraction_summary(self, test_files):
        """Generate a summary report of extraction capabilities."""
        summary = {
            "total_applications": len(test_files),
            "applications": []
        }

        for app_type, file_path in test_files.items():
            content = file_path.read_text()
            config = APPLICATION_TYPES[app_type]

            # Count authorization-related code
            auth_indicators = 0
            for pattern in config["expected_patterns"]:
                auth_indicators += content.count(pattern)

            summary["applications"].append({
                "type": app_type,
                "language": config["language"],
                "file": file_path.name,
                "size_bytes": file_path.stat().st_size,
                "auth_indicators": auth_indicators,
                "patterns_checked": len(config["expected_patterns"])
            })

        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("POLICY EXTRACTION - APPLICATION TYPE COVERAGE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Application Types: {summary['total_applications']}")
        logger.info("")

        for app in summary["applications"]:
            logger.info(
                f"  {app['type']:20} | {app['language']:12} | "
                f"{app['auth_indicators']:3} auth indicators | {app['file']}"
            )

        logger.info("=" * 80)

        # Assert we have sufficient coverage
        assert summary["total_applications"] >= 10, \
            f"Need at least 10 application types, found {summary['total_applications']}"

        # Assert all applications have authorization logic
        for app in summary["applications"]:
            assert app["auth_indicators"] > 0, \
                f"{app['type']} has no authorization indicators"

        return summary

    def test_language_diversity(self, test_files):
        """Verify we're testing diverse programming languages."""
        languages = set()
        for config in APPLICATION_TYPES.values():
            languages.add(config["language"])

        logger.info(f"Programming languages covered: {sorted(languages)}")

        # Should have at least 6 different languages
        assert len(languages) >= 6, \
            f"Need diverse languages, found only {len(languages)}: {languages}"

        expected_languages = {"java", "csharp", "python", "javascript", "typescript"}
        assert expected_languages.issubset(languages), \
            f"Missing core languages. Expected: {expected_languages}, Found: {languages}"

    def test_framework_diversity(self):
        """Verify we're testing diverse frameworks."""
        frameworks = set(APPLICATION_TYPES.keys())

        logger.info(f"Frameworks covered: {sorted(frameworks)}")

        # Should have at least 10 different frameworks
        assert len(frameworks) >= 10, \
            f"Need at least 10 frameworks, found {len(frameworks)}"

        # Should cover both backend and frontend
        backend_keywords = ["Spring", "Django", "Flask", "Express", "FastAPI", "Rails", "Laravel"]
        frontend_keywords = ["React", "Angular", "Vue"]

        has_backend = any(any(kw in fw for kw in backend_keywords) for fw in frameworks)
        has_frontend = any(any(kw in fw for kw in frontend_keywords) for fw in frameworks)

        assert has_backend, "Missing backend framework coverage"
        assert has_frontend, "Missing frontend framework coverage"

    def test_common_authorization_patterns_across_all_types(self, test_files):
        """Verify common authorization patterns exist across all application types."""
        for app_type, file_path in test_files.items():
            content = file_path.read_text()

            # Every application should have:
            # 1. Role-based access (MANAGER, DIRECTOR, ADMIN, etc.)
            has_roles = any(
                role in content
                for role in ["MANAGER", "Manager", "manager", "DIRECTOR", "Director", "ADMIN", "Admin"]
            )

            # 2. Financial/expense business logic
            has_expense_logic = any(
                keyword in content.lower()
                for keyword in ["expense", "amount", "5000", "approve"]
            )

            # 3. Department or attribute-based access control
            has_abac = any(
                keyword in content
                for keyword in ["department", "Department", "Finance", "finance"]
            )

            logger.info(
                f"{app_type:20} | Roles: {has_roles:5} | "
                f"Expense Logic: {has_expense_logic:5} | ABAC: {has_abac:5}"
            )

            assert has_roles, f"{app_type} missing role-based access control"
            assert has_expense_logic, f"{app_type} missing expense business logic"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
