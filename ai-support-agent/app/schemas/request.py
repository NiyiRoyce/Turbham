"""Request schemas."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class ChatRequest(BaseModel):
    """Request for chat endpoint."""
    message: str = Field(..., description="User message", min_length=1, max_length=5000)
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator("message")
    def validate_message(cls, v):
        """Validate message is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Where is my order #12345?",
                "user_id": "user_123",
                "session_id": "session_abc",
                "metadata": {
                    "source": "web",
                    "language": "en"
                }
            }
        }


class CreateSessionRequest(BaseModel):
    """Request for creating a new session."""
    user_id: Optional[str] = Field(None, description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_123",
                "metadata": {
                    "source": "mobile_app",
                    "platform": "ios",
                    "language": "en"
                }
            }
        }


class UpdateSessionRequest(BaseModel):
    """Request for updating session metadata."""
    metadata: Dict[str, Any] = Field(..., description="Metadata to update")
    merge: bool = Field(True, description="Merge with existing metadata or replace")
    
    class Config:
        schema_extra = {
            "example": {
                "metadata": {
                    "last_intent": "order_status",
                    "order_id": "12345"
                },
                "merge": True
            }
        }


class AddMessageRequest(BaseModel):
    """Request for adding a message to a session."""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content", min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    
    @validator("role")
    def validate_role(cls, v):
        """Validate role is valid."""
        valid_roles = ["user", "assistant", "system"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "role": "user",
                "content": "I need help with my order",
                "metadata": {
                    "timestamp": "2024-01-01T10:00:00Z"
                }
            }
        }


class WebhookRequest(BaseModel):
    """Generic webhook request."""
    event_type: str = Field(..., description="Type of event")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: Optional[str] = Field(None, description="Event timestamp")
    source: Optional[str] = Field(None, description="Event source")
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "order.updated",
                "data": {
                    "order_id": "12345",
                    "status": "shipped"
                },
                "timestamp": "2024-01-01T10:00:00Z",
                "source": "shopify"
            }
        }


class FeedbackRequest(BaseModel):
    """Request for submitting feedback."""
    request_id: str = Field(..., description="Request ID to provide feedback for")
    rating: int = Field(..., description="Rating (1-5)", ge=1, le=5)
    feedback: Optional[str] = Field(None, description="Optional feedback text")
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "req_abc123",
                "rating": 5,
                "feedback": "Very helpful response!"
            }
        }