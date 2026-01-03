# orchestration-level policies
"""Policies for orchestration decisions (escalation, fallback, etc.)."""

from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""
    action: str  # "proceed", "escalate", "fallback", "retry"
    reason: str
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EscalationPolicy:
    """
    Defines when and how to escalate to human agents.
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.5,
        error_count_threshold: int = 3,
        max_retries: int = 2,
    ):
        """
        Initialize escalation policy.
        
        Args:
            confidence_threshold: Confidence below which to escalate
            error_count_threshold: Errors before escalation
            max_retries: Max retries before escalation
        """
        self.confidence_threshold = confidence_threshold
        self.error_count_threshold = error_count_threshold
        self.max_retries = max_retries
    
    def should_escalate(
        self,
        confidence: Optional[float] = None,
        error_count: int = 0,
        retry_count: int = 0,
        explicit_request: bool = False,
        frustration_detected: bool = False,
        sensitive_topic: bool = False,
    ) -> PolicyDecision:
        """
        Determine if request should be escalated.
        
        Args:
            confidence: Overall confidence score
            error_count: Number of errors encountered
            retry_count: Number of retries attempted
            explicit_request: User explicitly requested human
            frustration_detected: Frustration detected in conversation
            sensitive_topic: Topic is sensitive (refunds, complaints, etc.)
            
        Returns:
            PolicyDecision
        """
        # Priority 1: Explicit request
        if explicit_request:
            return PolicyDecision(
                action="escalate",
                reason="User explicitly requested human agent",
                metadata={"priority": "high"}
            )
        
        # Priority 2: Frustration
        if frustration_detected:
            return PolicyDecision(
                action="escalate",
                reason="Customer frustration detected",
                metadata={"priority": "high", "urgency": "immediate"}
            )
        
        # Priority 3: Sensitive topics
        if sensitive_topic:
            return PolicyDecision(
                action="escalate",
                reason="Sensitive topic requires human judgment",
                metadata={"priority": "medium"}
            )
        
        # Priority 4: Too many errors
        if error_count >= self.error_count_threshold:
            return PolicyDecision(
                action="escalate",
                reason=f"Too many errors ({error_count})",
                metadata={"priority": "medium"}
            )
        
        # Priority 5: Too many retries
        if retry_count >= self.max_retries:
            return PolicyDecision(
                action="escalate",
                reason=f"Max retries exceeded ({retry_count})",
                metadata={"priority": "medium"}
            )
        
        # Priority 6: Low confidence
        if confidence is not None and confidence < self.confidence_threshold:
            return PolicyDecision(
                action="escalate",
                reason=f"Low confidence ({confidence:.2f})",
                metadata={"priority": "low"}
            )
        
        # No escalation needed
        return PolicyDecision(
            action="proceed",
            reason="No escalation criteria met"
        )
    
    def get_escalation_urgency(
        self,
        reason: str,
        context: Dict,
    ) -> str:
        """
        Determine escalation urgency.
        
        Args:
            reason: Escalation reason
            context: Additional context
            
        Returns:
            Urgency level: "low", "medium", "high", "critical"
        """
        if "explicit request" in reason.lower():
            return "high"
        elif "frustration" in reason.lower():
            return "high"
        elif "sensitive" in reason.lower():
            return "medium"
        elif "error" in reason.lower():
            return "medium"
        else:
            return "low"


class FallbackPolicy:
    """
    Defines fallback strategies when agents fail.
    """
    
    def __init__(self):
        self.fallback_responses = {
            "order_status": "I'm having trouble accessing order information right now. Please email support@example.com with your order number, and we'll help you immediately.",
            "product_info": "I'm unable to retrieve product details at the moment. Please visit our website or contact support for product information.",
            "ticket_creation": "I can't create a ticket right now, but you can email support@example.com and our team will help you.",
            "general": "I'm experiencing technical difficulties. Please try again in a moment, or contact support@example.com for immediate assistance.",
        }
    
    def get_fallback_response(
        self,
        intent: str,
        error: Optional[str] = None,
    ) -> str:
        """
        Get fallback response for failed intent.
        
        Args:
            intent: The intent that failed
            error: Optional error message
            
        Returns:
            Fallback response text
        """
        return self.fallback_responses.get(
            intent,
            self.fallback_responses["general"]
        )
    
    def should_use_fallback(
        self,
        agent_failed: bool,
        confidence: Optional[float] = None,
    ) -> bool:
        """
        Determine if fallback should be used.
        
        Args:
            agent_failed: Whether agent execution failed
            confidence: Confidence in agent output
            
        Returns:
            True if fallback should be used
        """
        if agent_failed:
            return True
        
        if confidence is not None and confidence < 0.3:
            return True
        
        return False


class RetryPolicy:
    """
    Defines retry strategies for failed operations.
    """
    
    def __init__(
        self,
        max_retries: int = 2,
        retry_delay_ms: int = 1000,
        backoff_multiplier: float = 2.0,
    ):
        """
        Initialize retry policy.
        
        Args:
            max_retries: Maximum retry attempts
            retry_delay_ms: Initial retry delay
            backoff_multiplier: Backoff multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms
        self.backoff_multiplier = backoff_multiplier
    
    def should_retry(
        self,
        error_type: str,
        retry_count: int,
    ) -> PolicyDecision:
        """
        Determine if operation should be retried.
        
        Args:
            error_type: Type of error encountered
            retry_count: Current retry count
            
        Returns:
            PolicyDecision
        """
        # Never retry these errors
        no_retry_errors = [
            "validation_error",
            "authentication_error",
            "not_found",
        ]
        
        if error_type in no_retry_errors:
            return PolicyDecision(
                action="fallback",
                reason=f"Error type {error_type} is not retryable"
            )
        
        # Check retry count
        if retry_count >= self.max_retries:
            return PolicyDecision(
                action="fallback",
                reason=f"Max retries ({self.max_retries}) exceeded"
            )
        
        # Calculate delay
        delay = self.retry_delay_ms * (self.backoff_multiplier ** retry_count)
        
        return PolicyDecision(
            action="retry",
            reason=f"Retryable error, attempt {retry_count + 1}",
            metadata={"delay_ms": delay}
        )
    
    def get_retry_delay(self, retry_count: int) -> int:
        """Get retry delay in milliseconds."""
        return int(self.retry_delay_ms * (self.backoff_multiplier ** retry_count))


class ConfidencePolicy:
    """
    Defines confidence-based routing decisions.
    """
    
    def __init__(
        self,
        high_confidence: float = 0.8,
        medium_confidence: float = 0.6,
        low_confidence: float = 0.4,
    ):
        """
        Initialize confidence policy.
        
        Args:
            high_confidence: Threshold for high confidence
            medium_confidence: Threshold for medium confidence
            low_confidence: Threshold for low confidence
        """
        self.high_confidence = high_confidence
        self.medium_confidence = medium_confidence
        self.low_confidence = low_confidence
    
    def get_action_for_confidence(
        self,
        confidence: float,
        component: str,
    ) -> PolicyDecision:
        """
        Determine action based on confidence level.
        
        Args:
            confidence: Confidence score
            component: Component that generated confidence
            
        Returns:
            PolicyDecision
        """
        if confidence >= self.high_confidence:
            return PolicyDecision(
                action="proceed",
                reason=f"High confidence ({confidence:.2f})",
                metadata={"confidence_level": "high"}
            )
        
        elif confidence >= self.medium_confidence:
            # Medium confidence - proceed but with caution
            return PolicyDecision(
                action="proceed",
                reason=f"Medium confidence ({confidence:.2f})",
                metadata={"confidence_level": "medium", "add_disclaimer": True}
            )
        
        elif confidence >= self.low_confidence:
            # Low confidence - clarify
            return PolicyDecision(
                action="clarify",
                reason=f"Low confidence ({confidence:.2f}), needs clarification",
                metadata={"confidence_level": "low"}
            )
        
        else:
            # Very low confidence - fallback or escalate
            return PolicyDecision(
                action="fallback",
                reason=f"Very low confidence ({confidence:.2f})",
                metadata={"confidence_level": "very_low"}
            )


class PolicyManager:
    """
    Central manager for all orchestration policies.
    """
    
    def __init__(
        self,
        escalation_policy: Optional[EscalationPolicy] = None,
        fallback_policy: Optional[FallbackPolicy] = None,
        retry_policy: Optional[RetryPolicy] = None,
        confidence_policy: Optional[ConfidencePolicy] = None,
    ):
        """
        Initialize policy manager.
        
        Args:
            escalation_policy: Escalation policy
            fallback_policy: Fallback policy
            retry_policy: Retry policy
            confidence_policy: Confidence policy
        """
        self.escalation = escalation_policy or EscalationPolicy()
        self.fallback = fallback_policy or FallbackPolicy()
        self.retry = retry_policy or RetryPolicy()
        self.confidence = confidence_policy or ConfidencePolicy()
    
    def evaluate_request(
        self,
        context: Dict,
    ) -> Dict[str, PolicyDecision]:
        """
        Evaluate all policies for a request.
        
        Args:
            context: Request context
            
        Returns:
            Dictionary of policy decisions
        """
        decisions = {}
        
        # Evaluate escalation
        decisions["escalation"] = self.escalation.should_escalate(
            confidence=context.get("confidence"),
            error_count=context.get("error_count", 0),
            explicit_request=context.get("explicit_escalation_request", False),
            frustration_detected=context.get("frustration_detected", False),
        )
        
        # Evaluate confidence
        if "confidence" in context:
            decisions["confidence"] = self.confidence.get_action_for_confidence(
                confidence=context["confidence"],
                component=context.get("component", "unknown"),
            )
        
        return decisions
    
    def get_final_action(
        self,
        decisions: Dict[str, PolicyDecision],
    ) -> PolicyDecision:
        """
        Get final action from multiple policy decisions.
        
        Priority: escalate > fallback > clarify > retry > proceed
        
        Args:
            decisions: Dictionary of policy decisions
            
        Returns:
            Final PolicyDecision
        """
        # Priority order
        priority = ["escalate", "fallback", "clarify", "retry", "proceed"]
        
        for action in priority:
            for decision in decisions.values():
                if decision.action == action:
                    return decision
        
        # Default
        return PolicyDecision(
            action="proceed",
            reason="No specific policy matched"
        )