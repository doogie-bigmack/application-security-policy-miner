"""
Scanner service mock responses for E2E testing.

Provides mock scan results with extracted policies.
"""

from typing import Any

# Mock scan result with extracted policies
MOCK_SCAN_RESULT: dict[str, Any] = {
    "scan_id": "scan-123456",
    "repository_id": "repo-111111",
    "status": "completed",
    "started_at": "2025-01-09T00:00:00Z",
    "completed_at": "2025-01-09T00:01:30Z",
    "duration_seconds": 90,
    "policies_extracted": 15,
    "files_scanned": 42,
    "errors": [],
}

# Mock extracted policies from scan
MOCK_EXTRACTED_POLICIES: list[dict[str, Any]] = [
    {
        "id": "policy-001",
        "subject": "User with role 'admin'",
        "resource": "/api/admin/users",
        "action": "DELETE",
        "conditions": "None",
        "evidence": {
            "file_path": "python/flask_decorators.py",
            "line_number": 15,
            "code_snippet": "@require_role('admin')\ndef delete_user(user_id: int):\n    # Delete user logic",
            "language": "python",
        },
        "confidence": 0.95,
        "source": "code_analysis",
    },
    {
        "id": "policy-002",
        "subject": "User with role 'editor'",
        "resource": "/api/posts",
        "action": "CREATE",
        "conditions": "None",
        "evidence": {
            "file_path": "python/flask_decorators.py",
            "line_number": 25,
            "code_snippet": "@require_role('editor')\ndef create_post(post_data: dict):\n    # Create post logic",
            "language": "python",
        },
        "confidence": 0.92,
        "source": "code_analysis",
    },
    {
        "id": "policy-003",
        "subject": "User with permission 'read:documents'",
        "resource": "/api/documents/{id}",
        "action": "GET",
        "conditions": "user.organization_id == document.organization_id",
        "evidence": {
            "file_path": "csharp/Controllers.cs",
            "line_number": 42,
            "code_snippet": "[Authorize(Policy = \"read:documents\")]\npublic IActionResult GetDocument(int id)",
            "language": "csharp",
        },
        "confidence": 0.89,
        "source": "code_analysis",
    },
    {
        "id": "policy-004",
        "subject": "User with role 'ROLE_ADMIN'",
        "resource": "/api/settings",
        "action": "UPDATE",
        "conditions": "None",
        "evidence": {
            "file_path": "java/RestController.java",
            "line_number": 58,
            "code_snippet": "@PreAuthorize(\"hasRole('ADMIN')\")\npublic ResponseEntity<Settings> updateSettings(@RequestBody Settings settings)",
            "language": "java",
        },
        "confidence": 0.94,
        "source": "code_analysis",
    },
    {
        "id": "policy-005",
        "subject": "Authenticated user",
        "resource": "/api/profile",
        "action": "GET",
        "conditions": "request.user_id == profile.user_id",
        "evidence": {
            "file_path": "javascript/middleware.js",
            "line_number": 12,
            "code_snippet": "requireAuth(),\ncheckOwnership('user_id'),\ngetProfile",
            "language": "javascript",
        },
        "confidence": 0.87,
        "source": "code_analysis",
    },
]

# Mock incremental scan result (fewer files, faster)
MOCK_INCREMENTAL_SCAN_RESULT: dict[str, Any] = {
    "scan_id": "scan-123457",
    "repository_id": "repo-111111",
    "status": "completed",
    "started_at": "2025-01-09T00:02:00Z",
    "completed_at": "2025-01-09T00:02:15Z",
    "duration_seconds": 15,
    "policies_extracted": 3,
    "files_scanned": 5,
    "errors": [],
}

# Mock scan with errors
MOCK_SCAN_WITH_ERRORS: dict[str, Any] = {
    "scan_id": "scan-123458",
    "repository_id": "repo-111111",
    "status": "completed_with_errors",
    "started_at": "2025-01-09T00:03:00Z",
    "completed_at": "2025-01-09T00:03:45Z",
    "duration_seconds": 45,
    "policies_extracted": 10,
    "files_scanned": 38,
    "errors": [
        {
            "file_path": "rust/auth.rs",
            "error": "Unsupported language: Rust",
            "severity": "warning",
        }
    ],
}
