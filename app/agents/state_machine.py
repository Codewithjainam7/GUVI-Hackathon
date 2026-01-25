"""
Conversation State Machine - Manages honeypot engagement states
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

import structlog

logger = structlog.get_logger()


class ConversationState(str, Enum):
    """States in the honeypot conversation lifecycle"""
    INITIAL = "initial"                    # First contact
    NORMAL_CHAT = "normal_chat"            # Non-scam conversation
    SCAM_SUSPECTED = "scam_suspected"      # Scam indicators detected
    HONEYPOT_ENGAGED = "honeypot_engaged"  # Actively engaging scammer
    INTEL_EXTRACTION = "intel_extraction"  # Focused on extracting info
    SAFE_TERMINATION = "safe_termination"  # Ending engagement safely
    TERMINATED = "terminated"              # Conversation ended


class StateTransition(str, Enum):
    """Possible state transitions"""
    SCAM_DETECTED = "scam_detected"
    SCAM_CONFIRMED = "scam_confirmed"
    INTEL_RECEIVED = "intel_received"
    MAX_TURNS_REACHED = "max_turns_reached"
    SAFETY_TRIGGERED = "safety_triggered"
    SCAMMER_DISENGAGED = "scammer_disengaged"
    USER_TERMINATED = "user_terminated"
    SCAM_CLEARED = "scam_cleared"


# State transition rules
TRANSITION_RULES: Dict[ConversationState, Dict[StateTransition, ConversationState]] = {
    ConversationState.INITIAL: {
        StateTransition.SCAM_DETECTED: ConversationState.SCAM_SUSPECTED,
        StateTransition.SCAM_CLEARED: ConversationState.NORMAL_CHAT,
    },
    ConversationState.NORMAL_CHAT: {
        StateTransition.SCAM_DETECTED: ConversationState.SCAM_SUSPECTED,
        StateTransition.USER_TERMINATED: ConversationState.TERMINATED,
    },
    ConversationState.SCAM_SUSPECTED: {
        StateTransition.SCAM_CONFIRMED: ConversationState.HONEYPOT_ENGAGED,
        StateTransition.SCAM_CLEARED: ConversationState.NORMAL_CHAT,
        StateTransition.SAFETY_TRIGGERED: ConversationState.SAFE_TERMINATION,
    },
    ConversationState.HONEYPOT_ENGAGED: {
        StateTransition.INTEL_RECEIVED: ConversationState.INTEL_EXTRACTION,
        StateTransition.MAX_TURNS_REACHED: ConversationState.SAFE_TERMINATION,
        StateTransition.SAFETY_TRIGGERED: ConversationState.SAFE_TERMINATION,
        StateTransition.SCAMMER_DISENGAGED: ConversationState.SAFE_TERMINATION,
    },
    ConversationState.INTEL_EXTRACTION: {
        StateTransition.MAX_TURNS_REACHED: ConversationState.SAFE_TERMINATION,
        StateTransition.SAFETY_TRIGGERED: ConversationState.SAFE_TERMINATION,
        StateTransition.SCAMMER_DISENGAGED: ConversationState.SAFE_TERMINATION,
    },
    ConversationState.SAFE_TERMINATION: {
        StateTransition.USER_TERMINATED: ConversationState.TERMINATED,
    },
}


@dataclass
class ConversationContext:
    """Context for a conversation"""
    conversation_id: str
    state: ConversationState = ConversationState.INITIAL
    turn_count: int = 0
    scam_score: float = 0.0
    persona_type: Optional[str] = None
    scammer_identifier: Optional[str] = None
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    # Intelligence
    extracted_entities: Dict[str, List[str]] = field(default_factory=dict)
    intel_count: int = 0
    
    # History
    messages: List[Dict[str, Any]] = field(default_factory=list)
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Safety
    safety_violations: List[str] = field(default_factory=list)
    is_terminated: bool = False
    termination_reason: Optional[str] = None


class StateMachine:
    """
    Finite State Machine for conversation management
    """
    
    def __init__(self, max_turns: int = 50):
        self.max_turns = max_turns
        self.contexts: Dict[str, ConversationContext] = {}
        
        logger.info("State machine initialized", max_turns=max_turns)
    
    def create_context(
        self,
        conversation_id: str,
        scammer_identifier: Optional[str] = None
    ) -> ConversationContext:
        """Create a new conversation context"""
        context = ConversationContext(
            conversation_id=conversation_id,
            scammer_identifier=scammer_identifier
        )
        self.contexts[conversation_id] = context
        
        logger.info(
            "Conversation context created",
            conversation_id=conversation_id,
            state=context.state.value
        )
        
        return context
    
    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get existing conversation context"""
        return self.contexts.get(conversation_id)
    
    def transition(
        self,
        conversation_id: str,
        trigger: StateTransition,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """
        Attempt a state transition
        
        Args:
            conversation_id: The conversation to transition
            trigger: The transition trigger
            metadata: Additional metadata for the transition
            
        Returns:
            Updated ConversationContext
        """
        context = self.contexts.get(conversation_id)
        if not context:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        current_state = context.state
        valid_transitions = TRANSITION_RULES.get(current_state, {})
        
        if trigger not in valid_transitions:
            logger.warning(
                "Invalid state transition",
                conversation_id=conversation_id,
                current_state=current_state.value,
                trigger=trigger.value
            )
            return context
        
        new_state = valid_transitions[trigger]
        
        # Record transition
        context.state_history.append({
            'from_state': current_state.value,
            'to_state': new_state.value,
            'trigger': trigger.value,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata
        })
        
        # Update state
        context.state = new_state
        context.last_activity = datetime.utcnow()
        
        # Handle terminal states
        if new_state == ConversationState.TERMINATED:
            context.is_terminated = True
            context.termination_reason = trigger.value
        
        logger.info(
            "State transition",
            conversation_id=conversation_id,
            from_state=current_state.value,
            to_state=new_state.value,
            trigger=trigger.value
        )
        
        return context
    
    def add_message(
        self,
        conversation_id: str,
        role: str,  # 'scammer' or 'honeypot'
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """Add a message to the conversation"""
        context = self.contexts.get(conversation_id)
        if not context:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'turn': context.turn_count,
            'metadata': metadata or {}
        }
        
        context.messages.append(message)
        context.turn_count += 1
        context.last_activity = datetime.utcnow()
        
        # Check max turns
        if context.turn_count >= self.max_turns:
            self.transition(conversation_id, StateTransition.MAX_TURNS_REACHED)
        
        return context
    
    def add_intel(
        self,
        conversation_id: str,
        entity_type: str,
        value: str
    ) -> ConversationContext:
        """Add extracted intelligence to the conversation"""
        context = self.contexts.get(conversation_id)
        if not context:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        if entity_type not in context.extracted_entities:
            context.extracted_entities[entity_type] = []
        
        if value not in context.extracted_entities[entity_type]:
            context.extracted_entities[entity_type].append(value)
            context.intel_count += 1
            
            logger.info(
                "Intel extracted",
                conversation_id=conversation_id,
                entity_type=entity_type,
                intel_count=context.intel_count
            )
            
            # Transition to extraction state if in honeypot mode
            if context.state == ConversationState.HONEYPOT_ENGAGED:
                self.transition(conversation_id, StateTransition.INTEL_RECEIVED)
        
        return context
    
    def update_scam_score(
        self,
        conversation_id: str,
        score: float
    ) -> ConversationContext:
        """Update the scam score for a conversation"""
        context = self.contexts.get(conversation_id)
        if not context:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        context.scam_score = score
        
        # Auto-transition based on score
        if context.state == ConversationState.INITIAL:
            if score > 0.7:
                self.transition(conversation_id, StateTransition.SCAM_DETECTED)
            else:
                self.transition(conversation_id, StateTransition.SCAM_CLEARED)
        elif context.state == ConversationState.SCAM_SUSPECTED:
            if score > 0.8:
                self.transition(conversation_id, StateTransition.SCAM_CONFIRMED)
            elif score < 0.4:
                self.transition(conversation_id, StateTransition.SCAM_CLEARED)
        
        return context
    
    def record_safety_violation(
        self,
        conversation_id: str,
        violation: str
    ) -> ConversationContext:
        """Record a safety violation"""
        context = self.contexts.get(conversation_id)
        if not context:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        context.safety_violations.append(violation)
        
        logger.warning(
            "Safety violation recorded",
            conversation_id=conversation_id,
            violation=violation,
            total_violations=len(context.safety_violations)
        )
        
        # Auto-terminate on critical violations
        critical_violations = [
            'payment_attempted',
            'pii_leaked',
            'prompt_injection_detected'
        ]
        
        if violation in critical_violations:
            self.transition(
                conversation_id,
                StateTransition.SAFETY_TRIGGERED,
                {'violation': violation}
            )
        
        return context
    
    def get_state_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation state"""
        context = self.contexts.get(conversation_id)
        if not context:
            return {'error': 'Conversation not found'}
        
        return {
            'conversation_id': conversation_id,
            'state': context.state.value,
            'turn_count': context.turn_count,
            'scam_score': context.scam_score,
            'persona': context.persona_type,
            'intel_count': context.intel_count,
            'is_terminated': context.is_terminated,
            'duration_seconds': (datetime.utcnow() - context.started_at).total_seconds(),
            'safety_violations': len(context.safety_violations)
        }


# Singleton instance
_state_machine: Optional[StateMachine] = None


def get_state_machine() -> StateMachine:
    """Get or create the state machine singleton"""
    global _state_machine
    if _state_machine is None:
        _state_machine = StateMachine()
    return _state_machine
