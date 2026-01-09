"""Bitbucket API integration service."""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BitbucketService:
    """Service for interacting with Bitbucket API."""

    BASE_URL = "https://api.bitbucket.org/2.0"

    def __init__(self, username: str, app_password: str):
        """
        Initialize Bitbucket service with app password.

        Args:
            username: Bitbucket username or email
            app_password: Bitbucket App Password (not account password)
        """
        self.username = username
        self.app_password = app_password
        self.auth = (username, app_password)

    async def list_repositories(self, per_page: int = 100, page: int = 1) -> dict[str, Any]:
        """
        List repositories accessible to the authenticated user.

        Args:
            per_page: Number of repositories per page (max 100)
            page: Page number to fetch

        Returns:
            Dictionary with repositories list and total count

        Raises:
            httpx.HTTPStatusError: If Bitbucket API returns an error
        """
        logger.info("Fetching Bitbucket repositories", extra={"page": page, "per_page": per_page})

        try:
            async with httpx.AsyncClient() as client:
                # Get user's repositories
                response = await client.get(
                    f"{self.BASE_URL}/repositories/{self.username}",
                    auth=self.auth,
                    params={
                        "pagelen": per_page,
                        "page": page,
                        "sort": "-updated_on",  # Most recently updated first
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                data = response.json()
                repositories = data.get("values", [])
                total_count = data.get("size", len(repositories))

                # Transform to our format
                formatted_repos = [
                    {
                        "id": repo["uuid"],
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo.get("description"),
                        "clone_url": next(
                            (link["href"] for link in repo["links"]["clone"] if link["name"] == "https"),
                            None,
                        ),
                        "ssh_url": next(
                            (link["href"] for link in repo["links"]["clone"] if link["name"] == "ssh"),
                            None,
                        ),
                        "html_url": repo["links"]["html"]["href"],
                        "private": repo["is_private"],
                        "language": repo.get("language"),
                        "updated_at": repo["updated_on"],
                        "default_branch": repo.get("mainbranch", {}).get("name", "main"),
                        "workspace": repo["workspace"]["slug"],
                    }
                    for repo in repositories
                ]

                logger.info("Bitbucket repositories fetched", extra={"count": len(formatted_repos), "total": total_count})

                return {
                    "repositories": formatted_repos,
                    "total": total_count,
                    "page": page,
                    "per_page": per_page,
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "Bitbucket API error",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to fetch Bitbucket repositories", extra={"error": str(e)})
            raise

    async def verify_access(self) -> dict[str, Any]:
        """
        Verify the credentials are valid by fetching user info.

        Returns:
            Dictionary with user information

        Raises:
            httpx.HTTPStatusError: If credentials are invalid
        """
        logger.info("Verifying Bitbucket access")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/user",
                    auth=self.auth,
                    timeout=10.0,
                )
                response.raise_for_status()

                user_data = response.json()
                logger.info("Bitbucket access verified", extra={"user": user_data.get("username")})

                return {
                    "username": user_data["username"],
                    "display_name": user_data.get("display_name"),
                    "uuid": user_data["uuid"],
                    "avatar_url": user_data.get("links", {}).get("avatar", {}).get("href"),
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "Bitbucket verification failed",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to verify Bitbucket credentials", extra={"error": str(e)})
            raise
