"""GitHub API integration service."""
import logging
from typing import Any

import httpx

from app.core.test_mode import is_test_mode
from tests.fixtures.github_responses import (
    GITHUB_LIST_REPOS,
    GITHUB_VERIFY_TOKEN,
)

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, access_token: str):
        """Initialize GitHub service with access token."""
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def list_repositories(self, per_page: int = 100, page: int = 1) -> dict[str, Any]:
        """
        List repositories accessible to the authenticated user.

        Args:
            per_page: Number of repositories per page (max 100)
            page: Page number to fetch

        Returns:
            Dictionary with repositories list and total count

        Raises:
            httpx.HTTPStatusError: If GitHub API returns an error
        """
        logger.info("Fetching GitHub repositories", extra={"page": page, "per_page": per_page})

        # Return mock data in test mode
        if is_test_mode():
            logger.info("TEST_MODE: Returning mock GitHub repositories")
            formatted_repos = [
                {
                    "id": repo["id"],
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "clone_url": repo["html_url"] + ".git",
                    "ssh_url": f"git@github.com:{repo['full_name']}.git",
                    "html_url": repo["html_url"],
                    "private": repo["private"],
                    "language": repo.get("language"),
                    "updated_at": repo["updated_at"],
                    "default_branch": repo["default_branch"],
                }
                for repo in GITHUB_LIST_REPOS
            ]
            return {
                "repositories": formatted_repos,
                "total": len(formatted_repos),
                "page": page,
                "per_page": per_page,
            }

        try:
            async with httpx.AsyncClient() as client:
                # Get user's repositories (owned + collaborated)
                response = await client.get(
                    f"{self.BASE_URL}/user/repos",
                    headers=self.headers,
                    params={
                        "per_page": per_page,
                        "page": page,
                        "sort": "updated",
                        "affiliation": "owner,collaborator,organization_member",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                repositories = response.json()

                # Transform to our format
                formatted_repos = [
                    {
                        "id": repo["id"],
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo.get("description"),
                        "clone_url": repo["clone_url"],
                        "ssh_url": repo["ssh_url"],
                        "html_url": repo["html_url"],
                        "private": repo["private"],
                        "language": repo.get("language"),
                        "updated_at": repo["updated_at"],
                        "default_branch": repo["default_branch"],
                    }
                    for repo in repositories
                ]

                logger.info("GitHub repositories fetched", extra={"count": len(formatted_repos)})

                return {
                    "repositories": formatted_repos,
                    "total": len(formatted_repos),  # Note: GitHub doesn't provide total count easily
                    "page": page,
                    "per_page": per_page,
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "GitHub API error",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to fetch GitHub repositories", extra={"error": str(e)})
            raise

    async def verify_access(self) -> dict[str, Any]:
        """
        Verify the access token is valid by fetching user info.

        Returns:
            Dictionary with user information

        Raises:
            httpx.HTTPStatusError: If token is invalid
        """
        logger.info("Verifying GitHub access token")

        # Return mock data in test mode
        if is_test_mode():
            logger.info("TEST_MODE: Returning mock GitHub user")
            return {
                "login": GITHUB_VERIFY_TOKEN["login"],
                "name": GITHUB_VERIFY_TOKEN.get("name"),
                "email": GITHUB_VERIFY_TOKEN.get("email"),
                "avatar_url": GITHUB_VERIFY_TOKEN.get("avatar_url"),
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/user",
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()

                user_data = response.json()
                logger.info("GitHub access token verified", extra={"user": user_data.get("login")})

                return {
                    "login": user_data["login"],
                    "name": user_data.get("name"),
                    "email": user_data.get("email"),
                    "avatar_url": user_data.get("avatar_url"),
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "GitHub token verification failed",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to verify GitHub token", extra={"error": str(e)})
            raise
