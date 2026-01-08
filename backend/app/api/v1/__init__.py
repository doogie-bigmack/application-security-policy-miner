"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import policies, repositories

api_router = APIRouter()

# Include routers
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(policies.router, prefix="/policies", tags=["policies"])
