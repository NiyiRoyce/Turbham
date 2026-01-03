"""Health check endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import asyncio
import logging
from typing import Dict

from app.schemas.response import HealthResponse
from app.dependencies import (
    get_llm_router,
    get_memory_manager,
    get_orchestration_router,
)
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

HEALTHCHECK_TIMEOUT = 2.0  # seconds


async def _with_timeout(coro, name: str):
    """
    Run a health check with a timeout to prevent blocking.
    """
    try:
        return await asyncio.wait_for(coro, timeout=HEALTHCHECK_TIMEOUT)
    except asyncio.TimeoutError:
        raise RuntimeError(f"{name} health check timed out")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Lightweight health check for uptime monitoring",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """
    Basic uptime check.
    No external dependencies are verified.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get(
    "/health/detailed",
    response_model=HealthResponse,
    summary="Detailed health check",
    description="Verify health of all internal system components",
    tags=["Health"],
)
async def detailed_health_check(
    llm_router=Depends(get_llm_router),
    memory_manager=Depends(get_memory_manager),
    orchestrator=Depends(get_orchestration_router),
) -> HealthResponse:
    """
    Performs dependency-aware health checks with isolation and timeouts.
    """

    services: Dict[str, str] = {}
    errors: Dict[str, str] = {}

    # ---- LLM Router Check ----
    try:
        _ = await _with_timeout(
            asyncio.to_thread(llm_router.get_provider_stats),
            "LLM router",
        )
        services["llm"] = "healthy"
        services["llm_providers"] = list(llm_router.providers.keys())
    except Exception as e:
        logger.error("LLM health check failed", exc_info=True)
        services["llm"] = "unhealthy"
        errors["llm"] = str(e)

    # ---- Memory Manager Check ----
    try:
        _ = await _with_timeout(
            memory_manager.get_stats(),
            "Memory manager",
        )
        services["memory"] = "healthy"
    except Exception as e:
        logger.error("Memory health check failed", exc_info=True)
        services["memory"] = "unhealthy"
        errors["memory"] = str(e)

    # ---- Orchestration Check ----
    try:
        orchestrator.validate()
        services["orchestration"] = "healthy"
    except Exception as e:
        logger.error("Orchestration health check failed", exc_info=True)
        services["orchestration"] = "unhealthy"
        errors["orchestration"] = str(e)

    # ---- Overall Status ----
    critical_services = ["llm", "memory", "orchestration"]
    overall_status = (
        "healthy"
        if all(services.get(s) == "healthy" for s in critical_services)
        else "degraded"
    )

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        environment=settings.app_env,
        services=services,
        errors=errors or None,
    )


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Indicates whether the service is ready to receive traffic",
    tags=["Health"],
)
async def readiness_check(
    memory_manager=Depends(get_memory_manager),
) -> dict:
    """
    Kubernetes readiness probe.
    Fails if critical dependencies are unavailable.
    """
    try:
        await _with_timeout(memory_manager.get_stats(), "Memory readiness")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready",
        )

    return {"ready": True}


@router.get(
    "/health/live",
    summary="Liveness check",
    description="Indicates whether the process is alive",
    tags=["Health"],
)
async def liveness_check() -> dict:
    """
    Kubernetes liveness probe.
    Should NEVER check dependencies.
    """
    return {"live": True}
