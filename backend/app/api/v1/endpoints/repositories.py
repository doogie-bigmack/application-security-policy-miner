"""Repository API endpoints."""
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_tenant_id
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUpdate,
)
from app.services.azure_devops_service import AzureDevOpsService
from app.services.bitbucket_service import BitbucketService
from app.services.evidence_validation_service import EvidenceValidationService
from app.services.github_service import GitHubService
from app.services.gitlab_service import GitLabService
from app.services.repository_service import RepositoryService

logger = structlog.get_logger()

router = APIRouter()


@router.post("/", response_model=RepositoryResponse, status_code=201)
def create_repository(
    repository: RepositoryCreate,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
):
    """Create a new repository."""
    logger.info("api_create_repository", name=repository.name, tenant_id=tenant_id)

    service = RepositoryService(db)
    created_repo = service.create_repository(repository, tenant_id=tenant_id)

    # Verify the connection based on repository type
    if created_repo.repository_type.value == "git" and created_repo.source_url:
        service.verify_git_connection(created_repo)
    elif created_repo.repository_type.value == "database" and created_repo.connection_config:
        service.verify_database_connection(created_repo)

    return created_repo


@router.get("/", response_model=RepositoryListResponse)
def list_repositories(
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all repositories."""
    logger.info("api_list_repositories", skip=skip, limit=limit, tenant_id=tenant_id)

    service = RepositoryService(db)
    repositories, total = service.list_repositories(skip=skip, limit=limit, tenant_id=tenant_id)

    return RepositoryListResponse(repositories=repositories, total=total)


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(
    repository_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
):
    """Get a repository by ID."""
    logger.info("api_get_repository", repository_id=repository_id, tenant_id=tenant_id)

    service = RepositoryService(db)
    repository = service.get_repository(repository_id, tenant_id=tenant_id)

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.put("/{repository_id}", response_model=RepositoryResponse)
def update_repository(
    repository_id: int,
    repository_data: RepositoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
):
    """Update a repository."""
    logger.info("api_update_repository", repository_id=repository_id, tenant_id=tenant_id)

    service = RepositoryService(db)
    repository = service.update_repository(repository_id, repository_data, tenant_id=tenant_id)

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.delete("/{repository_id}", status_code=204)
def delete_repository(
    repository_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
):
    """Delete a repository."""
    logger.info("api_delete_repository", repository_id=repository_id, tenant_id=tenant_id)

    service = RepositoryService(db)
    deleted = service.delete_repository(repository_id, tenant_id=tenant_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Repository not found")

    return None


@router.get("/{repository_id}/scans")
def get_repository_scans(
    repository_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
):
    """Get scan history for a repository."""
    logger.info("api_get_repository_scans", repository_id=repository_id, tenant_id=tenant_id)

    from app.models.scan_progress import ScanProgress

    # Verify repository exists
    service = RepositoryService(db)
    repository = service.get_repository(repository_id, tenant_id=tenant_id)

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get scan history
    scans = (
        db.query(ScanProgress)
        .filter(ScanProgress.repository_id == repository_id)
        .order_by(ScanProgress.created_at.desc())
        .limit(20)
        .all()
    )

    return scans


@router.post("/{repository_id}/scan")
async def scan_repository(
    repository_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
    incremental: bool = Query(False, description="Perform incremental scan (only changed files)"),
):
    """Trigger a scan for a repository.

    This will clone the repository, analyze the code, and extract authorization policies.
    If incremental=true, only files changed since the last scan will be processed.
    """
    scan_type = "incremental" if incremental else "full"
    logger.info("api_scan_repository", repository_id=repository_id, tenant_id=tenant_id, scan_type=scan_type)

    from app.services.scanner_service import ScannerService

    # Verify repository exists
    service = RepositoryService(db)
    repository = service.get_repository(repository_id, tenant_id=tenant_id)

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Only scan git repositories for now
    if repository.repository_type.value != "git":
        raise HTTPException(
            status_code=400,
            detail="Only Git repositories are supported for scanning currently",
        )

    # Start scan
    scanner = ScannerService(db)
    try:
        result = await scanner.scan_repository(repository_id, tenant_id=tenant_id, incremental=incremental)
        return result
    except Exception as e:
        logger.error("scan_failed", repository_id=repository_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.post("/{repository_id}/validate-evidence")
async def validate_repository_evidence(
    repository_id: int,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: Annotated[str | None, Depends(get_tenant_id)],
) -> dict:
    """Validate all evidence items for all policies in a repository.

    This prevents AI hallucination by verifying that evidence matches source files.

    Args:
        repository_id: Repository ID
        db: Database session
        tenant_id: Tenant ID

    Returns:
        Validation summary with statistics
    """
    logger.info("api_validate_repository_evidence", repository_id=repository_id, tenant_id=tenant_id)

    # Verify repository exists
    service = RepositoryService(db)
    repository = service.get_repository(repository_id, tenant_id=tenant_id)

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get repository path
    repo_path = Path("/tmp/policy_miner_repos") / str(repository_id)

    if not repo_path.exists():
        raise HTTPException(
            status_code=400,
            detail="Repository not found on disk. Please scan the repository first.",
        )

    # Validate all evidence
    validation_service = EvidenceValidationService(db)
    result = validation_service.validate_repository_evidence(repository_id, str(repo_path))

    logger.info(
        "repository_evidence_validated",
        repository_id=repository_id,
        total_evidence=result.get("total_evidence"),
        valid=result.get("valid"),
        invalid=result.get("invalid"),
    )

    return result


@router.post("/github/list")
async def list_github_repositories(
    access_token: str = Query(..., description="GitHub personal access token"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Results per page"),
) -> dict:
    """
    List GitHub repositories accessible to the user.

    Requires a GitHub personal access token with 'repo' scope.

    Args:
        access_token: GitHub personal access token
        page: Page number (default: 1)
        per_page: Results per page (default: 100, max: 100)

    Returns:
        List of GitHub repositories with metadata
    """
    logger.info("api_list_github_repositories", page=page, per_page=per_page)

    try:
        github_service = GitHubService(access_token)
        result = await github_service.list_repositories(per_page=per_page, page=page)

        logger.info("github_repositories_listed", count=result.get("total"))
        return result

    except Exception as e:
        logger.error("failed_to_list_github_repositories", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch GitHub repositories: {str(e)}",
        )


@router.post("/github/verify")
async def verify_github_token(
    access_token: str = Query(..., description="GitHub personal access token"),
) -> dict:
    """
    Verify GitHub access token and get user information.

    Args:
        access_token: GitHub personal access token

    Returns:
        User information if token is valid
    """
    logger.info("api_verify_github_token")

    try:
        github_service = GitHubService(access_token)
        user_info = await github_service.verify_access()

        logger.info("github_token_verified", user=user_info.get("login"))
        return user_info

    except Exception as e:
        logger.error("github_token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid GitHub access token",
        )


@router.post("/gitlab/list")
async def list_gitlab_repositories(
    access_token: str = Query(..., description="GitLab personal access token"),
    base_url: str = Query("https://gitlab.com", description="GitLab instance URL"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Results per page"),
) -> dict:
    """
    List GitLab projects accessible to the user.

    Requires a GitLab personal access token with 'api' or 'read_api' scope.

    Args:
        access_token: GitLab personal access token
        base_url: GitLab instance URL (default: https://gitlab.com)
        page: Page number (default: 1)
        per_page: Results per page (default: 100, max: 100)

    Returns:
        List of GitLab projects with metadata
    """
    logger.info("api_list_gitlab_repositories", page=page, per_page=per_page, base_url=base_url)

    try:
        gitlab_service = GitLabService(access_token, base_url)
        result = await gitlab_service.list_repositories(per_page=per_page, page=page)

        logger.info("gitlab_repositories_listed", count=result.get("total"))
        return result

    except Exception as e:
        logger.error("failed_to_list_gitlab_repositories", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch GitLab repositories: {str(e)}",
        )


@router.post("/gitlab/verify")
async def verify_gitlab_token(
    access_token: str = Query(..., description="GitLab personal access token"),
    base_url: str = Query("https://gitlab.com", description="GitLab instance URL"),
) -> dict:
    """
    Verify GitLab access token and get user information.

    Args:
        access_token: GitLab personal access token
        base_url: GitLab instance URL (default: https://gitlab.com)

    Returns:
        User information if token is valid
    """
    logger.info("api_verify_gitlab_token", base_url=base_url)

    try:
        gitlab_service = GitLabService(access_token, base_url)
        user_info = await gitlab_service.verify_access()

        logger.info("gitlab_token_verified", user=user_info.get("username"))
        return user_info

    except Exception as e:
        logger.error("gitlab_token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid GitLab access token",
        )


@router.post("/bitbucket/list")
async def list_bitbucket_repositories(
    username: str = Query(..., description="Bitbucket username or email"),
    app_password: str = Query(..., description="Bitbucket App Password"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Results per page"),
) -> dict:
    """
    List Bitbucket repositories accessible to the user.

    Requires a Bitbucket App Password (not your account password).
    Create one at: https://bitbucket.org/account/settings/app-passwords/

    Args:
        username: Bitbucket username or email
        app_password: Bitbucket App Password
        page: Page number (default: 1)
        per_page: Results per page (default: 100, max: 100)

    Returns:
        List of Bitbucket repositories with metadata
    """
    logger.info("api_list_bitbucket_repositories", page=page, per_page=per_page, username=username)

    try:
        bitbucket_service = BitbucketService(username, app_password)
        result = await bitbucket_service.list_repositories(per_page=per_page, page=page)

        logger.info("bitbucket_repositories_listed", count=result.get("total"))
        return result

    except Exception as e:
        logger.error("failed_to_list_bitbucket_repositories", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch Bitbucket repositories: {str(e)}",
        )


@router.post("/bitbucket/verify")
async def verify_bitbucket_credentials(
    username: str = Query(..., description="Bitbucket username or email"),
    app_password: str = Query(..., description="Bitbucket App Password"),
) -> dict:
    """
    Verify Bitbucket credentials and get user information.

    Args:
        username: Bitbucket username or email
        app_password: Bitbucket App Password

    Returns:
        User information if credentials are valid
    """
    logger.info("api_verify_bitbucket_credentials", username=username)

    try:
        bitbucket_service = BitbucketService(username, app_password)
        user_info = await bitbucket_service.verify_access()

        logger.info("bitbucket_credentials_verified", user=user_info.get("username"))
        return user_info

    except Exception as e:
        logger.error("bitbucket_credentials_verification_failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid Bitbucket credentials",
        )


@router.post("/azure-devops/list")
async def list_azure_devops_repositories(
    access_token: str = Query(..., description="Azure DevOps Personal Access Token (PAT)"),
    organization: str = Query(..., description="Azure DevOps organization name"),
    project: str | None = Query(None, description="Optional project name to filter repositories"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Results per page"),
) -> dict:
    """
    List Azure DevOps repositories accessible to the user.

    Requires an Azure DevOps Personal Access Token (PAT) with 'Code (Read)' scope.
    Create one at: https://dev.azure.com/{organization}/_usersSettings/tokens

    Args:
        access_token: Azure DevOps Personal Access Token
        organization: Azure DevOps organization name
        project: Optional project name to filter repositories
        page: Page number (default: 1)
        per_page: Results per page (default: 100, max: 100)

    Returns:
        List of Azure DevOps repositories with metadata
    """
    logger.info(
        "api_list_azure_devops_repositories",
        page=page,
        per_page=per_page,
        organization=organization,
        project=project,
    )

    try:
        azure_service = AzureDevOpsService(access_token, organization)
        result = await azure_service.list_repositories(project=project, per_page=per_page, page=page)

        logger.info("azure_devops_repositories_listed", count=result.get("total"))
        return result

    except Exception as e:
        logger.error("failed_to_list_azure_devops_repositories", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch Azure DevOps repositories: {str(e)}",
        )


@router.post("/azure-devops/verify")
async def verify_azure_devops_token(
    access_token: str = Query(..., description="Azure DevOps Personal Access Token (PAT)"),
    organization: str = Query(..., description="Azure DevOps organization name"),
) -> dict:
    """
    Verify Azure DevOps access token and get user information.

    Args:
        access_token: Azure DevOps Personal Access Token
        organization: Azure DevOps organization name

    Returns:
        User information if token is valid
    """
    logger.info("api_verify_azure_devops_token", organization=organization)

    try:
        azure_service = AzureDevOpsService(access_token, organization)
        user_info = await azure_service.verify_access()

        logger.info("azure_devops_token_verified", user=user_info.get("name"))
        return user_info

    except Exception as e:
        logger.error("azure_devops_token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid Azure DevOps access token",
        )


@router.post("/azure-devops/projects")
async def list_azure_devops_projects(
    access_token: str = Query(..., description="Azure DevOps Personal Access Token (PAT)"),
    organization: str = Query(..., description="Azure DevOps organization name"),
) -> dict:
    """
    List all projects in an Azure DevOps organization.

    Args:
        access_token: Azure DevOps Personal Access Token
        organization: Azure DevOps organization name

    Returns:
        List of projects in the organization
    """
    logger.info("api_list_azure_devops_projects", organization=organization)

    try:
        azure_service = AzureDevOpsService(access_token, organization)
        result = await azure_service.list_projects()

        logger.info("azure_devops_projects_listed", count=result.get("total"))
        return result

    except Exception as e:
        logger.error("failed_to_list_azure_devops_projects", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch Azure DevOps projects: {str(e)}",
        )
