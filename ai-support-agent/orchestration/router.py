# routes intents to agents
"""Main orchestration router that coordinates all agents and execution."""

from typing import Optional, Dict, Any
import time

from orchestration.context import OrchestrationContext, ContextBuilder
from orchestration.confidence import ConfidenceAggregator, ConfidencePolicy
from orchestration.ambiguity import AmbiguityResolver
from orchestration.execution_plan import ExecutionPlanBuilder, ExecutionPlan, ActionStatus
from orchestration.policies import PolicyManager, PolicyDecision

from agents import (
    IntentAgent,
    KnowledgeAgent,
    OrdersAgent,
    TicketsAgent,
    EscalationAgent,
)
from agents.base import AgentContext
from llm import LLMRouter
from memory import MemoryManager


class OrchestrationRouter:
    """
    Main orchestration router that coordinates request processing.
    
    Flow:
    1. Receive user request
    2. Classify intent
    3. Check for ambiguity
    4. Create execution plan
    5. Execute plan (call agents, fetch data, etc.)
    6. Apply policies (escalation, fallback, etc.)
    7. Return response
    """
    
    def __init__(
        self,
        llm_router: LLMRouter,
        memory_manager: Optional[MemoryManager] = None,
        policy_manager: Optional[PolicyManager] = None,
    ):
        """
        Initialize orchestration router.
        
        Args:
            llm_router: LLM router for agents
            memory_manager: Optional memory manager
            policy_manager: Optional policy manager
        """
        self.llm_router = llm_router
        self.memory_manager = memory_manager
        self.policy_manager = policy_manager or PolicyManager()
        
        # Initialize agents
        self.intent_agent = IntentAgent(llm_router)
        self.knowledge_agent = KnowledgeAgent(llm_router)
        self.orders_agent = OrdersAgent(llm_router)
        self.tickets_agent = TicketsAgent(llm_router)
        self.escalation_agent = EscalationAgent(llm_router)
        
        # Initialize orchestration components
        self.ambiguity_resolver = AmbiguityResolver()
    
    async def process_request(
        self,
        user_message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        user_metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Process user request through orchestration pipeline.
        
        Args:
            user_message: User's message
            user_id: Optional user identifier
            session_id: Optional session identifier
            conversation_history: Optional conversation history
            user_metadata: Optional user metadata
            
        Returns:
            Response dictionary
        """
        # Build orchestration context
        context = ContextBuilder.from_request(
            user_message=user_message,
            user_id=user_id,
            session_id=session_id,
            conversation_history=conversation_history,
            user_metadata=user_metadata,
        )
        
        try:
            # Step 1: Classify intent
            intent_result = await self._classify_intent(context)
            
            # Step 2: Check for ambiguity
            ambiguity_check = await self._check_ambiguity(context, intent_result)
            
            if ambiguity_check["requires_clarification"]:
                return self._create_clarification_response(context, ambiguity_check)
            
            # Step 3: Create execution plan
            execution_plan = self._create_execution_plan(context, intent_result)
            context.execution_plan = execution_plan
            
            # Step 4: Execute plan
            execution_result = await self._execute_plan(context, execution_plan)
            
            # Step 5: Check escalation
            escalation_check = await self._check_escalation(context)
            
            if escalation_check["should_escalate"]:
                return self._create_escalation_response(context, escalation_check)
            
            # Step 6: Format final response
            return self._create_success_response(context, execution_result)
        
        except Exception as e:
            context.add_error(str(e), "orchestration_router", "critical")
            return self._create_error_response(context, str(e))
    
    async def _classify_intent(
        self,
        context: OrchestrationContext,
    ) -> Dict[str, Any]:
        """Classify user intent."""
        start_time = time.time()
        
        # Execute intent agent
        result = await self.intent_agent.execute(
            user_message=context.user_message,
            context=context.agent_context,
        )
        
        latency = (time.time() - start_time) * 1000
        
        # Update context
        if result.success:
            context.current_intent = result.data["intent"]
            context.set_confidence("intent", result.confidence)
            context.add_agent_execution(
                "intent_agent",
                latency,
                tokens=result.metadata.get("tokens_used", 0),
                cost=result.metadata.get("cost", 0.0),
            )
        else:
            context.add_error(result.error, "intent_agent")
        
        return result.data if result.success else {}
    
    async def _check_ambiguity(
        self,
        context: OrchestrationContext,
        intent_result: Dict,
    ) -> Dict:
        """Check for ambiguous input."""
        ambiguity_check = self.ambiguity_resolver.analyze_and_resolve(
            user_message=context.user_message,
            intent_confidence=context.confidence_scores.get("intent"),
            possible_intents=intent_result.get("possible_intents"),
            context=context.user_metadata,
        )
        
        if ambiguity_check["requires_clarification"]:
            context.requires_clarification = True
            context.clarification_question = ambiguity_check["clarification_question"]
        
        return ambiguity_check
    
    def _create_execution_plan(
        self,
        context: OrchestrationContext,
        intent_result: Dict,
    ) -> ExecutionPlan:
        """Create execution plan based on intent."""
        intent = context.current_intent or "unknown"
        
        plan = ExecutionPlanBuilder.build_for_intent(
            intent=intent,
            context={
                "user_message": context.user_message,
                "user_metadata": context.user_metadata,
                **intent_result,
            }
        )
        
        return plan
    
    async def _execute_plan(
        self,
        context: OrchestrationContext,
        plan: ExecutionPlan,
    ) -> Dict[str, Any]:
        """Execute the execution plan."""
        results = {}
        
        # Execute actions in plan
        max_iterations = 10
        iteration = 0
        
        while not plan.is_complete() and iteration < max_iterations:
            next_actions = plan.get_next_actions()
            
            if not next_actions:
                break
            
            for action in next_actions:
                # Execute action based on type
                result = await self._execute_action(context, action)
                
                if result["success"]:
                    action.mark_completed(result["data"])
                    results[action.action_id] = result["data"]
                else:
                    if action.required:
                        action.mark_failed(result["error"])
                        context.add_error(result["error"], action.component)
                        break
                    else:
                        action.mark_skipped()
            
            iteration += 1
        
        return results
    
    async def _execute_action(
        self,
        context: OrchestrationContext,
        action,
    ) -> Dict:
        """Execute a single action."""
        start_time = time.time()
        
        try:
            if action.action_type.value == "agent_call":
                result = await self._execute_agent(context, action)
            elif action.action_type.value == "data_fetch":
                result = await self._execute_data_fetch(context, action)
            elif action.action_type.value == "response_generation":
                result = await self._execute_response_generation(context, action)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action type: {action.action_type}"
                }
            
            latency = (time.time() - start_time) * 1000
            context.add_agent_execution(action.component, latency)
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_agent(
        self,
        context: OrchestrationContext,
        action,
    ) -> Dict:
        """Execute an agent call."""
        agent_map = {
            "knowledge_agent": self.knowledge_agent,
            "orders_agent": self.orders_agent,
            "tickets_agent": self.tickets_agent,
        }
        
        agent = agent_map.get(action.component)
        if not agent:
            return {"success": False, "error": f"Agent {action.component} not found"}
        
        # Execute agent
        result = await agent.execute(
            user_message=context.user_message,
            context=context.agent_context,
            **action.parameters,
        )
        
        if result.success:
            return {"success": True, "data": result.data}
        else:
            return {"success": False, "error": result.error}
    
    async def _execute_data_fetch(
        self,
        context: OrchestrationContext,
        action,
    ) -> Dict:
        """Execute data fetch (mock implementation)."""
        # In production, this would call actual services
        # For now, return mock data
        
        if action.component == "knowledge_base":
            return {
                "success": True,
                "data": {
                    "chunks": ["Mock knowledge base content..."],
                }
            }
        elif action.component == "shopify":
            return {
                "success": True,
                "data": {
                    "order_id": action.parameters.get("order_id"),
                    "status": "shipped",
                    "tracking": "TRACK123",
                }
            }
        else:
            return {"success": True, "data": {}}
    
    async def _execute_response_generation(
        self,
        context: OrchestrationContext,
        action,
    ) -> Dict:
        """Execute response generation."""
        # Use execution results to generate response
        return {
            "success": True,
            "data": {
                "response": "Response generated successfully"
            }
        }
    
    async def _check_escalation(
        self,
        context: OrchestrationContext,
    ) -> Dict:
        """Check if request should be escalated."""
        # Use escalation agent
        result = await self.escalation_agent.execute(
            user_message=context.user_message,
            context=context.agent_context,
        )
        
        if result.success and result.data.get("should_escalate"):
            context.escalate_to_human = True
            context.escalation_reason = result.data.get("reason")
            return {
                "should_escalate": True,
                "reason": result.data.get("reason"),
                "urgency": result.data.get("urgency"),
            }
        
        return {"should_escalate": False}
    
    def _create_clarification_response(
        self,
        context: OrchestrationContext,
        ambiguity_check: Dict,
    ) -> Dict[str, Any]:
        """Create clarification response."""
        return {
            "success": True,
            "requires_clarification": True,
            "message": ambiguity_check["clarification_question"],
            "ambiguity_score": ambiguity_check["ambiguity_score"],
            "metadata": {
                "request_id": context.request_id,
                "metrics": context.get_metrics(),
            }
        }
    
    def _create_escalation_response(
        self,
        context: OrchestrationContext,
        escalation_check: Dict,
    ) -> Dict[str, Any]:
        """Create escalation response."""
        return {
            "success": True,
            "escalated": True,
            "message": "I'm connecting you with a human agent who can better assist you.",
            "reason": escalation_check["reason"],
            "urgency": escalation_check["urgency"],
            "metadata": {
                "request_id": context.request_id,
                "metrics": context.get_metrics(),
            }
        }
    
    def _create_success_response(
        self,
        context: OrchestrationContext,
        execution_result: Dict,
    ) -> Dict[str, Any]:
        """Create successful response."""
        # Extract response from execution results
        response_message = "I've processed your request."
        
        # Try to get response from various result keys
        for key in ["response_message", "answer", "user_response"]:
            for result in execution_result.values():
                if isinstance(result, dict) and key in result:
                    response_message = result[key]
                    break
        
        return {
            "success": True,
            "message": response_message,
            "intent": context.current_intent,
            "confidence": context.confidence_scores,
            "metadata": {
                "request_id": context.request_id,
                "trace_id": context.trace_id,
                "metrics": context.get_metrics(),
                "execution_plan": context.execution_plan.to_dict() if context.execution_plan else None,
            }
        }
    
    def _create_error_response(
        self,
        context: OrchestrationContext,
        error: str,
    ) -> Dict[str, Any]:
        """Create error response."""
        fallback = self.policy_manager.fallback.get_fallback_response(
            context.current_intent or "general"
        )
        
        return {
            "success": False,
            "message": fallback,
            "error": error,
            "metadata": {
                "request_id": context.request_id,
                "errors": context.errors,
                "metrics": context.get_metrics(),
            }
        }