# confidence scoring utilities
"""Confidence scoring and aggregation for orchestration decisions."""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence levels for decision making."""
    VERY_HIGH = "very_high"  # >= 0.9
    HIGH = "high"            # >= 0.7
    MEDIUM = "medium"        # >= 0.5
    LOW = "low"              # >= 0.3
    VERY_LOW = "very_low"    # < 0.3


@dataclass
class ConfidenceScore:
    """Confidence score with metadata."""
    score: float  # 0.0 to 1.0
    component: str
    reasoning: Optional[str] = None
    
    def get_level(self) -> ConfidenceLevel:
        """Get confidence level from score."""
        if self.score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.score >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def is_acceptable(self, threshold: float = 0.7) -> bool:
        """Check if confidence meets threshold."""
        return self.score >= threshold


class ConfidenceAggregator:
    """
    Aggregates confidence scores from multiple agents/components.
    """
    
    def __init__(self, default_threshold: float = 0.7):
        """
        Initialize aggregator.
        
        Args:
            default_threshold: Default confidence threshold
        """
        self.default_threshold = default_threshold
        self.scores: Dict[str, ConfidenceScore] = {}
    
    def add_score(
        self,
        component: str,
        score: float,
        reasoning: Optional[str] = None,
    ):
        """
        Add confidence score.
        
        Args:
            component: Component name (e.g., "intent_agent")
            score: Confidence score (0.0 to 1.0)
            reasoning: Optional reasoning
        """
        self.scores[component] = ConfidenceScore(
            score=score,
            component=component,
            reasoning=reasoning,
        )
    
    def get_score(self, component: str) -> Optional[float]:
        """Get score for a component."""
        if component in self.scores:
            return self.scores[component].score
        return None
    
    def get_weighted_average(
        self,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculate weighted average of all scores.
        
        Args:
            weights: Optional component weights (default: equal weights)
            
        Returns:
            Weighted average confidence score
        """
        if not self.scores:
            return 0.0
        
        if weights is None:
            # Equal weights
            return sum(s.score for s in self.scores.values()) / len(self.scores)
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for component, score_obj in self.scores.items():
            weight = weights.get(component, 1.0)
            weighted_sum += score_obj.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def get_minimum(self) -> Optional[float]:
        """Get minimum confidence score."""
        if not self.scores:
            return None
        return min(s.score for s in self.scores.values())
    
    def get_maximum(self) -> Optional[float]:
        """Get maximum confidence score."""
        if not self.scores:
            return None
        return max(s.score for s in self.scores.values())
    
    def meets_threshold(
        self,
        threshold: Optional[float] = None,
        require_all: bool = False,
    ) -> bool:
        """
        Check if confidence meets threshold.
        
        Args:
            threshold: Confidence threshold (uses default if not provided)
            require_all: If True, all scores must meet threshold;
                        If False, weighted average must meet threshold
            
        Returns:
            True if threshold is met
        """
        threshold = threshold or self.default_threshold
        
        if not self.scores:
            return False
        
        if require_all:
            return all(s.score >= threshold for s in self.scores.values())
        else:
            return self.get_weighted_average() >= threshold
    
    def get_lowest_scoring_component(self) -> Optional[str]:
        """Get component with lowest confidence."""
        if not self.scores:
            return None
        return min(self.scores.items(), key=lambda x: x[1].score)[0]
    
    def get_report(self) -> Dict:
        """Get detailed confidence report."""
        if not self.scores:
            return {
                "overall": 0.0,
                "level": ConfidenceLevel.VERY_LOW.value,
                "scores": {},
            }
        
        overall = self.get_weighted_average()
        
        return {
            "overall": overall,
            "level": self._score_to_level(overall).value,
            "minimum": self.get_minimum(),
            "maximum": self.get_maximum(),
            "scores": {
                component: {
                    "score": score.score,
                    "level": score.get_level().value,
                    "reasoning": score.reasoning,
                }
                for component, score in self.scores.items()
            },
            "components_count": len(self.scores),
        }
    
    def _score_to_level(self, score: float) -> ConfidenceLevel:
        """Convert score to confidence level."""
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


class ConfidencePolicy:
    """
    Defines confidence-based decision policies.
    """
    
    def __init__(
        self,
        intent_threshold: float = 0.7,
        knowledge_threshold: float = 0.6,
        escalation_threshold: float = 0.5,
    ):
        """
        Initialize confidence policy.
        
        Args:
            intent_threshold: Threshold for intent classification
            knowledge_threshold: Threshold for knowledge answers
            escalation_threshold: Threshold below which to escalate
        """
        self.intent_threshold = intent_threshold
        self.knowledge_threshold = knowledge_threshold
        self.escalation_threshold = escalation_threshold
    
    def should_clarify_intent(self, confidence: float) -> bool:
        """Determine if intent needs clarification."""
        return confidence < self.intent_threshold
    
    def should_use_answer(self, confidence: float) -> bool:
        """Determine if answer is confident enough to use."""
        return confidence >= self.knowledge_threshold
    
    def should_escalate(self, confidence: float) -> bool:
        """Determine if low confidence requires escalation."""
        return confidence < self.escalation_threshold
    
    def get_action(
        self,
        component: str,
        confidence: float,
    ) -> str:
        """
        Get recommended action based on confidence.
        
        Args:
            component: Component name
            confidence: Confidence score
            
        Returns:
            Action string: "proceed", "clarify", "retry", "escalate"
        """
        if component == "intent":
            if confidence >= self.intent_threshold:
                return "proceed"
            elif confidence >= self.escalation_threshold:
                return "clarify"
            else:
                return "escalate"
        
        elif component == "knowledge":
            if confidence >= self.knowledge_threshold:
                return "proceed"
            elif confidence >= self.escalation_threshold:
                return "retry"
            else:
                return "escalate"
        
        else:
            # Generic logic
            if confidence >= 0.7:
                return "proceed"
            elif confidence >= 0.5:
                return "retry"
            else:
                return "escalate"


class ConfidenceBooster:
    """
    Adjusts confidence scores based on additional signals.
    """
    
    @staticmethod
    def boost_from_history(
        base_confidence: float,
        history_match: bool,
    ) -> float:
        """
        Boost confidence if matches conversation history.
        
        Args:
            base_confidence: Base confidence score
            history_match: Whether request matches conversation context
            
        Returns:
            Boosted confidence
        """
        if history_match:
            return min(1.0, base_confidence + 0.1)
        return base_confidence
    
    @staticmethod
    def boost_from_metadata(
        base_confidence: float,
        has_order_id: bool = False,
        has_user_context: bool = False,
    ) -> float:
        """
        Boost confidence from metadata signals.
        
        Args:
            base_confidence: Base confidence score
            has_order_id: Whether order ID is present
            has_user_context: Whether user context is available
            
        Returns:
            Boosted confidence
        """
        boost = 0.0
        if has_order_id:
            boost += 0.05
        if has_user_context:
            boost += 0.05
        
        return min(1.0, base_confidence + boost)
    
    @staticmethod
    def penalize_from_ambiguity(
        base_confidence: float,
        ambiguity_score: float,
    ) -> float:
        """
        Penalize confidence for ambiguous input.
        
        Args:
            base_confidence: Base confidence score
            ambiguity_score: Ambiguity score (0.0 to 1.0, higher = more ambiguous)
            
        Returns:
            Adjusted confidence
        """
        penalty = ambiguity_score * 0.2  # Max 0.2 penalty
        return max(0.0, base_confidence - penalty)
    
    @staticmethod
    def adjust_confidence(
        base_confidence: float,
        adjustments: Dict[str, float],
    ) -> float:
        """
        Apply multiple confidence adjustments.
        
        Args:
            base_confidence: Base confidence score
            adjustments: Dict of adjustment factors
            
        Returns:
            Final adjusted confidence
        """
        adjusted = base_confidence
        
        for factor, value in adjustments.items():
            if factor == "boost":
                adjusted = min(1.0, adjusted + value)
            elif factor == "penalty":
                adjusted = max(0.0, adjusted - value)
            elif factor == "multiply":
                adjusted *= value
        
        return max(0.0, min(1.0, adjusted))