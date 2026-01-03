# central dependencies (db, llm client, etc.)
"""FastAPI dependency injection."""

from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from functools import lru_cache

from llm import LLMRouter, OpenAIProvider, AnthropicProvider, RouteConfig, RoutingStrategy
from memory import MemoryManager, InMemoryStore, RedisStore
from orchestration import OrchestrationRouter, PolicyManager
from config import settings


# Global instances (initialized once)
_llm_router: Optional[LLMRouter] = None
_memory_manager: Optional[MemoryManager] = None
_orchestration_router: Optional[OrchestrationRouter] = None


@lru_cache()
def get_llm_router() -> LLMRouter:
    """
    Get or create LLM router instance.
    
    Returns:
        LLMRouter instance
    """
    global _llm_router
    
    if _llm_router is None:
        # Initialize providers
        providers = {}
        
        if settings.openai_api_key:
            providers["openai"] = OpenAIProvider(
                api_key=settings.openai_api_key,
                default_model=settings.default_model,
            )
        
        if settings.anthropic_api_key:
            providers["anthropic"] = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                default_model=settings.fallback_model,
            )
        
        if not providers:
            raise RuntimeError("No LLM providers configured")
        
        # Create router with configuration
        strategy_map = {
            "cost": RoutingStrategy.COST,
            "latency": RoutingStrategy.LATENCY,
            "quality": RoutingStrategy.QUALITY,
            "primary": RoutingStrategy.PRIMARY,
        }
        
        _llm_router = LLMRouter(
            providers=providers,
            route_config=RouteConfig(
                strategy=strategy_map.get(
                    settings.llm_routing_strategy,
                    RoutingStrategy.QUALITY
                ),
                primary_provider=settings.default_llm_provider,
                fallback_providers=[settings.fallback_provider] if settings.fallback_provider != settings.default_llm_provider else [],
            )
        )
    
    return _llm_router


@lru_cache()
def get_memory_manager() -> MemoryManager:
    """
    Get or create memory manager instance.
    
    Returns:
        MemoryManager instance
    """
    global _memory_manager
    
    if _memory_manager is None:
        # Choose storage backend based on environment
        if settings.is_production and settings.redis_url:
            store = RedisStore(
                redis_url=settings.redis_url,
                ttl_seconds=7 * 86400,  # 7 days
            )
        else:
            store = InMemoryStore()
        
        _memory_manager = MemoryManager(
            store=store,
            llm_router=get_llm_router(),
            enable_summarization=settings.enable_rag,
            enable_validation=True,
            auto_summarize_threshold=20,
        )
    
    return _memory_manager


@lru_cache()
def get_orchestration_router() -> OrchestrationRouter:
    """
    Get or create orchestration router instance.
    
    Returns:
        OrchestrationRouter instance
    """
    global _orchestration_router
    
    if _orchestration_router is None:
        _orchestration_router = OrchestrationRouter(
            llm_router=get_llm_router(),
            memory_manager=get_memory_manager(),
            policy_manager=PolicyManager(),
        )
    
    return _orchestration_router


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Verify API key from header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        Verified API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Skip in development
    if settings.is_development:
        return "dev_key"
    
    if not settings.api_key:
        # No API key configured, skip verification
        return "no_key_configured"
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return x_api_key


async def get_current_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> Optional[str]:
    """
    Extract user ID from header.
    
    Args:
        x_user_id: User ID from X-User-Id header
        
    Returns:
        User ID or None
    """
    return x_user_id


async def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id")
) -> Optional[str]:
    """
    Extract session ID from header.
    
    Args:
        x_session_id: Session ID from X-Session-Id header
        
    Returns:
        Session ID or None
    """
    return x_session_id


# Dependency combinations
async def get_authenticated_user(
    api_key: str = Depends(verify_api_key),
    user_id: Optional[str] = Depends(get_current_user_id),
) -> Optional[str]:
    """
    Get authenticated user ID.
    
    Args:
        api_key: Verified API key
        user_id: User ID from header
        
    Returns:
        User ID or None
    """
    return user_id


async def get_request_context(
    user_id: Optional[str] = Depends(get_current_user_id),
    session_id: Optional[str] = Depends(get_session_id),
) -> dict:
    """
    Build request context from headers.
    
    Args:
        user_id: User ID from header
        session_id: Session ID from header
        
    Returns:
        Request context dictionary
    """
    return {
        "user_id": user_id,
        "session_id": session_id,
    }