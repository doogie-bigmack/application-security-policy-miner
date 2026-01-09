# Test Fixtures for E2E Testing

This directory contains mock responses for external API services used during E2E testing.

## Overview

When `TEST_MODE=true` environment variable is set, the application services will return these mock responses instead of calling real external APIs. This allows E2E tests to run without requiring valid API tokens or network connectivity to external services.

## Available Fixtures

### Git Repository Providers

- **github_responses.py**: Mock responses for GitHub API
  - `GITHUB_VERIFY_TOKEN`: User verification response
  - `GITHUB_LIST_REPOS`: Repository list response
  - `GITHUB_REPO_CONTENTS`: Repository contents
  - `GITHUB_FILE_CONTENT`: File content with auth patterns
  - `GITHUB_CREATE_WEBHOOK`: Webhook creation response

- **gitlab_responses.py**: Mock responses for GitLab API
  - `GITLAB_VERIFY_TOKEN`: User verification response
  - `GITLAB_LIST_PROJECTS`: Project list response
  - `GITLAB_REPO_TREE`: Repository tree
  - `GITLAB_FILE_CONTENT`: File content with auth patterns
  - `GITLAB_CREATE_WEBHOOK`: Webhook creation response

- **bitbucket_responses.py**: Mock responses for Bitbucket API
  - `BITBUCKET_VERIFY_TOKEN`: User verification response
  - `BITBUCKET_LIST_REPOS`: Repository list response
  - `BITBUCKET_FILE_CONTENT`: File content with auth patterns
  - `BITBUCKET_CREATE_WEBHOOK`: Webhook creation response

- **azure_devops_responses.py**: Mock responses for Azure DevOps API
  - `AZURE_DEVOPS_VERIFY_TOKEN`: Profile verification response
  - `AZURE_DEVOPS_LIST_REPOS`: Repository list response
  - `AZURE_DEVOPS_FILE_CONTENT`: File content with auth patterns
  - `AZURE_DEVOPS_CREATE_WEBHOOK`: Webhook creation response

### PBAC Providers

- **pbac_responses.py**: Mock responses for PBAC provider APIs
  - OPA (Open Policy Agent): Health check, policy upload, list, evaluation
  - AWS Verified Permissions: Policy store creation, policy creation, list
  - Axiomatics: Policy upload, list, evaluation
  - PlainID: Policy upload, list, authorization

### Scanner Service

- **scanner_responses.py**: Mock scan results
  - `MOCK_SCAN_RESULT`: Complete scan result with extracted policies
  - `MOCK_EXTRACTED_POLICIES`: 5 sample extracted policies from various languages
  - `MOCK_INCREMENTAL_SCAN_RESULT`: Faster incremental scan result
  - `MOCK_SCAN_WITH_ERRORS`: Scan with partial errors

## Usage

### Enabling Test Mode

Set the `TEST_MODE` environment variable:

```bash
export TEST_MODE=true
# or
TEST_MODE=true python -m uvicorn app.main:app
```

### In Service Code

Services check test mode using `app.core.test_mode.is_test_mode()`:

```python
from app.core.test_mode import is_test_mode
from tests.fixtures.github_responses import GITHUB_LIST_REPOS

async def list_repositories(self):
    if is_test_mode():
        logger.info("TEST_MODE: Returning mock repositories")
        return GITHUB_LIST_REPOS

    # Real API call
    async with httpx.AsyncClient() as client:
        response = await client.get(...)
```

## Services with Test Mode Support

✅ **Implemented:**
- `github_service.py`: list_repositories(), verify_access()
- `gitlab_service.py`: list_repositories(), verify_access()

⏳ **To be implemented:**
- `bitbucket_service.py`: list_repositories(), verify_access()
- `azure_devops_service.py`: list_repositories(), verify_access()
- `scanner_service.py`: scan_repository()
- `provisioning_service.py`: provision_policy()

## Test Configuration

See `backend/.env.test` for the complete test environment configuration including:
- TEST_MODE=true
- Test database configuration
- Mock service endpoints

## Adding New Fixtures

When adding new mock responses:

1. Match the structure of real API responses exactly
2. Include all fields that the application code expects
3. Use realistic data (dates, IDs, URLs)
4. Add docstrings explaining the fixture purpose
5. Update this README with the new fixture

## Notes

- Mock responses are designed to match real API response structures
- Authorization patterns in file contents are realistic examples used for policy extraction
- Test data uses the test-user account and doogie-bigmack organization
- No real API calls are made when TEST_MODE=true
