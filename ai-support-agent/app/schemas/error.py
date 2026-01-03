"""Error schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: Optional[str] = Field(None, description="Field that caused error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid request data",
                "details": [
                    {
                        "field": "message",
                        "message": "Message cannot be empty",
                        "code": "value_error"
                    }
                ],
                "request_id": "req_abc123"
            }
        }


class ValidationError(ErrorResponse):
    """Validation error response."""
    error: str = "ValidationError"


class AuthenticationError(ErrorResponse):
    """Authentication error response."""
    error: str = "AuthenticationError"


class RateLimitError(ErrorResponse):
    """Rate limit error response."""
    error: str = "RateLimitError"
    retry_after: Optional[int] = Field(None, description="Seconds until retry allowed")


class NotFoundError(ErrorResponse):
    """Not found error response."""
    error: str = "NotFoundError"


class InternalServerError(ErrorResponse):
    """Internal server error response."""
    error: str = "InternalServerError"