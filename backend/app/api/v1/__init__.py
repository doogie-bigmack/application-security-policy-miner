"""API v1 router."""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    auto_approval,
    changes,
    conflicts,
    provisioning,
    scan_progress,
    security_audit,
    webhooks,
)
from app.api.v1.endpoints import (
    applications,
    audit_logs,
    code_advisories,
    organizations,
    policies,
    repositories,
    risk,
    secrets,
)

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(policies.router, prefix="/policies", tags=["policies"])
api_router.include_router(conflicts.router, prefix="/conflicts", tags=["conflicts"])
api_router.include_router(scan_progress.router, prefix="/scan-progress", tags=["scan-progress"])
api_router.include_router(changes.router, prefix="/changes", tags=["changes"])
api_router.include_router(secrets.router, prefix="/secrets", tags=["secrets"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(security_audit.router, prefix="/security", tags=["security"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(provisioning.router, prefix="/provisioning", tags=["provisioning"])
api_router.include_router(code_advisories.router, prefix="/code-advisories", tags=["code-advisories"])
api_router.include_router(auto_approval.router, prefix="/auto-approval", tags=["auto-approval"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
