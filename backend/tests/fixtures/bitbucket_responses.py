"""
Bitbucket API mock responses for E2E testing.

Provides mock responses that match the structure of real Bitbucket API responses.
"""

from typing import Any

# Mock response for Bitbucket user verification (GET /user)
BITBUCKET_VERIFY_TOKEN: dict[str, Any] = {
    "username": "test-user",
    "display_name": "Test User",
    "uuid": "{12345678-1234-1234-1234-123456789012}",
    "links": {
        "self": {"href": "https://api.bitbucket.org/2.0/users/test-user"},
        "html": {"href": "https://bitbucket.org/test-user"},
        "avatar": {"href": "https://bitbucket.org/account/test-user/avatar/"},
    },
    "created_on": "2020-01-01T00:00:00.000000+00:00",
    "type": "user",
    "account_id": "123456:abcdef12-3456-7890-abcd-ef1234567890",
}

# Mock response for listing repositories (GET /repositories/{workspace})
BITBUCKET_LIST_REPOS: dict[str, Any] = {
    "pagelen": 10,
    "page": 1,
    "size": 2,
    "values": [
        {
            "slug": "test-auth-patterns",
            "name": "test-auth-patterns",
            "full_name": "test-user/test-auth-patterns",
            "description": "Test repository with authorization code patterns for policy extraction",
            "is_private": False,
            "created_on": "2025-01-01T00:00:00.000000+00:00",
            "updated_on": "2025-01-09T00:00:00.000000+00:00",
            "mainbranch": {"name": "main", "type": "branch"},
            "language": "python",
            "links": {
                "self": {"href": "https://api.bitbucket.org/2.0/repositories/test-user/test-auth-patterns"},
                "html": {"href": "https://bitbucket.org/test-user/test-auth-patterns"},
            },
            "uuid": "{11111111-1111-1111-1111-111111111111}",
        },
        {
            "slug": "application-security-policy-miner",
            "name": "application-security-policy-miner",
            "full_name": "test-user/application-security-policy-miner",
            "description": "Application Security Policy Miner - Extract and analyze security policies from code",
            "is_private": False,
            "created_on": "2024-01-01T00:00:00.000000+00:00",
            "updated_on": "2025-01-09T00:00:00.000000+00:00",
            "mainbranch": {"name": "main", "type": "branch"},
            "language": "python",
            "links": {
                "self": {"href": "https://api.bitbucket.org/2.0/repositories/test-user/application-security-policy-miner"},
                "html": {"href": "https://bitbucket.org/test-user/application-security-policy-miner"},
            },
            "uuid": "{22222222-2222-2222-2222-222222222222}",
        },
    ],
}

# Mock response for repository source (GET /repositories/{workspace}/{repo_slug}/src/{node}/{path})
BITBUCKET_FILE_CONTENT: str = """from functools import wraps
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

# Mock response for webhook creation (POST /repositories/{workspace}/{repo_slug}/hooks)
BITBUCKET_CREATE_WEBHOOK: dict[str, Any] = {
    "uuid": "{99999999-9999-9999-9999-999999999999}",
    "url": "https://example.com/webhook",
    "description": "Policy Miner webhook",
    "subject_type": "repository",
    "active": True,
    "created_at": "2025-01-09T00:00:00.000000+00:00",
    "events": ["repo:push"],
    "links": {
        "self": {"href": "https://api.bitbucket.org/2.0/repositories/test-user/test-auth-patterns/hooks/99999999-9999-9999-9999-999999999999"}
    },
}
