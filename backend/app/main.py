"""
Main FastAPI application entry point.
"""
import time

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.metrics import get_metrics, record_api_request

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

app = FastAPI(
    title="Policy Miner API",
    description="Application Security Policy Mining and Analysis",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to track API request metrics."""
    # Skip metrics for the /metrics endpoint itself
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Record metrics
    record_api_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        duration=duration
    )

    return response


# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("health_check_called")
    return {"status": "healthy", "service": "policy-miner-api"}


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    """
    logger.info("metrics_endpoint_called")
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain")


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("application_starting", version="0.1.0")

    # Create database tables
    from app.core.database import engine
    from app.models.repository import Base

    logger.info("creating_database_tables")
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("application_shutting_down")
