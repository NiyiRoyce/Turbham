# execution plan builder
"""Execution plan for orchestrating agent actions."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    """Types of actions in execution plan."""
    AGENT_CALL = "agent_call"
    TOOL_CALL = "tool_call"
    DATA_FETCH = "data_fetch"
    VALIDATION = "validation"
    RESPONSE_GENERATION = "response_generation"
    ESCALATION = "escalation"


class ActionStatus(str, Enum):
    """Status of action execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Action:
    """Single action in execution plan."""
    action_id: str
    action_type: ActionType
    component: str  # Agent or tool name
    description: str
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    
    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Execution state
    status: ActionStatus = ActionStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Flags
    required: bool = True  # If True, failure blocks plan
    retry_on_failure: bool = False
    max_retries: int = 0
    
    def can_execute(self, completed_actions: List[str]) -> bool:
        """Check if action can be executed."""
        if self.status != ActionStatus.PENDING:
            return False
        
        # Check dependencies
        return all(dep in completed_actions for dep in self.depends_on)
    
    def mark_completed(self, result: Any):
        """Mark action as completed."""
        self.status = ActionStatus.COMPLETED
        self.result = result
    
    def mark_failed(self, error: str):
        """Mark action as failed."""
        self.status = ActionStatus.FAILED
        self.error = error
    
    def mark_skipped(self):
        """Mark action as skipped."""
        self.status = ActionStatus.SKIPPED


@dataclass
class ExecutionPlan:
    """
    Structured execution plan for request processing.
    
    Defines sequence of actions (agent calls, tool calls, etc.)
    needed to fulfill a user request.
    """
    plan_id: str
    intent: str
    actions: List[Action] = field(default_factory=list)
    
    # Metadata
    created_at: Optional[str] = None
    estimated_duration_ms: Optional[float] = None
    
    def add_action(self, action: Action):
        """Add action to plan."""
        self.actions.append(action)
    
    def get_next_actions(self) -> List[Action]:
        """Get actions ready to execute."""
        completed = [
            a.action_id for a in self.actions
            if a.status == ActionStatus.COMPLETED
        ]
        
        return [
            action for action in self.actions
            if action.can_execute(completed)
        ]
    
    def get_action(self, action_id: str) -> Optional[Action]:
        """Get action by ID."""
        for action in self.actions:
            if action.action_id == action_id:
                return action
        return None
    
    def is_complete(self) -> bool:
        """Check if all required actions are complete."""
        for action in self.actions:
            if action.required and action.status != ActionStatus.COMPLETED:
                return False
        return True
    
    def has_failed(self) -> bool:
        """Check if any required action has failed."""
        for action in self.actions:
            if action.required and action.status == ActionStatus.FAILED:
                return True
        return False
    
    def get_progress(self) -> Dict[str, int]:
        """Get execution progress."""
        status_counts = {
            "total": len(self.actions),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
        }
        
        for action in self.actions:
            status_counts[action.status.value] += 1
        
        return status_counts
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "intent": self.intent,
            "actions": [
                {
                    "action_id": a.action_id,
                    "type": a.action_type.value,
                    "component": a.component,
                    "description": a.description,
                    "status": a.status.value,
                    "required": a.required,
                }
                for a in self.actions
            ],
            "progress": self.get_progress(),
            "is_complete": self.is_complete(),
            "has_failed": self.has_failed(),
        }


class ExecutionPlanBuilder:
    """
    Builds execution plans based on intent and context.
    """
    
    @staticmethod
    def build_for_intent(
        intent: str,
        context: Dict[str, Any],
    ) -> ExecutionPlan:
        """
        Build execution plan for given intent.
        
        Args:
            intent: Classified intent
            context: Request context
            
        Returns:
            ExecutionPlan
        """
        plan_id = f"plan_{intent}"
        plan = ExecutionPlan(plan_id=plan_id, intent=intent)
        
        if intent == "order_status":
            plan = ExecutionPlanBuilder._build_order_status_plan(context)
        
        elif intent == "product_info":
            plan = ExecutionPlanBuilder._build_product_info_plan(context)
        
        elif intent == "ticket_creation":
            plan = ExecutionPlanBuilder._build_ticket_plan(context)
        
        elif intent == "returns_refunds":
            plan = ExecutionPlanBuilder._build_returns_plan(context)
        
        elif intent in ["general_inquiry", "greeting"]:
            plan = ExecutionPlanBuilder._build_knowledge_plan(context)
        
        elif intent == "escalation":
            plan = ExecutionPlanBuilder._build_escalation_plan(context)
        
        else:
            # Default plan
            plan = ExecutionPlanBuilder._build_default_plan(context)
        
        return plan
    
    @staticmethod
    def _build_order_status_plan(context: Dict) -> ExecutionPlan:
        """Build plan for order status queries."""
        plan = ExecutionPlan(plan_id="plan_order_status", intent="order_status")
        
        # Action 1: Fetch order data
        plan.add_action(Action(
            action_id="fetch_order",
            action_type=ActionType.DATA_FETCH,
            component="shopify",
            description="Fetch order data from Shopify",
            parameters={"order_id": context.get("order_id")},
            required=True,
        ))
        
        # Action 2: Generate response with orders agent
        plan.add_action(Action(
            action_id="generate_response",
            action_type=ActionType.AGENT_CALL,
            component="orders_agent",
            description="Generate order status response",
            depends_on=["fetch_order"],
            required=True,
        ))
        
        return plan
    
    @staticmethod
    def _build_product_info_plan(context: Dict) -> ExecutionPlan:
        """Build plan for product information queries."""
        plan = ExecutionPlan(plan_id="plan_product_info", intent="product_info")
        
        # Action 1: Search knowledge base
        plan.add_action(Action(
            action_id="search_knowledge",
            action_type=ActionType.DATA_FETCH,
            component="knowledge_base",
            description="Search product information",
            required=True,
        ))
        
        # Action 2: Generate answer with knowledge agent
        plan.add_action(Action(
            action_id="generate_answer",
            action_type=ActionType.AGENT_CALL,
            component="knowledge_agent",
            description="Generate product information answer",
            depends_on=["search_knowledge"],
            required=True,
        ))
        
        return plan
    
    @staticmethod
    def _build_ticket_plan(context: Dict) -> ExecutionPlan:
        """Build plan for ticket creation."""
        plan = ExecutionPlan(plan_id="plan_ticket", intent="ticket_creation")
        
        # Action 1: Generate ticket with tickets agent
        plan.add_action(Action(
            action_id="create_ticket_data",
            action_type=ActionType.AGENT_CALL,
            component="tickets_agent",
            description="Generate ticket structure",
            required=True,
        ))
        
        # Action 2: Create ticket in helpdesk
        plan.add_action(Action(
            action_id="create_ticket",
            action_type=ActionType.TOOL_CALL,
            component="gorgias",
            description="Create ticket in Gorgias",
            depends_on=["create_ticket_data"],
            required=True,
        ))
        
        # Action 3: Send confirmation
        plan.add_action(Action(
            action_id="send_confirmation",
            action_type=ActionType.RESPONSE_GENERATION,
            component="response_formatter",
            description="Send ticket confirmation to user",
            depends_on=["create_ticket"],
            required=True,
        ))
        
        return plan
    
    @staticmethod
    def _build_returns_plan(context: Dict) -> ExecutionPlan:
        """Build plan for returns/refunds."""
        plan = ExecutionPlan(plan_id="plan_returns", intent="returns_refunds")
        
        # Similar structure to ticket plan
        plan.add_action(Action(
            action_id="fetch_order",
            action_type=ActionType.DATA_FETCH,
            component="shopify",
            description="Fetch order for return",
            required=True,
        ))
        
        plan.add_action(Action(
            action_id="create_return_ticket",
            action_type=ActionType.AGENT_CALL,
            component="tickets_agent",
            description="Create return ticket",
            depends_on=["fetch_order"],
            required=True,
        ))
        
        return plan
    
    @staticmethod
    def _build_knowledge_plan(context: Dict) -> ExecutionPlan:
        """Build plan for knowledge-based queries."""
        plan = ExecutionPlan(plan_id="plan_knowledge", intent="general_inquiry")
        
        plan.add_action(Action(
            action_id="search_knowledge",
            action_type=ActionType.DATA_FETCH,
            component="knowledge_base",
            description="Search knowledge base",
            required=True,
        ))
        
        plan.add_action(Action(
            action_id="generate_answer",
            action_type=ActionType.AGENT_CALL,
            component="knowledge_agent",
            description="Generate answer",
            depends_on=["search_knowledge"],
            required=True,
        ))
        
        return plan
    
    @staticmethod
    def _build_escalation_plan(context: Dict) -> ExecutionPlan:
        """Build plan for escalation."""
        plan = ExecutionPlan(plan_id="plan_escalation", intent="escalation")
        
        plan.add_action(Action(
            action_id="notify_human",
            action_type=ActionType.ESCALATION,
            component="slack",
            description="Notify human agents",
            required=True,
        ))
        
        plan.add_action(Action(
            action_id="send_handoff",
            action_type=ActionType.RESPONSE_GENERATION,
            component="response_formatter",
            description="Send handoff message to user",
            depends_on=["notify_human"],
            required=True,
        ))
        
        return plan
    
    @staticmethod
    def _build_default_plan(context: Dict) -> ExecutionPlan:
        """Build default fallback plan."""
        plan = ExecutionPlan(plan_id="plan_default", intent="unknown")
        
        plan.add_action(Action(
            action_id="generate_fallback",
            action_type=ActionType.RESPONSE_GENERATION,
            component="response_formatter",
            description="Generate fallback response",
            required=True,
        ))
        
        return plan