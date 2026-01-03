# request logging middleware (stub)

"""Logging middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging
import time

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        # Log request
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"[{request_id}]"
        )
        
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} "
            f"[{request_id}] "
            f"({duration:.3f}s)"
        )
        
        return response