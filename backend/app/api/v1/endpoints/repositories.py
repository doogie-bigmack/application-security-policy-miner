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
from app.services.evidence_validation_service import EvidenceValidationService
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
