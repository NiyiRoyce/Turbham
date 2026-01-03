# runtime context for request handling
"""Request-scoped context for orchestration."""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from agents.base import AgentContext


@dataclass
class OrchestrationContext:
    """
    Request-scoped context that flows through the orchestration pipeline.
    
    Contains all information needed to process a user request through
    multiple agents and execution steps.
    """
    # Request identifiers
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:16]}")
    
    # User information
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Request data
    user_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Agent context (for agents)
    agent_context: Optional[AgentContext] = None
    
    # Conversation metadata
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    user_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Orchestration state
    current_intent: Optional[str] = None
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    executed_agents: List[str] = field(default_factory=list)
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    
    # Execution tracking
    execution_plan: Optional[Any] = None  # Will be ExecutionPlan
    execution_results: Dict[str, Any] = field(default_factory=dict)
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Performance metrics
    start_time: datetime = field(default_factory=datetime.now)
    agent_latencies: Dict[str, float] = field(default_factory=dict)
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    
    # Flags
    escalate_to_human: bool = False
    escalation_reason: Optional[str] = None
    
    def add_agent_execution(
        self,
        agent_name: str,
        latency_ms: float,
        tokens: int = 0,
        cost: float = 0.0,
    ):
        """Record agent execution."""
        self.executed_agents.append(agent_name)
        self.agent_latencies[agent_name] = latency_ms
        self.total_tokens_used += tokens
        self.total_cost_usd += cost
    
    def add_error(
        self,
        error: str,
        component: str,
        severity: str = "error",
    ):
        """Add error to context."""
        self.errors.append({
            "error": error,
            "component": component,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
        })
    
    def add_warning(self, warning: str):
        """Add warning to context."""
        self.warnings.append(warning)
    
    def set_confidence(self, agent: str, confidence: float):
        """Set confidence score for an agent."""
        self.confidence_scores[agent] = confidence
    
    def get_elapsed_time_ms(self) -> float:
        """Get elapsed time since request start."""
        return (datetime.now() - self.start_time).total_seconds() * 1000
    
    def should_escalate(self) -> bool:
        """Determine if request should be escalated."""
        return (
            self.escalate_to_human
            or len(self.errors) > 3
            or any(e["severity"] == "critical" for e in self.errors)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/monitoring."""
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "current_intent": self.current_intent,
            "executed_agents": self.executed_agents,
            "requires_clarification": self.requires_clarification,
            "escalate_to_human": self.escalate_to_human,
            "elapsed_time_ms": self.get_elapsed_time_ms(),
            "total_tokens": self.total_tokens_used,
            "total_cost": self.total_cost_usd,
            "errors": self.errors,
            "warnings": self.warnings,
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "elapsed_time_ms": self.get_elapsed_time_ms(),
            "agents_executed": len(self.executed_agents),
            "agent_latencies": self.agent_latencies,
            "total_tokens": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


@dataclass
class RequestMetadata:
    """Metadata about the incoming request."""
    source: str = "api"  # api, websocket, webhook, etc.
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    language: str = "en"
    platform: Optional[str] = None
    version: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "language": self.language,
            "platform": self.platform,
            "version": self.version,
        }


class ContextBuilder:
    """
    Builds orchestration context from incoming requests.
    """
    
    @staticmethod
    def from_request(
        user_message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        user_metadata: Optional[Dict] = None,
        request_metadata: Optional[RequestMetadata] = None,
    ) -> OrchestrationContext:
        """
        Build orchestration context from request parameters.
        
        Args:
            user_message: The user's message
            user_id: Optional user identifier
            session_id: Optional session identifier
            conversation_history: Optional conversation history
            user_metadata: Optional user metadata
            request_metadata: Optional request metadata
            
        Returns:
            OrchestrationContext
        """
        # Create agent context
        agent_context = AgentContext(
            user_id=user_id,
            session_id=session_id,
            conversation_history=conversation_history or [],
            user_metadata=user_metadata or {},
        )
        
        # Build orchestration context
        context = OrchestrationContext(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            agent_context=agent_context,
            conversation_history=conversation_history or [],
            user_metadata=user_metadata or {},
        )
        
        # Add request metadata if provided
        if request_metadata:
            context.user_metadata["request_metadata"] = request_metadata.to_dict()
        
        return context
    
    @staticmethod
    def from_memory_session(
        user_message: str,
        session_id: str,
        memory_manager,
    ) -> OrchestrationContext:
        """
        Build context from memory session.
        
        Args:
            user_message: The user's message
            session_id: Session identifier
            memory_manager: MemoryManager instance
            
        Returns:
            OrchestrationContext (async, so caller must await)
        """
        # This is a helper - actual implementation would be async
        # and called from the router
        pass


class ContextEnricher:
    """
    Enriches context with additional data during orchestration.
    """
    
    @staticmethod
    def enrich_with_intent(
        context: OrchestrationContext,
        intent: str,
        confidence: float,
    ):
        """Add intent classification results."""
        context.current_intent = intent
        context.set_confidence("intent", confidence)
    
    @staticmethod
    def enrich_with_clarification(
        context: OrchestrationContext,
        requires_clarification: bool,
        question: Optional[str] = None,
    ):
        """Add clarification requirement."""
        context.requires_clarification = requires_clarification
        context.clarification_question = question
    
    @staticmethod
    def enrich_with_escalation(
        context: OrchestrationContext,
        should_escalate: bool,
        reason: Optional[str] = None,
    ):
        """Add escalation decision."""
        context.escalate_to_human = should_escalate
        context.escalation_reason = reason
    
    @staticmethod
    def enrich_with_execution_result(
        context: OrchestrationContext,
        component: str,
        result: Any,
    ):
        """Add execution result."""
        context.execution_results[component] = result