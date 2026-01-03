"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.api import chat, health, sessions, webhooks
from app.middleware.logging import LoggingMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from config import settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered customer support agent API",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware (order matters!)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware)
    
    # Register routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
    app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])
    app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
    
    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            }
        )
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
        
        # Validate configuration
        try:
            settings.validate_llm_config()
            logger.info("LLM configuration validated successfully")
        except ValueError as e:
            logger.error(f"LLM configuration error: {e}")
            raise
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info(f"Shutting down {settings.app_name}")
        # Cleanup resources here (close connections, etc.)
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )