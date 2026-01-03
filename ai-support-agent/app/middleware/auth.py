
"""Authentication middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    """Optional authentication middleware for all routes."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Skip in development
        if settings.is_development:
            return await call_next(request)
        
        # Check API key
        api_key = request.headers.get("x-api-key")
        
        if not api_key or api_key != settings.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AuthenticationError",
                    "message": "Invalid or missing API key"
                }
            )
        
        return await call_next(request)
