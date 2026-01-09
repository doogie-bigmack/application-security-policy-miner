"""API v1 router."""
from fastapi import APIRouter

from app.api.v1 import auth, changes, conflicts, scan_progress
from app.api.v1.endpoints import policies, repositories

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(policies.router, prefix="/policies", tags=["policies"])
api_router.include_router(conflicts.router, prefix="/conflicts", tags=["conflicts"])
api_router.include_router(scan_progress.router, prefix="/scan-progress", tags=["scan-progress"])
api_router.include_router(changes.router, prefix="/changes", tags=["changes"])
