"""
Azure DevOps API mock responses for E2E testing.

Provides mock responses that match the structure of real Azure DevOps API responses.
"""

from typing import Any

# Mock response for profile verification (GET /_apis/profile/profiles/me)
AZURE_DEVOPS_VERIFY_TOKEN: dict[str, Any] = {
    "displayName": "Test User",
    "publicAlias": "test-user",
    "emailAddress": "test@example.com",
    "coreRevision": 123456,
    "timeStamp": "2025-01-09T00:00:00Z",
    "id": "12345678-1234-1234-1234-123456789012",
    "revision": 1,
}

# Mock response for listing repositories (GET /{organization}/{project}/_apis/git/repositories)
AZURE_DEVOPS_LIST_REPOS: dict[str, Any] = {
    "value": [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "test-auth-patterns",
            "url": "https://dev.azure.com/test-org/_apis/git/repositories/11111111-1111-1111-1111-111111111111",
            "project": {
                "id": "22222222-2222-2222-2222-222222222222",
                "name": "TestProject",
                "state": "wellFormed",
            },
            "defaultBranch": "refs/heads/main",
            "size": 128,
            "remoteUrl": "https://dev.azure.com/test-org/TestProject/_git/test-auth-patterns",
            "sshUrl": "git@ssh.dev.azure.com:v3/test-org/TestProject/test-auth-patterns",
            "webUrl": "https://dev.azure.com/test-org/TestProject/_git/test-auth-patterns",
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "name": "application-security-policy-miner",
            "url": "https://dev.azure.com/test-org/_apis/git/repositories/33333333-3333-3333-3333-333333333333",
            "project": {
                "id": "22222222-2222-2222-2222-222222222222",
                "name": "TestProject",
                "state": "wellFormed",
            },
            "defaultBranch": "refs/heads/main",
            "size": 2048,
            "remoteUrl": "https://dev.azure.com/test-org/TestProject/_git/application-security-policy-miner",
            "sshUrl": "git@ssh.dev.azure.com:v3/test-org/TestProject/application-security-policy-miner",
            "webUrl": "https://dev.azure.com/test-org/TestProject/_git/application-security-policy-miner",
        },
    ],
    "count": 2,
}

# Mock response for file content (GET /{organization}/{project}/_apis/git/repositories/{repositoryId}/items)
AZURE_DEVOPS_FILE_CONTENT: str = """from functools import wraps
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

# Mock response for webhook creation (POST /{organization}/_apis/hooks/subscriptions)
AZURE_DEVOPS_CREATE_WEBHOOK: dict[str, Any] = {
    "id": "99999999-9999-9999-9999-999999999999",
    "url": "https://dev.azure.com/test-org/_apis/hooks/subscriptions/99999999-9999-9999-9999-999999999999",
    "publisherId": "tfs",
    "eventType": "git.push",
    "resourceVersion": "1.0",
    "consumerId": "webHooks",
    "consumerActionId": "httpRequest",
    "publisherInputs": {
        "projectId": "22222222-2222-2222-2222-222222222222",
        "repository": "11111111-1111-1111-1111-111111111111",
    },
    "consumerInputs": {
        "url": "https://example.com/webhook",
    },
    "createdBy": {
        "displayName": "Test User",
        "id": "12345678-1234-1234-1234-123456789012",
    },
    "createdDate": "2025-01-09T00:00:00Z",
    "status": "enabled",
}
