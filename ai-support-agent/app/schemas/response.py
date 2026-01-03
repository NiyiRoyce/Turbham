"""Response schemas."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    success: bool = Field(..., description="Whether request was successful")
    message: str = Field(..., description="Response message for user")
    request_id: str = Field(..., description="Unique request identifier")
    
    # Optional fields for successful responses
    intent: Optional[str] = Field(None, description="Detected intent")
    confidence: Optional[float] = Field(None, description="Overall confidence score")
    
    # Clarification
    requires_clarification: Optional[bool] = Field(None, description="Whether clarification is needed")
    
    # Escalation
    escalated: Optional[bool] = Field(None, description="Whether request was escalated")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Your order #12345 is currently being shipped and should arrive by Friday.",
                "request_id": "req_abc123",
                "intent": "order_status",
                "confidence": 0.95,
                "metadata": {
                    "execution_time_ms": 1250,
                    "tokens_used": 450
                }
            }
        }


class SessionResponse(BaseModel):
    """Response for session operations."""
    success: bool = Field(..., description="Whether operation was successful")
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    created_at: Optional[str] = Field(None, description="Session creation timestamp")
    updated_at: Optional[str] = Field(None, description="Session update timestamp")
    message_count: Optional[int] = Field(None, description="Number of messages in session")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "session_id": "session_abc123",
                "user_id": "user_123",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:05:00Z",
                "message_count": 4,
                "metadata": {
                    "source": "web",
                    "language": "en"
                }
            }
        }


class MessageResponse(BaseModel):
    """Response for message operations."""
    success: bool = Field(..., description="Whether operation was successful")
    message_id: Optional[str] = Field(None, description="Message identifier")
    role: Optional[str] = Field(None, description="Message role")
    content: Optional[str] = Field(None, description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message_id": "msg_xyz789",
                "role": "user",
                "content": "Where is my order?",
                "timestamp": "2024-01-01T10:00:00Z"
            }
        }


class ConversationHistoryResponse(BaseModel):
    """Response for conversation history."""
    success: bool = Field(..., description="Whether request was successful")
    session_id: str = Field(..., description="Session identifier")
    messages: List[Dict[str, Any]] = Field(..., description="List of messages")
    total_count: int = Field(..., description="Total message count")
    has_summary: bool = Field(False, description="Whether session has been summarized")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "session_id": "session_abc123",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello",
                        "timestamp": "2024-01-01T10:00:00Z"
                    },
                    {
                        "role": "assistant",
                        "content": "Hi! How can I help?",
                        "timestamp": "2024-01-01T10:00:01Z"
                    }
                ],
                "total_count": 2,
                "has_summary": False
            }
        }


class HealthResponse(BaseModel):
    """Response for health check."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment (dev/prod)")
    services: Optional[Dict[str, str]] = Field(None, description="Service health status")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T10:00:00Z",
                "version": "1.0.0",
                "environment": "production",
                "services": {
                    "llm": "healthy",
                    "memory": "healthy",
                    "orchestration": "healthy"
                }
            }
        }


class WebhookResponse(BaseModel):
    """Response for webhook operations."""
    success: bool = Field(..., description="Whether webhook was processed")
    event_type: str = Field(..., description="Type of event processed")
    message: Optional[str] = Field(None, description="Processing message")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "event_type": "order.updated",
                "message": "Webhook processed successfully"
            }
        }


class MetricsResponse(BaseModel):
    """Response with metrics data."""
    request_id: str
    execution_time_ms: float
    agents_executed: int
    total_tokens: int
    total_cost_usd: float
    error_count: int
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "req_abc123",
                "execution_time_ms": 1250.5,
                "agents_executed": 2,
                "total_tokens": 450,
                "total_cost_usd": 0.0015,
                "error_count": 0
            }
        }