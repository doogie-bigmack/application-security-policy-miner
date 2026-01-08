"""Repository API endpoints."""
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUpdate,
)
from app.services.repository_service import RepositoryService

logger = structlog.get_logger()

router = APIRouter()


@router.post("/", response_model=RepositoryResponse, status_code=201)
def create_repository(
    repository: RepositoryCreate,
    db: Session = Depends(get_db),
):
    """Create a new repository."""
    logger.info("api_create_repository", name=repository.name)

    service = RepositoryService(db)
    created_repo = service.create_repository(repository)

    # Verify the connection based on repository type
    if created_repo.repository_type.value == "git" and created_repo.source_url:
        service.verify_git_connection(created_repo)
    elif created_repo.repository_type.value == "database" and created_repo.connection_config:
        service.verify_database_connection(created_repo)

    return created_repo


@router.get("/", response_model=RepositoryListResponse)
def list_repositories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    """List all repositories."""
    logger.info("api_list_repositories", skip=skip, limit=limit, tenant_id=tenant_id)

    service = RepositoryService(db)
    repositories, total = service.list_repositories(skip=skip, limit=limit, tenant_id=tenant_id)

    return RepositoryListResponse(repositories=repositories, total=total)


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(
    repository_id: int,
    db: Session = Depends(get_db),
):
    """Get a repository by ID."""
    logger.info("api_get_repository", repository_id=repository_id)

    service = RepositoryService(db)
    repository = service.get_repository(repository_id)

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.put("/{repository_id}", response_model=RepositoryResponse)
def update_repository(
    repository_id: int,
    repository_data: RepositoryUpdate,
    db: Session = Depends(get_db),
):
    """Update a repository."""
    logger.info("api_update_repository", repository_id=repository_id)

    service = RepositoryService(db)
    repository = service.update_repository(repository_id, repository_data)

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.delete("/{repository_id}", status_code=204)
def delete_repository(
    repository_id: int,
    db: Session = Depends(get_db),
):
    """Delete a repository."""
    logger.info("api_delete_repository", repository_id=repository_id)

    service = RepositoryService(db)
    deleted = service.delete_repository(repository_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Repository not found")

    return None


@router.post("/{repository_id}/scan")
async def scan_repository(
    repository_id: int,
    db: Session = Depends(get_db),
):
    """Trigger a scan for a repository.

    This will clone the repository, analyze the code, and extract authorization policies.
    """
    logger.info("api_scan_repository", repository_id=repository_id)

    from app.services.scanner_service import ScannerService

    # Verify repository exists
    service = RepositoryService(db)
    repository = service.get_repository(repository_id)

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
        result = await scanner.scan_repository(repository_id)
        return result
    except Exception as e:
        logger.error("scan_failed", repository_id=repository_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")
