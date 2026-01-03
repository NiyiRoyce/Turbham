# intent cross-checking / ambiguity resolution
"""Ambiguity detection and resolution."""

from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class AmbiguitySignal:
    """Signal indicating ambiguity in user input."""
    signal_type: str
    confidence: float
    description: str
    examples: Optional[List[str]] = None


class AmbiguityDetector:
    """
    Detects ambiguous user input that requires clarification.
    """
    
    def __init__(self, ambiguity_threshold: float = 0.6):
        """
        Initialize ambiguity detector.
        
        Args:
            ambiguity_threshold: Threshold above which input is considered ambiguous
        """
        self.ambiguity_threshold = ambiguity_threshold
    
    def detect_ambiguity(
        self,
        user_message: str,
        intent_confidence: Optional[float] = None,
        possible_intents: Optional[List[str]] = None,
    ) -> tuple[bool, float, List[AmbiguitySignal]]:
        """
        Detect if user input is ambiguous.
        
        Args:
            user_message: User's message
            intent_confidence: Confidence from intent classification
            possible_intents: List of possible intents
            
        Returns:
            (is_ambiguous, ambiguity_score, signals)
        """
        signals = []
        
        # Check 1: Low intent confidence
        if intent_confidence is not None and intent_confidence < 0.6:
            signals.append(AmbiguitySignal(
                signal_type="low_intent_confidence",
                confidence=1.0 - intent_confidence,
                description="Intent classification has low confidence",
            ))
        
        # Check 2: Multiple equally likely intents
        if possible_intents and len(possible_intents) > 1:
            signals.append(AmbiguitySignal(
                signal_type="multiple_intents",
                confidence=0.7,
                description=f"Multiple possible intents: {', '.join(possible_intents)}",
                examples=possible_intents,
            ))
        
        # Check 3: Very short message
        if len(user_message.split()) <= 3:
            signals.append(AmbiguitySignal(
                signal_type="too_short",
                confidence=0.6,
                description="Message is very short and lacks context",
            ))
        
        # Check 4: Generic questions
        generic_patterns = [
            "help",
            "question",
            "issue",
            "problem",
            "can you",
            "i need",
        ]
        if any(pattern in user_message.lower() for pattern in generic_patterns):
            if len(user_message.split()) <= 5:
                signals.append(AmbiguitySignal(
                    signal_type="generic_request",
                    confidence=0.7,
                    description="Message is generic and non-specific",
                ))
        
        # Check 5: Multiple questions
        question_count = user_message.count('?')
        if question_count > 1:
            signals.append(AmbiguitySignal(
                signal_type="multiple_questions",
                confidence=0.5,
                description="Message contains multiple questions",
            ))
        
        # Calculate overall ambiguity score
        if signals:
            ambiguity_score = sum(s.confidence for s in signals) / len(signals)
        else:
            ambiguity_score = 0.0
        
        is_ambiguous = ambiguity_score >= self.ambiguity_threshold
        
        return is_ambiguous, ambiguity_score, signals
    
    def detect_missing_context(
        self,
        user_message: str,
        context: Dict,
    ) -> tuple[bool, List[str]]:
        """
        Detect missing context that needs clarification.
        
        Args:
            user_message: User's message
            context: Current context
            
        Returns:
            (has_missing_context, missing_items)
        """
        missing = []
        message_lower = user_message.lower()
        
        # Check for references without context
        if any(word in message_lower for word in ["it", "that", "this", "they"]):
            if not context.get("conversation_history"):
                missing.append("conversation_context")
        
        # Check for order references without order ID
        if any(word in message_lower for word in ["order", "delivery", "shipment"]):
            if "order_id" not in context:
                missing.append("order_id")
        
        # Check for product references without product name
        if any(word in message_lower for word in ["product", "item"]):
            if "product_name" not in context:
                missing.append("product_name")
        
        return len(missing) > 0, missing


class ClarificationGenerator:
    """
    Generates clarification questions for ambiguous input.
    """
    
    @staticmethod
    def generate_intent_clarification(
        possible_intents: List[str],
        user_message: str,
    ) -> str:
        """
        Generate clarification for ambiguous intent.
        
        Args:
            possible_intents: List of possible intents
            user_message: Original user message
            
        Returns:
            Clarification question
        """
        intent_map = {
            "order_status": "check the status of an existing order",
            "product_info": "learn about products or their availability",
            "ticket_creation": "report an issue or get technical support",
            "returns_refunds": "process a return or refund",
            "account_management": "manage your account settings",
        }
        
        if len(possible_intents) == 2:
            intent1 = intent_map.get(possible_intents[0], possible_intents[0])
            intent2 = intent_map.get(possible_intents[1], possible_intents[1])
            
            return f"I want to help! Are you looking to {intent1}, or {intent2}?"
        
        elif len(possible_intents) > 2:
            return "I'd be happy to help! To make sure I assist you correctly, could you tell me if you're looking for:\n" + \
                   "\n".join([f"- {intent_map.get(i, i)}" for i in possible_intents[:3]])
        
        else:
            return "Could you provide a bit more detail about what you need help with?"
    
    @staticmethod
    def generate_context_clarification(
        missing_context: List[str],
    ) -> str:
        """
        Generate clarification for missing context.
        
        Args:
            missing_context: List of missing context items
            
        Returns:
            Clarification question
        """
        context_questions = {
            "order_id": "Could you provide your order number?",
            "product_name": "Which product are you asking about?",
            "conversation_context": "Could you provide more details about what you're referring to?",
            "email": "Could you provide your email address?",
        }
        
        if len(missing_context) == 1:
            return context_questions.get(
                missing_context[0],
                "Could you provide more information?"
            )
        else:
            return "To help you better, I need a bit more information:\n" + \
                   "\n".join([f"- {context_questions.get(c, c)}" for c in missing_context])
    
    @staticmethod
    def generate_generic_clarification() -> str:
        """Generate generic clarification question."""
        return "I want to make sure I understand correctly. Could you rephrase or provide more details about what you need?"


class AmbiguityResolver:
    """
    Resolves ambiguity through clarification.
    """
    
    def __init__(self):
        self.detector = AmbiguityDetector()
        self.generator = ClarificationGenerator()
    
    def analyze_and_resolve(
        self,
        user_message: str,
        intent_confidence: Optional[float] = None,
        possible_intents: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Analyze ambiguity and generate resolution strategy.
        
        Args:
            user_message: User's message
            intent_confidence: Confidence from intent classification
            possible_intents: List of possible intents
            context: Current context
            
        Returns:
            Resolution strategy dictionary
        """
        # Detect ambiguity
        is_ambiguous, score, signals = self.detector.detect_ambiguity(
            user_message,
            intent_confidence,
            possible_intents,
        )
        
        # Check for missing context
        has_missing, missing = self.detector.detect_missing_context(
            user_message,
            context or {},
        )
        
        # Generate clarification if needed
        clarification = None
        if is_ambiguous and possible_intents:
            clarification = self.generator.generate_intent_clarification(
                possible_intents,
                user_message,
            )
        elif has_missing:
            clarification = self.generator.generate_context_clarification(missing)
        elif is_ambiguous:
            clarification = self.generator.generate_generic_clarification()
        
        return {
            "requires_clarification": is_ambiguous or has_missing,
            "ambiguity_score": score,
            "signals": [
                {
                    "type": s.signal_type,
                    "confidence": s.confidence,
                    "description": s.description,
                }
                for s in signals
            ],
            "missing_context": missing if has_missing else [],
            "clarification_question": clarification,
            "severity": self._get_severity(score),
        }
    
    def _get_severity(self, ambiguity_score: float) -> str:
        """Get ambiguity severity level."""
        if ambiguity_score >= 0.8:
            return "high"
        elif ambiguity_score >= 0.6:
            return "medium"
        else:
            return "low"


class DisambiguationStrategy:
    """
    Strategy for handling disambiguation in multi-turn conversations.
    """
    
    def __init__(self):
        self.pending_clarifications: Dict[str, Dict] = {}
    
    def register_clarification(
        self,
        session_id: str,
        clarification_data: Dict,
    ):
        """
        Register pending clarification for a session.
        
        Args:
            session_id: Session identifier
            clarification_data: Clarification metadata
        """
        self.pending_clarifications[session_id] = {
            "data": clarification_data,
            "timestamp": None,  # Would use datetime
        }
    
    def has_pending_clarification(self, session_id: str) -> bool:
        """Check if session has pending clarification."""
        return session_id in self.pending_clarifications
    
    def get_pending_clarification(
        self,
        session_id: str,
    ) -> Optional[Dict]:
        """Get pending clarification for session."""
        return self.pending_clarifications.get(session_id)
    
    def resolve_clarification(
        self,
        session_id: str,
        user_response: str,
    ) -> Optional[Dict]:
        """
        Resolve pending clarification with user response.
        
        Args:
            session_id: Session identifier
            user_response: User's clarifying response
            
        Returns:
            Resolved clarification data
        """
        if session_id not in self.pending_clarifications:
            return None
        
        clarification = self.pending_clarifications.pop(session_id)
        
        # Process user response to extract resolved information
        # This is a simplified version - would be more sophisticated
        resolved = {
            "original_clarification": clarification,
            "user_response": user_response,
            "resolved": True,
        }
        
        return resolved
    
    def clear_pending(self, session_id: str):
        """Clear pending clarification for session."""
        if session_id in self.pending_clarifications:
            del self.pending_clarifications[session_id]