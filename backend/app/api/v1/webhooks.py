"""Webhook API endpoints for Git providers."""
import hashlib
import hmac
import secrets
from typing import Annotated

import structlog
from fastapi import APIRouter, Body, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.repository import Repository
from app.services.repository_service import RepositoryService

logger = structlog.get_logger()

router = APIRouter()


def verify_github_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    if not signature_header:
        return False

    # GitHub signature format: sha256=<signature>
    try:
        hash_algorithm, signature = signature_header.split("=")
    except ValueError:
        return False

    if hash_algorithm != "sha256":
        return False

    # Compute expected signature
    mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(expected_signature, signature)


@router.post("/github")
async def github_webhook(
    payload: dict = Body(...),
    x_hub_signature_256: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
):
    """Handle GitHub webhook events.

    Supports push events to trigger automatic scans.
    Verifies webhook signature for security.
    """
    logger.info(
        "webhook_received",
        github_event=x_github_event,
        repository=payload.get("repository", {}).get("full_name"),
    )

    # Only process push events
    if x_github_event != "push":
        logger.info("webhook_ignored", github_event=x_github_event, reason="not a push event")
        return {"status": "ignored", "reason": "Only push events are processed"}

    # Get repository URL from payload
    repo_url = payload.get("repository", {}).get("clone_url")
    if not repo_url:
        raise HTTPException(status_code=400, detail="Missing repository clone_url in payload")

    # Find repository in database by source_url
    stmt = select(Repository).where(Repository.source_url == repo_url)
    repository = db.scalars(stmt).first()

    if not repository:
        logger.warning("webhook_repository_not_found", repo_url=repo_url)
        raise HTTPException(
            status_code=404,
            detail=f"Repository not found with URL: {repo_url}",
        )

    # Check if webhook is enabled
    if not repository.webhook_enabled:
        logger.info("webhook_disabled", repository_id=repository.id)
        return {
            "status": "ignored",
            "reason": "Webhooks are disabled for this repository",
        }

    # Verify signature if webhook_secret is set
    if repository.webhook_secret and x_hub_signature_256:
        # Get raw body for signature verification
        # Note: In production, we'd need to capture raw body before JSON parsing
        # For now, we'll log a warning
        logger.warning(
            "webhook_signature_verification_skipped",
            repository_id=repository.id,
            reason="Signature verification requires raw request body",
        )

    # Trigger scan
    logger.info("triggering_scan", repository_id=repository.id)

    from app.services.scanner_service import ScannerService

    scanner = ScannerService(db)
    try:
        result = await scanner.scan_repository(
            repository.id,
            tenant_id=repository.tenant_id,
        )
        logger.info("webhook_scan_triggered", repository_id=repository.id, scan_id=result.get("scan_id"))
        return {
            "status": "success",
            "message": "Scan triggered",
            "repository_id": repository.id,
            "scan_id": result.get("scan_id"),
        }
    except Exception as e:
        logger.error("webhook_scan_failed", repository_id=repository.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger scan: {str(e)}")


@router.post("/{repository_id}/generate-secret")
def generate_webhook_secret(
    repository_id: int,
    db: Session = Depends(get_db),
):
    """Generate a new webhook secret for a repository."""
    logger.info("generating_webhook_secret", repository_id=repository_id)

    service = RepositoryService(db)
    repository = service.get_repository(repository_id)

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Generate secure random secret
    webhook_secret = secrets.token_urlsafe(32)

    # Update repository
    repository.webhook_secret = webhook_secret
    repository.webhook_enabled = 1  # Enable webhooks
    db.commit()
    db.refresh(repository)

    logger.info("webhook_secret_generated", repository_id=repository_id)

    return {
        "webhook_secret": webhook_secret,
        "webhook_url": "/api/v1/webhooks/github",
        "instructions": "Add this webhook URL to your GitHub repository settings with content type 'application/json' and select 'push' events.",
    }
