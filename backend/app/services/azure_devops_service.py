"""Azure DevOps API integration service."""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AzureDevOpsService:
    """Service for interacting with Azure DevOps API."""

    def __init__(self, access_token: str, organization: str):
        """
        Initialize Azure DevOps service with access token.

        Args:
            access_token: Azure DevOps Personal Access Token (PAT)
            organization: Azure DevOps organization name
        """
        self.access_token = access_token
        self.organization = organization
        self.base_url = f"https://dev.azure.com/{organization}"
        self.api_version = "7.0"
        self.headers = {
            "Authorization": f"Basic {self._encode_pat(access_token)}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _encode_pat(pat: str) -> str:
        """
        Encode PAT for Basic Authentication.

        Azure DevOps uses Basic Auth with empty username and PAT as password.

        Args:
            pat: Personal Access Token

        Returns:
            Base64 encoded credentials
        """
        import base64

        credentials = f":{pat}"
        return base64.b64encode(credentials.encode()).decode()

    async def list_repositories(
        self, project: str | None = None, per_page: int = 100, page: int = 1
    ) -> dict[str, Any]:
        """
        List Git repositories accessible to the authenticated user.

        Args:
            project: Optional project name to filter repositories
            per_page: Number of repositories per page (max 100)
            page: Page number to fetch (1-based)

        Returns:
            Dictionary with repositories list and total count

        Raises:
            httpx.HTTPStatusError: If Azure DevOps API returns an error
        """
        logger.info(
            "Fetching Azure DevOps repositories",
            extra={"organization": self.organization, "project": project, "page": page, "per_page": per_page},
        )

        try:
            async with httpx.AsyncClient() as client:
                # Calculate skip for pagination (Azure DevOps uses skip/top, not page)
                skip = (page - 1) * per_page

                if project:
                    # Get repositories for specific project
                    url = f"{self.base_url}/{project}/_apis/git/repositories"
                else:
                    # Get all repositories across all projects
                    url = f"{self.base_url}/_apis/git/repositories"

                response = await client.get(
                    url,
                    headers=self.headers,
                    params={
                        "api-version": self.api_version,
                        "$top": per_page,
                        "$skip": skip,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                data = response.json()
                repositories = data.get("value", [])
                total_count = data.get("count", len(repositories))

                # Transform to our format
                formatted_repos = [
                    {
                        "id": repo["id"],
                        "name": repo["name"],
                        "full_name": f"{repo['project']['name']}/{repo['name']}",
                        "description": None,  # Azure DevOps doesn't provide repo description in list API
                        "clone_url": repo["remoteUrl"],
                        "ssh_url": repo.get("sshUrl"),
                        "html_url": repo["webUrl"],
                        "private": True,  # Azure DevOps repos are private by default
                        "language": None,  # Not provided in list API
                        "updated_at": None,  # Not provided in list API
                        "default_branch": repo.get("defaultBranch", "refs/heads/main").replace("refs/heads/", ""),
                        "project": repo["project"]["name"],
                        "project_id": repo["project"]["id"],
                    }
                    for repo in repositories
                ]

                logger.info(
                    "Azure DevOps repositories fetched",
                    extra={"count": len(formatted_repos), "total": total_count},
                )

                return {
                    "repositories": formatted_repos,
                    "total": total_count,
                    "page": page,
                    "per_page": per_page,
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "Azure DevOps API error",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to fetch Azure DevOps repositories", extra={"error": str(e)})
            raise

    async def list_projects(self) -> dict[str, Any]:
        """
        List all projects in the organization.

        Returns:
            Dictionary with projects list

        Raises:
            httpx.HTTPStatusError: If Azure DevOps API returns an error
        """
        logger.info("Fetching Azure DevOps projects", extra={"organization": self.organization})

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/_apis/projects",
                    headers=self.headers,
                    params={"api-version": self.api_version},
                    timeout=30.0,
                )
                response.raise_for_status()

                data = response.json()
                projects = data.get("value", [])

                formatted_projects = [
                    {
                        "id": project["id"],
                        "name": project["name"],
                        "description": project.get("description"),
                        "url": project["url"],
                        "state": project.get("state"),
                        "visibility": project.get("visibility", "private"),
                    }
                    for project in projects
                ]

                logger.info("Azure DevOps projects fetched", extra={"count": len(formatted_projects)})

                return {
                    "projects": formatted_projects,
                    "total": len(formatted_projects),
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "Azure DevOps API error",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to fetch Azure DevOps projects", extra={"error": str(e)})
            raise

    async def verify_access(self) -> dict[str, Any]:
        """
        Verify the access token is valid by fetching user profile.

        Returns:
            Dictionary with user information

        Raises:
            httpx.HTTPStatusError: If token is invalid
        """
        logger.info("Verifying Azure DevOps access token")

        try:
            async with httpx.AsyncClient() as client:
                # Use Visual Studio Services API for user profile
                response = await client.get(
                    "https://app.vssps.visualstudio.com/_apis/profile/profiles/me",
                    headers=self.headers,
                    params={"api-version": self.api_version},
                    timeout=10.0,
                )
                response.raise_for_status()

                user_data = response.json()
                logger.info("Azure DevOps access token verified", extra={"user": user_data.get("displayName")})

                return {
                    "id": user_data.get("id"),
                    "name": user_data.get("displayName"),
                    "email": user_data.get("emailAddress"),
                    "organization": self.organization,
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "Azure DevOps token verification failed",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise
        except Exception as e:
            logger.error("Failed to verify Azure DevOps token", extra={"error": str(e)})
            raise
