"""
Agent Orchestrator - Coordinates all agents for honeypot operation
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

import structlog

from app.config import get_settings
from app.orchestrator.model_router import ModelRouter, TaskType, get_model_router
from app.agents.state_machine import (
    StateMachine, ConversationState, StateTransition,
    ConversationContext, get_state_machine
)
from app.personas.persona_engine import PersonaEngine, PersonaType, get_persona_engine
from app.scoring.ensemble_engine import EnsembleRiskEngine, EnsembleResult, get_ensemble_engine
from app.extractors.regex_extractor import RegexExtractor, get_regex_extractor

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class EngagementResult:
    """Result of a single engagement turn"""
    conversation_id: str
    response: str
    state: str
    persona_used: str
    risk_score: float
    extracted_intel: Dict[str, List[str]]
    models_used: List[str]
    should_continue: bool
    processing_time_ms: int
    safety_warnings: List[str]


class HoneypotOrchestrator:
    """
    Main orchestrator that coordinates:
    - Planner Agent (Gemini) - Strategic planning
    - Conversation Agent (Gemini) - Response generation
    - Extraction Agent (Local LLaMA) - Entity extraction
    - Evaluator Agent (Gemini) - Safety and termination decisions
    """
    
    def __init__(self):
        self.model_router = get_model_router()
        self.state_machine = get_state_machine()
        self.persona_engine = get_persona_engine()
        self.risk_engine = get_ensemble_engine()
        self.regex_extractor = get_regex_extractor()
        
        logger.info("Honeypot orchestrator initialized")
    
    async def analyze_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EnsembleResult:
        """
        Analyze a message for scam detection (entry point)
        
        Args:
            message: The message to analyze
            context: Optional context information
            
        Returns:
            EnsembleResult with detection details
        """
        return await self.risk_engine.analyze(message, context)
    
    async def start_engagement(
        self,
        initial_message: str,
        scammer_identifier: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EngagementResult:
        """
        Start a new honeypot engagement
        
        Args:
            initial_message: The scammer's initial message
            scammer_identifier: Phone/email/ID of the scammer
            context: Additional context
            
        Returns:
            EngagementResult with first response
        """
        import time
        import uuid
        
        start_time = time.time()
        
        # Generate conversation ID
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        
        # Create conversation context
        conv_context = self.state_machine.create_context(
            conversation_id=conversation_id,
            scammer_identifier=scammer_identifier
        )
        
        # Analyze the initial message
        analysis = await self.risk_engine.analyze(initial_message, context)
        
        # Update scam score (triggers state transitions)
        self.state_machine.update_scam_score(conversation_id, analysis.risk_score)
        
        # Add the scammer's message
        self.state_machine.add_message(
            conversation_id, 'scammer', initial_message,
            {'analysis': analysis.to_dict()}
        )
        
        # Select persona based on scam type
        persona = self.persona_engine.select_persona(scam_type=analysis.scam_type)
        conv_context.persona_type = persona.persona_type.value
        
        # Extract entities from initial message
        regex_entities = self.regex_extractor.extract(initial_message)
        for entity_type, values in regex_entities.entities.items():
            for value in values:
                self.state_machine.add_intel(conversation_id, entity_type, value)
        
        # Also try LLM extraction if scam detected
        if analysis.scam_detected:
            try:
                llm_entities = await self.model_router.route_task(
                    TaskType.ENTITY_EXTRACTION,
                    text=initial_message
                )
                for entity_type, values in llm_entities.get('entities', {}).items():
                    for value in values:
                        self.state_machine.add_intel(conversation_id, entity_type, value)
            except Exception as e:
                logger.warning("LLM extraction failed", error=str(e))
        
        # Generate response using persona
        response = await self._generate_honeypot_response(
            conv_context=conv_context,
            scammer_message=initial_message,
            persona=persona
        )
        
        # Add honeypot response to conversation
        self.state_machine.add_message(
            conversation_id, 'honeypot', response,
            {'persona': persona.persona_type.value}
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return EngagementResult(
            conversation_id=conversation_id,
            response=response,
            state=conv_context.state.value,
            persona_used=persona.persona_type.value,
            risk_score=analysis.risk_score,
            extracted_intel=conv_context.extracted_entities,
            models_used=analysis.models_used + ['gemini'],
            should_continue=not conv_context.is_terminated,
            processing_time_ms=processing_time,
            safety_warnings=[]
        )
    
    async def continue_engagement(
        self,
        conversation_id: str,
        scammer_message: str
    ) -> EngagementResult:
        """
        Continue an existing honeypot engagement
        
        Args:
            conversation_id: The conversation to continue
            scammer_message: The scammer's new message
            
        Returns:
            EngagementResult with next response
        """
        import time
        
        start_time = time.time()
        models_used = []
        
        # Get conversation context
        conv_context = self.state_machine.get_context(conversation_id)
        if not conv_context:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        if conv_context.is_terminated:
            return EngagementResult(
                conversation_id=conversation_id,
                response="",
                state=conv_context.state.value,
                persona_used=conv_context.persona_type or "",
                risk_score=conv_context.scam_score,
                extracted_intel=conv_context.extracted_entities,
                models_used=[],
                should_continue=False,
                processing_time_ms=0,
                safety_warnings=["Conversation already terminated"]
            )
        
        # Add scammer message
        self.state_machine.add_message(conversation_id, 'scammer', scammer_message)
        
        # Safety check
        safety_warnings = await self._check_safety(scammer_message, conv_context)
        if conv_context.is_terminated:
            return EngagementResult(
                conversation_id=conversation_id,
                response="I need to go now. Goodbye.",
                state=conv_context.state.value,
                persona_used=conv_context.persona_type or "",
                risk_score=conv_context.scam_score,
                extracted_intel=conv_context.extracted_entities,
                models_used=[],
                should_continue=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                safety_warnings=safety_warnings
            )
        
        # Extract entities
        regex_entities = self.regex_extractor.extract(scammer_message)
        for entity_type, values in regex_entities.entities.items():
            for value in values:
                self.state_machine.add_intel(conversation_id, entity_type, value)
        models_used.append('regex')
        
        # LLM extraction for complex entities
        try:
            llm_entities = await self.model_router.route_task(
                TaskType.ENTITY_EXTRACTION,
                text=scammer_message
            )
            for entity_type, values in llm_entities.get('entities', {}).items():
                for value in values:
                    self.state_machine.add_intel(conversation_id, entity_type, value)
            models_used.append('local_llama')
        except Exception as e:
            logger.warning("LLM extraction failed", error=str(e))
        
        # Get persona
        persona_type = PersonaType(conv_context.persona_type) if conv_context.persona_type else PersonaType.SENIOR_CITIZEN
        persona = self.persona_engine.get_persona(persona_type)
        
        # Strategic planning (every 5 turns)
        if conv_context.turn_count % 5 == 0:
            try:
                plan = await self.model_router.route_task(
                    TaskType.AGENT_PLANNING,
                    scammer_profile={'identifier': conv_context.scammer_identifier},
                    current_state=conv_context.state.value,
                    extracted_intel=conv_context.extracted_entities
                )
                
                # Apply plan recommendations
                if plan.get('recommended_action') == 'terminate':
                    self.state_machine.transition(
                        conversation_id,
                        StateTransition.SAFETY_TRIGGERED,
                        {'reason': 'planner_recommendation'}
                    )
                
                models_used.append('gemini')
            except Exception as e:
                logger.warning("Planning failed", error=str(e))
        
        # Generate response
        response = await self._generate_honeypot_response(
            conv_context=conv_context,
            scammer_message=scammer_message,
            persona=persona
        )
        models_used.append('gemini')
        
        # Add human imperfections
        response = self.persona_engine.add_human_mistakes(response, persona)
        
        # Add honeypot response
        self.state_machine.add_message(
            conversation_id, 'honeypot', response,
            {'persona': persona.persona_type.value}
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return EngagementResult(
            conversation_id=conversation_id,
            response=response,
            state=conv_context.state.value,
            persona_used=persona.persona_type.value,
            risk_score=conv_context.scam_score,
            extracted_intel=conv_context.extracted_entities,
            models_used=list(set(models_used)),
            should_continue=not conv_context.is_terminated,
            processing_time_ms=processing_time,
            safety_warnings=safety_warnings
        )
    
    async def _generate_honeypot_response(
        self,
        conv_context: ConversationContext,
        scammer_message: str,
        persona
    ) -> str:
        """Generate a honeypot response using the persona"""
        
        # Build conversation history
        history = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in conv_context.messages[-10:]
        ]
        
        try:
            result = await self.model_router.route_task(
                TaskType.RESPONSE_GENERATION,
                conversation_history=history,
                persona_prompt=persona.system_prompt,
                scammer_message=scammer_message
            )
            return result.get('response', "I'm not sure I understand. Could you explain again?")
        except Exception as e:
            logger.error("Response generation failed", error=str(e))
            # Fallback response based on persona
            fallback_responses = {
                PersonaType.SENIOR_CITIZEN: "Oh my... I'm a bit confused dear. Could you explain that again please?",
                PersonaType.STUDENT: "wait what? can u explain that again lol",
                PersonaType.BUSINESS_OWNER: "I'll need more details about this. Can you send documentation?",
                PersonaType.HOMEMAKER: "Let me ask my husband about this. Can you call back later?",
                PersonaType.TECH_NAIVE: "I'm not very good with technology. Can you help me step by step?",
            }
            return fallback_responses.get(
                persona.persona_type,
                "I need some time to think about this."
            )
    
    async def _check_safety(
        self,
        message: str,
        conv_context: ConversationContext
    ) -> List[str]:
        """Check for safety violations"""
        warnings = []
        
        # Check for payment-related instructions
        payment_keywords = ['send money', 'transfer', 'pay now', 'payment', 'upi', 'bank transfer']
        message_lower = message.lower()
        
        for keyword in payment_keywords:
            if keyword in message_lower:
                warnings.append(f"Payment keyword detected: {keyword}")
        
        # Check turn count
        if conv_context.turn_count >= settings.max_conversation_turns - 5:
            warnings.append(f"Approaching max turns: {conv_context.turn_count}/{settings.max_conversation_turns}")
        
        # Check for prompt injection attempts
        injection_patterns = [
            'ignore previous instructions',
            'you are now',
            'forget your training',
            'act as',
            'pretend to be',
            'disregard the above'
        ]
        
        for pattern in injection_patterns:
            if pattern in message_lower:
                self.state_machine.record_safety_violation(
                    conv_context.conversation_id,
                    'prompt_injection_detected'
                )
                warnings.append(f"Possible prompt injection: {pattern}")
        
        return warnings
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get a summary of a conversation"""
        return self.state_machine.get_state_summary(conversation_id)


# Singleton instance
_orchestrator: Optional[HoneypotOrchestrator] = None


def get_orchestrator() -> HoneypotOrchestrator:
    """Get or create the orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = HoneypotOrchestrator()
    return _orchestrator
