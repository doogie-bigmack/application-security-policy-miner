"""
GitHub API mock responses for E2E testing.

Provides mock responses that match the structure of real GitHub API responses.
"""

from typing import Any

# Mock response for GitHub token verification (GET /user)
GITHUB_VERIFY_TOKEN: dict[str, Any] = {
    "login": "test-user",
    "id": 123456,
    "node_id": "MDQ6VXNlcjEyMzQ1Ng==",
    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/test-user",
    "html_url": "https://github.com/test-user",
    "type": "User",
    "name": "Test User",
    "company": "Test Company",
    "blog": "https://test.example.com",
    "location": "Test City",
    "email": "test@example.com",
    "bio": "Test user for E2E testing",
    "public_repos": 10,
    "public_gists": 5,
    "followers": 20,
    "following": 15,
    "created_at": "2020-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z",
}

# Mock response for listing user repositories (GET /user/repos)
GITHUB_LIST_REPOS: list[dict[str, Any]] = [
    {
        "id": 111111,
        "node_id": "R_kgDOBhgHbQ",
        "name": "test-auth-patterns",
        "full_name": "test-user/test-auth-patterns",
        "private": False,
        "owner": {
            "login": "test-user",
            "id": 123456,
            "node_id": "MDQ6VXNlcjEyMzQ1Ng==",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4",
            "type": "User",
        },
        "html_url": "https://github.com/test-user/test-auth-patterns",
        "description": "Test repository with authorization code patterns for policy extraction",
        "fork": False,
        "url": "https://api.github.com/repos/test-user/test-auth-patterns",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-09T00:00:00Z",
        "pushed_at": "2025-01-09T00:00:00Z",
        "size": 128,
        "stargazers_count": 5,
        "watchers_count": 5,
        "language": "Python",
        "default_branch": "main",
        "visibility": "public",
    },
    {
        "id": 222222,
        "node_id": "R_kgDOBhgHbR",
        "name": "application-security-policy-miner",
        "full_name": "test-user/application-security-policy-miner",
        "private": False,
        "owner": {
            "login": "test-user",
            "id": 123456,
            "node_id": "MDQ6VXNlcjEyMzQ1Ng==",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4",
            "type": "User",
        },
        "html_url": "https://github.com/test-user/application-security-policy-miner",
        "description": "Application Security Policy Miner - Extract and analyze security policies from code",
        "fork": False,
        "url": "https://api.github.com/repos/test-user/application-security-policy-miner",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2025-01-09T00:00:00Z",
        "pushed_at": "2025-01-09T00:00:00Z",
        "size": 2048,
        "stargazers_count": 15,
        "watchers_count": 15,
        "language": "Python",
        "default_branch": "main",
        "visibility": "public",
    },
]

# Mock response for repository contents (GET /repos/{owner}/{repo}/contents/{path})
GITHUB_REPO_CONTENTS: list[dict[str, Any]] = [
    {
        "name": "README.md",
        "path": "README.md",
        "sha": "abc123",
        "size": 1024,
        "url": "https://api.github.com/repos/test-user/test-auth-patterns/contents/README.md",
        "html_url": "https://github.com/test-user/test-auth-patterns/blob/main/README.md",
        "git_url": "https://api.github.com/repos/test-user/test-auth-patterns/git/blobs/abc123",
        "download_url": "https://raw.githubusercontent.com/test-user/test-auth-patterns/main/README.md",
        "type": "file",
    },
    {
        "name": "python",
        "path": "python",
        "sha": "def456",
        "size": 0,
        "url": "https://api.github.com/repos/test-user/test-auth-patterns/contents/python",
        "html_url": "https://github.com/test-user/test-auth-patterns/tree/main/python",
        "git_url": "https://api.github.com/repos/test-user/test-auth-patterns/git/trees/def456",
        "download_url": None,
        "type": "dir",
    },
]

# Mock response for file content with authorization patterns
GITHUB_FILE_CONTENT: dict[str, Any] = {
    "name": "flask_decorators.py",
    "path": "python/flask_decorators.py",
    "sha": "ghi789",
    "size": 512,
    "url": "https://api.github.com/repos/test-user/test-auth-patterns/contents/python/flask_decorators.py",
    "html_url": "https://github.com/test-user/test-auth-patterns/blob/main/python/flask_decorators.py",
    "git_url": "https://api.github.com/repos/test-user/test-auth-patterns/git/blobs/ghi789",
    "download_url": "https://raw.githubusercontent.com/test-user/test-auth-patterns/main/python/flask_decorators.py",
    "type": "file",
    "content": "ZnJvbSBmdW5jdG9vbHMgaW1wb3J0IHdyYXBzCmZyb20gZmxhc2sgaW1wb3J0IGFib3J0CgpkZWYgcmVxdWlyZV9yb2xlKHJvbGUpOgogICAgZGVmIGRlY29yYXRvcihmdW5jKToKICAgICAgICBAd3JhcHMoZnVuYykKICAgICAgICBkZWYgd3JhcHBlcigqYXJncywgKiprd2FyZ3MpOgogICAgICAgICAgICBpZiBub3QgaGFzX3JvbGUocm9sZSk6CiAgICAgICAgICAgICAgICBhYm9ydCg0MDMpCiAgICAgICAgICAgIHJldHVybiBmdW5jKCphcmdzLCAqKmt3YXJncykKICAgICAgICByZXR1cm4gd3JhcHBlcgogICAgcmV0dXJuIGRlY29yYXRvcg==",
    "encoding": "base64",
}

# Mock response for webhook creation (POST /repos/{owner}/{repo}/hooks)
GITHUB_CREATE_WEBHOOK: dict[str, Any] = {
    "id": 999999,
    "url": "https://api.github.com/repos/test-user/test-auth-patterns/hooks/999999",
    "test_url": "https://api.github.com/repos/test-user/test-auth-patterns/hooks/999999/test",
    "ping_url": "https://api.github.com/repos/test-user/test-auth-patterns/hooks/999999/pings",
    "name": "web",
    "events": ["push"],
    "active": True,
    "config": {
        "url": "https://example.com/webhook",
        "content_type": "json",
        "insecure_ssl": "0",
    },
    "updated_at": "2025-01-09T00:00:00Z",
    "created_at": "2025-01-09T00:00:00Z",
}
