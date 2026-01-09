"""GitLab API integration service."""
import logging
from typing import Any

import httpx

from app.core.test_mode import is_test_mode
from tests.fixtures.gitlab_responses import (
    GITLAB_LIST_PROJECTS,
    GITLAB_VERIFY_TOKEN,
)

logger = logging.getLogger(__name__)


class GitLabService:
    """Service for interacting with GitLab API."""

    def __init__(self, access_token: str, base_url: str = "https://gitlab.com"):
        """
        Initialize GitLab service with access token.

        Args:
            access_token: GitLab Personal Access Token
            base_url: GitLab instance URL (default: https://gitlab.com for GitLab.com)
        """
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v4"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def list_repositories(self, per_page: int = 100, page: int = 1) -> dict[str, Any]:
        """
        List projects (repositories) accessible to the authenticated user.

        Args:
            per_page: Number of projects per page (max 100)
            page: Page number to fetch

        Returns:
            Dictionary with projects list and total count

        Raises:
            httpx.HTTPStatusError: If GitLab API returns an error
        """
        logger.info("Fetching GitLab projects", extra={"page": page, "per_page": per_page})

        # Return mock data in test mode
        if is_test_mode():
            logger.info("TEST_MODE: Returning mock GitLab projects")
            formatted_repos = [
                {
                    "id": project["id"],
                    "name": project["name"],
                    "full_name": project["path_with_namespace"],
                    "description": project.get("description"),
                    "clone_url": project["web_url"] + ".git",
                    "ssh_url": project["web_url"].replace("https://gitlab.com", "git@gitlab.com:") + ".git",
                    "html_url": project["web_url"],
                    "private": project["visibility"] != "public",
                    "language": None,
                    "updated_at": project["last_activity_at"],
                    "default_branch": project.get("default_branch", "main"),
                    "visibility": project["visibility"],
                    "namespace": project["path_with_namespace"].split("/")[0],
                }
                for project in GITLAB_LIST_PROJECTS
            ]
            return {
                "repositories": formatted_repos,
                "total": len(formatted_repos),
                "page": page,
                "per_page": per_page,
            }

        try:
            async with httpx.AsyncClient() as client:
                # Get user's projects (owned + member)
                response = await client.get(
                    f"{self.api_url}/projects",
                    headers=self.headers,
                    params={
                        "per_page": per_page,
                        "page": page,
                        "order_by": "last_activity_at",
                        "sort": "desc",
                        "membership": "true",  # Only projects user is a member of
                        "simple": "false",  # Get full project details
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                projects = response.json()

                # Get total count from headers
                total_count = int(response.headers.get("X-Total", len(projects)))

                # Transform to our format
                formatted_repos = [
                    {
                        "id": project["id"],
                        "name": project["name"],
                        "full_name": project["path_with_namespace"],
                        "description": project.get("description"),
                        "clone_url": project["http_url_to_repo"],
                        "ssh_url": project["ssh_url_to_repo"],
                        "html_url": project["web_url"],
                        "private": project["visibility"] != "public",
                        "language": None,  # GitLab doesn't provide primary language in list API
                        "updated_at": project["last_activity_at"],
                        "default_branch": project.get("default_branch", "main"),
                        "visibility": project["visibility"],
                        "namespace": project["namespace"]["full_path"],
                    }
                    for project in projects
                ]

                logger.info("GitLab projects fetched", extra={"count": len(formatted_repos), "total": total_count})

                return {
                    "repositories": formatted_repos,
                    "total": total_count,
                    "page": page,
                    "per_page": per_page,
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "GitLab API error",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to fetch GitLab projects", extra={"error": str(e)})
            raise

    async def verify_access(self) -> dict[str, Any]:
        """
        Verify the access token is valid by fetching user info.

        Returns:
            Dictionary with user information

        Raises:
            httpx.HTTPStatusError: If token is invalid
        """
        logger.info("Verifying GitLab access token")

        # Return mock data in test mode
        if is_test_mode():
            logger.info("TEST_MODE: Returning mock GitLab user")
            return {
                "username": GITLAB_VERIFY_TOKEN["username"],
                "name": GITLAB_VERIFY_TOKEN.get("name"),
                "email": GITLAB_VERIFY_TOKEN.get("email"),
                "avatar_url": GITLAB_VERIFY_TOKEN.get("avatar_url"),
                "instance_url": self.base_url,
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/user",
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()

                user_data = response.json()
                logger.info("GitLab access token verified", extra={"user": user_data.get("username")})

                return {
                    "username": user_data["username"],
                    "name": user_data.get("name"),
                    "email": user_data.get("email"),
                    "avatar_url": user_data.get("avatar_url"),
                    "instance_url": self.base_url,
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "GitLab token verification failed",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to verify GitLab token", extra={"error": str(e)})
            raise
