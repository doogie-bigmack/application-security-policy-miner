"""Security audit API routes."""

import logging

from fastapi import APIRouter

from app.services.security_audit_service import security_audit_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/audit")
def get_security_audit():
    """
    Get security audit report showing encryption status.

    Returns comprehensive audit of:
    - Database encryption (at rest and in transit)
    - Redis encryption
    - Object storage (MinIO/S3) encryption
    - Secrets encryption
    - API encryption (HTTPS/TLS)
    """
    logger.info("Generating security audit report")
    audit_results = security_audit_service.audit_encryption()
    return audit_results
