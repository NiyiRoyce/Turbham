# request context helper (stub)

"""Request context middleware for tracking."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import uuid
import time


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request context (ID, timing, etc.)."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Track timing
        start_time = time.time()
        
        # Add to headers for response
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration:.3f}"
        
        return response

