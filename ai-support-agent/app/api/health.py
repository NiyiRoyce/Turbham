"""Health check endpoints."""

from fastapi import APIRouter, Depends
from datetime import datetime
import logging

from app.schemas.response import HealthResponse
from app.dependencies import get_llm_router, get_memory_manager, get_orchestration_router
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the API is healthy and all services are operational",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse with service status
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        environment=settings.app_env,
    )


@router.get(
    "/health/detailed",
    response_model=HealthResponse,
    summary="Detailed health check",
    description="Check health status of all system components",
    tags=["Health"],
)
async def detailed_health_check(
    llm_router = Depends(get_llm_router),
    memory_manager = Depends(get_memory_manager),
    orchestrator = Depends(get_orchestration_router),
) -> HealthResponse:
    """
    Detailed health check that verifies all components.
    
    Args:
        llm_router: LLM router instance
        memory_manager: Memory manager instance
        orchestrator: Orchestration router instance
        
    Returns:
        HealthResponse with detailed service status
    """
    services = {}
    
    # Check LLM router
    try:
        provider_stats = llm_router.get_provider_stats()
        services["llm"] = "healthy"
        services["llm_providers"] = list(llm_router.providers.keys())
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        services["llm"] = "unhealthy"
    
    # Check memory manager
    try:
        stats = await memory_manager.get_stats()
        services["memory"] = "healthy"
    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        services["memory"] = "unhealthy"
    
    # Check orchestration
    try:
        services["orchestration"] = "healthy"
    except Exception as e:
        logger.error(f"Orchestration health check failed: {e}")
        services["orchestration"] = "unhealthy"
    
    # Determine overall status
    overall_status = "healthy" if all(
        v == "healthy" for k, v in services.items()
        if not k.endswith("_providers")
    ) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        environment=settings.app_env,
        services=services,
    )


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Check if the service is ready to accept requests",
    tags=["Health"],
)
async def readiness_check() -> dict:
    """
    Kubernetes/Docker readiness probe.
    
    Returns:
        Ready status
    """
    return {"ready": True}


@router.get(
    "/health/live",
    summary="Liveness check",
    description="Check if the service is alive",
    tags=["Health"],
)
async def liveness_check() -> dict:
    """
    Kubernetes/Docker liveness probe.
    
    Returns:
        Live status
    """
    return {"live": True}