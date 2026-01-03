"""Chat endpoint for processing user messages."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging

from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse
from app.schemas.error import ErrorResponse
from app.dependencies import (
    get_orchestration_router,
    get_memory_manager,
    verify_api_key,
    get_request_context,
)
from orchestration import OrchestrationRouter
from memory import MemoryManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        200: {"description": "Successful response"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Process chat message",
    description="Process a user message through the AI support agent system",
)
async def chat(
    request: ChatRequest,
    orchestrator: OrchestrationRouter = Depends(get_orchestration_router),
    memory: MemoryManager = Depends(get_memory_manager),
    api_key: str = Depends(verify_api_key),
    context: dict = Depends(get_request_context),
) -> ChatResponse:
    """
    Process user message through orchestration pipeline.
    
    Args:
        request: Chat request with user message
        orchestrator: Orchestration router
        memory: Memory manager
        api_key: Verified API key
        context: Request context
        
    Returns:
        ChatResponse with AI-generated response
    """
    try:
        # Extract context
        user_id = request.user_id or context.get("user_id")
        session_id = request.session_id or context.get("session_id")
        
        # Create session if needed
        if not session_id:
            session = await memory.create_session(
                user_id=user_id,
                metadata=request.metadata or {}
            )
            session_id = session.session_id
            logger.info(f"Created new session: {session_id}")
        
        # Get conversation history
        conversation_history = await memory.get_context_for_llm(
            session_id=session_id,
            max_messages=10,
        )
        
        # Add user message to memory
        await memory.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            metadata=request.metadata,
        )
        
        # Process through orchestration
        result = await orchestrator.process_request(
            user_message=request.message,
            user_id=user_id,
            session_id=session_id,
            conversation_history=conversation_history,
            user_metadata=request.metadata or {},
        )
        
        # Save assistant response to memory
        if result["success"] and not result.get("requires_clarification"):
            await memory.add_message(
                session_id=session_id,
                role="assistant",
                content=result["message"],
                metadata={
                    "intent": result.get("intent"),
                    "confidence": result.get("confidence"),
                    "request_id": result["metadata"]["request_id"],
                }
            )
        
        # Build response
        return ChatResponse(
            success=result["success"],
            message=result["message"],
            request_id=result["metadata"]["request_id"],
            intent=result.get("intent"),
            confidence=result["metadata"].get("metrics", {}).get("overall_confidence"),
            requires_clarification=result.get("requires_clarification", False),
            escalated=result.get("escalated", False),
            escalation_reason=result.get("escalation_reason"),
            metadata={
                **result.get("metadata", {}),
                "session_id": session_id,
            }
        )
    
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.post(
    "/chat/stream",
    summary="Process chat message with streaming",
    description="Process a user message with streaming response (future implementation)",
)
async def chat_stream(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Stream chat response (placeholder for future implementation).
    
    This endpoint will support streaming responses using Server-Sent Events (SSE)
    or WebSocket for real-time AI responses.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Streaming chat is not yet implemented"
    )