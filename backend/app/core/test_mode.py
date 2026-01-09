"""
Test mode utilities for E2E testing.

This module provides utilities to check if the application is running in TEST_MODE,
which allows E2E tests to run without calling external APIs (GitHub, GitLab, etc.).
"""

import os
from typing import Literal

TestMode = Literal["true", "false"]


def is_test_mode() -> bool:
    """
    Check if the application is running in TEST_MODE.

    Returns:
        bool: True if TEST_MODE environment variable is set to "true", False otherwise.
    """
    return os.getenv("TEST_MODE", "false").lower() == "true"


def get_test_mode() -> TestMode:
    """
    Get the current test mode setting.

    Returns:
        TestMode: "true" if TEST_MODE is enabled, "false" otherwise.
    """
    return "true" if is_test_mode() else "false"
