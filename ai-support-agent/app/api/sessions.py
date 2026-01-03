"""Session management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List
import logging

from app.schemas.request import CreateSessionRequest, UpdateSessionRequest
from app.schemas.response import SessionResponse, ConversationHistoryResponse
from app.schemas.error import ErrorResponse, NotFoundError
from app.dependencies import get_memory_manager, verify_api_key
from memory import MemoryManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Session created successfully"},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Create new session",
    description="Create a new conversation session",
)
async def create_session(
    request: CreateSessionRequest,
    memory: MemoryManager = Depends(get_memory_manager),
    api_key: str = Depends(verify_api_key),
) -> SessionResponse:
    """
    Create a new conversation session.
    
    Args:
        request: Session creation request
        memory: Memory manager
        api_key: Verified API key
        
    Returns:
        SessionResponse with new session details
    """
    try:
        session = await memory.create_session(
            user_id=request.user_id,
            metadata=request.metadata or {},
        )
        
        logger.info(f"Created session {session.session_id} for user {request.user_id}")
        
        return SessionResponse(
            success=True,
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            message_count=0,
            metadata=session.metadata,
        )
    
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    responses={
        200: {"description": "Session found"},
        404: {"model": NotFoundError, "description": "Session not found"},
        401: {"model": ErrorResponse},
    },
    summary="Get session",
    description="Retrieve session details",
)
async def get_session(
    session_id: str = Path(..., description="Session identifier"),
    memory: MemoryManager = Depends(get_memory_manager),
    api_key: str = Depends(verify_api_key),
) -> SessionResponse:
    """
    Get session details.
    
    Args:
        session_id: Session identifier
        memory: Memory manager
        api_key: Verified API key
        
    Returns:
        SessionResponse with session details
    """
    session = await memory.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return SessionResponse(
        success=True,
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        message_count=len(session.messages),
        metadata=session.metadata,
    )


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    responses={
        200: {"description": "Session updated"},
        404: {"model": NotFoundError},
        401: {"model": ErrorResponse},
    },
    summary="Update session",
    description="Update session metadata",
)
async def update_session(
    request: UpdateSessionRequest,
    session_id: str = Path(..., description="Session identifier"),
    memory: MemoryManager = Depends(get_memory_manager),
    api_key: str = Depends(verify_api_key),
) -> SessionResponse:
    """
    Update session metadata.
    
    Args:
        request: Update request
        session_id: Session identifier
        memory: Memory manager
        api_key: Verified API key
        
    Returns:
        SessionResponse with updated session
    """
    # Check if session exists
    session = await memory.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    try:
        await memory.update_session_metadata(
            session_id=session_id,
            metadata=request.metadata,
            merge=request.merge,
        )
        
        # Fetch updated session
        updated_session = await memory.get_session(session_id)
        
        return SessionResponse(
            success=True,
            session_id=updated_session.session_id,
            user_id=updated_session.user_id,
            created_at=updated_session.created_at.isoformat(),
            updated_at=updated_session.updated_at.isoformat(),
            message_count=len(updated_session.messages),
            metadata=updated_session.metadata,
        )
    
    except Exception as e:
        logger.error(f"Error updating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}"
        )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Session deleted"},
        404: {"model": NotFoundError},
        401: {"model": ErrorResponse},
    },
    summary="Delete session",
    description="Delete a conversation session",
)
async def delete_session(
    session_id: str = Path(..., description="Session identifier"),
    memory: MemoryManager = Depends(get_memory_manager),
    api_key: str = Depends(verify_api_key),
):
    """
    Delete a conversation session.
    
    Args:
        session_id: Session identifier
        memory: Memory manager
        api_key: Verified API key
    """
    deleted = await memory.delete_session(session_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    logger.info(f"Deleted session {session_id}")


@router.get(
    "/sessions/{session_id}/history",
    response_model=ConversationHistoryResponse,
    responses={
        200: {"description": "Conversation history"},
        404: {"model": NotFoundError},
        401: {"model": ErrorResponse},
    },
    summary="Get conversation history",
    description="Retrieve conversation history for a session",
)
async def get_conversation_history(
    session_id: str = Path(..., description="Session identifier"),
    limit: int = 50,
    memory: MemoryManager = Depends(get_memory_manager),
    api_key: str = Depends(verify_api_key),
) -> ConversationHistoryResponse:
    """
    Get conversation history.
    
    Args:
        session_id: Session identifier
        limit: Maximum messages to return
        memory: Memory manager
        api_key: Verified API key
        
    Returns:
        ConversationHistoryResponse with messages
    """
    session = await memory.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    messages = await memory.get_conversation_history(
        session_id=session_id,
        limit=limit,
        include_summary=True,
    )
    
    return ConversationHistoryResponse(
        success=True,
        session_id=session_id,
        messages=[
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in messages
        ],
        total_count=len(session.messages),
        has_summary=session.summary is not None,
    )


@router.get(
    "/users/{user_id}/sessions",
    response_model=List[SessionResponse],
    responses={
        200: {"description": "User sessions"},
        401: {"model": ErrorResponse},
    },
    summary="List user sessions",
    description="List all sessions for a user",
)
async def list_user_sessions(
    user_id: str = Path(..., description="User identifier"),
    limit: int = 10,
    memory: MemoryManager = Depends(get_memory_manager),
    api_key: str = Depends(verify_api_key),
) -> List[SessionResponse]:
    """
    List sessions for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum sessions to return
        memory: Memory manager
        api_key: Verified API key
        
    Returns:
        List of SessionResponse
    """
    sessions = await memory.list_user_sessions(user_id=user_id, limit=limit)
    
    return [
        SessionResponse(
            success=True,
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            message_count=len(session.messages),
            metadata=session.metadata,
        )
        for session in sessions
    ]