"""
E2E Test Scenarios Package

This package contains reusable test scenarios that can be composed to create
end-to-end test flows for the Policy Miner application.

Available scenario modules:
- repository_crud: Repository management scenarios (add, scan, delete)
- policy_viewing: Policy viewing and filtering scenarios (coming soon)
- provisioning_flow: PBAC provider and policy provisioning scenarios (coming soon)
"""

from e2e.scenarios.repository_crud import (
    add_github_repository,
    delete_repository,
    scan_repository,
)

__all__ = [
    "add_github_repository",
    "delete_repository",
    "scan_repository",
]
