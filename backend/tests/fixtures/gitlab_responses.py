"""
GitLab API mock responses for E2E testing.

Provides mock responses that match the structure of real GitLab API responses.
"""

from typing import Any

# Mock response for GitLab token verification (GET /user)
GITLAB_VERIFY_TOKEN: dict[str, Any] = {
    "id": 123456,
    "username": "test-user",
    "email": "test@example.com",
    "name": "Test User",
    "state": "active",
    "avatar_url": "https://gitlab.com/uploads/-/system/user/avatar/123456/avatar.png",
    "web_url": "https://gitlab.com/test-user",
    "created_at": "2020-01-01T00:00:00.000Z",
    "bio": "Test user for E2E testing",
    "location": "Test City",
    "public_email": "test@example.com",
    "is_admin": False,
    "can_create_group": True,
    "can_create_project": True,
}

# Mock response for listing user projects (GET /projects)
GITLAB_LIST_PROJECTS: list[dict[str, Any]] = [
    {
        "id": 111111,
        "name": "test-auth-patterns",
        "name_with_namespace": "Test User / test-auth-patterns",
        "path": "test-auth-patterns",
        "path_with_namespace": "test-user/test-auth-patterns",
        "description": "Test repository with authorization code patterns for policy extraction",
        "visibility": "public",
        "created_at": "2025-01-01T00:00:00.000Z",
        "last_activity_at": "2025-01-09T00:00:00.000Z",
        "web_url": "https://gitlab.com/test-user/test-auth-patterns",
        "default_branch": "main",
        "star_count": 5,
        "forks_count": 2,
    },
    {
        "id": 222222,
        "name": "application-security-policy-miner",
        "name_with_namespace": "Test User / application-security-policy-miner",
        "path": "application-security-policy-miner",
        "path_with_namespace": "test-user/application-security-policy-miner",
        "description": "Application Security Policy Miner - Extract and analyze security policies from code",
        "visibility": "public",
        "created_at": "2024-01-01T00:00:00.000Z",
        "last_activity_at": "2025-01-09T00:00:00.000Z",
        "web_url": "https://gitlab.com/test-user/application-security-policy-miner",
        "default_branch": "main",
        "star_count": 15,
        "forks_count": 5,
    },
]

# Mock response for repository tree (GET /projects/{id}/repository/tree)
GITLAB_REPO_TREE: list[dict[str, Any]] = [
    {
        "id": "abc123",
        "name": "README.md",
        "type": "blob",
        "path": "README.md",
        "mode": "100644",
    },
    {
        "id": "def456",
        "name": "python",
        "type": "tree",
        "path": "python",
        "mode": "040000",
    },
]

# Mock response for file content (GET /projects/{id}/repository/files/{file_path}/raw)
GITLAB_FILE_CONTENT: str = """from functools import wraps
from flask import abort

def require_role(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not has_role(role):
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator
"""

# Mock response for webhook creation (POST /projects/{id}/hooks)
GITLAB_CREATE_WEBHOOK: dict[str, Any] = {
    "id": 999999,
    "url": "https://example.com/webhook",
    "project_id": 111111,
    "push_events": True,
    "issues_events": False,
    "merge_requests_events": False,
    "wiki_page_events": False,
    "created_at": "2025-01-09T00:00:00.000Z",
    "enable_ssl_verification": True,
}
