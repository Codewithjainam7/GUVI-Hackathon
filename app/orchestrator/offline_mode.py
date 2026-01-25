"""
Offline Mode - Fallback when LLMs are unavailable
"""

from typing import Any, Dict, List, Optional

import structlog

from app.detectors.rule_based import get_rule_based_detector
from app.extractors.regex_extractor import get_regex_extractor
from app.personas.persona_engine import get_persona_engine, PersonaType

logger = structlog.get_logger()


class OfflineMode:
    """
    Fallback mode when LLMs are not available
    
    Uses:
    - Rule-based detection only
    - Regex extraction only
    - Pre-defined response templates
    """
    
    def __init__(self):
        self.rule_detector = get_rule_based_detector()
        self.regex_extractor = get_regex_extractor()
        self.persona_engine = get_persona_engine()
        
        # Pre-defined response templates by persona
        self.response_templates = {
            PersonaType.SENIOR_CITIZEN: [
                "Oh my dear... I don't quite understand. Could you explain again please?",
                "Let me ask my son about this first. He knows about these things...",
                "This sounds interesting but I need to think about it. Can you call back tomorrow?",
                "I'm a bit confused... What do I need to do exactly?",
                "Oh! That's a lot of money. I better check with my bank first.",
                "Dear, I'm not very good with technology. Can you speak slower please?",
            ],
            PersonaType.STUDENT: [
                "wait what? can u explain that again lol",
                "sounds cool but i need to check with my parents first",
                "yo that's a lot of money, u sure this is legit?",
                "idk man, my friends said to be careful with stuff like this",
                "can u send more details? like on whatsapp or something",
                "tbh i don't have that much money rn, maybe later?",
            ],
            PersonaType.BUSINESS_OWNER: [
                "I need to see some documentation before proceeding.",
                "Can you send me this in writing? I'll have my accountant review it.",
                "What company are you from? I need to verify this.",
                "This sounds interesting but I need proper paperwork.",
                "Let me consult with my CA first. Give me your contact details.",
                "I don't make decisions this quickly. Send me an email with all details.",
            ],
            PersonaType.HOMEMAKER: [
                "Oh, let me ask my husband about this first.",
                "I need to discuss this with my family before deciding.",
                "Can you call back later? My husband handles these financial matters.",
                "This is too big a decision for me alone. I'll talk to my husband.",
                "Is there a number I can call you back on? After talking to my family?",
                "I'm not sure about this. Let me think and get back to you.",
            ],
            PersonaType.TECH_NAIVE: [
                "I don't understand all this technical stuff. Can you explain simply?",
                "How do I do that? I'm not good with computers.",
                "Can someone come to my house and help me with this?",
                "I'm afraid I might press the wrong button. What if I make a mistake?",
                "My nephew usually helps me with these things. Can I ask him first?",
                "I heard about scams on TV. How do I know this is real?",
            ],
        }
        
        # Detection response templates
        self.detection_responses = {
            'high_risk': "This message shows strong indicators of a scam. Proceed with caution.",
            'medium_risk': "This message has some suspicious elements. Verify before responding.",
            'low_risk': "This message appears normal but stay vigilant.",
        }
        
        logger.info("Offline mode initialized")
    
    def analyze_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze message using rule-based detection only
        
        Args:
            message: Message to analyze
            context: Optional context
            
        Returns:
            Analysis result
        """
        # Run rule-based detection
        rule_result = self.rule_detector.detect(message, context)
        
        # Extract entities
        entities = self.regex_extractor.extract(message)
        
        # Determine risk level
        if rule_result.score >= 0.7:
            risk_level = 'high'
            scam_detected = True
        elif rule_result.score >= 0.4:
            risk_level = 'medium'
            scam_detected = True
        else:
            risk_level = 'low'
            scam_detected = False
        
        return {
            'scam_detected': scam_detected,
            'risk_score': rule_result.score,
            'confidence': 0.6,  # Lower confidence in offline mode
            'risk_level': risk_level,
            'reasons': [s.description for s in rule_result.signals],
            'extracted_entities': entities.entities,
            'models_used': ['rule_based', 'regex'],
            'offline_mode': True,
            'explanation': self.detection_responses.get(f'{risk_level}_risk', 'Analysis complete.')
        }
    
    def generate_response(
        self,
        persona_type: Optional[PersonaType] = None,
        turn: int = 0,
        scammer_message: Optional[str] = None
    ) -> str:
        """
        Generate a response using templates
        
        Args:
            persona_type: The persona to use
            turn: Conversation turn number
            scammer_message: Scammer's message (for context)
            
        Returns:
            Response string
        """
        import random
        
        # Default to senior citizen
        persona = persona_type or PersonaType.SENIOR_CITIZEN
        templates = self.response_templates.get(persona, self.response_templates[PersonaType.SENIOR_CITIZEN])
        
        # Select based on turn (cycle through templates)
        index = turn % len(templates)
        response = templates[index]
        
        # Add some variation
        if random.random() < 0.3:
            # Add typo for realism
            typos = [
                (response, response.replace('the', 'teh', 1)),
                (response, response.replace('you', 'yuo', 1)),
                (response, response + '..'),
            ]
            response = random.choice(typos)[1]
        
        return response
    
    def continue_conversation(
        self,
        conversation_id: str,
        scammer_message: str,
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Continue a conversation in offline mode
        
        Args:
            conversation_id: Conversation ID
            scammer_message: Scammer's new message
            conversation_state: Current state
            
        Returns:
            Response data
        """
        # Analyze incoming message
        analysis = self.analyze_message(scammer_message)
        
        # Extract entities
        entities = self.regex_extractor.extract(scammer_message)
        
        # Get persona
        persona_type = PersonaType(conversation_state.get('persona_type', 'senior_citizen'))
        turn = conversation_state.get('turn_count', 0)
        
        # Generate response
        response = self.generate_response(persona_type, turn, scammer_message)
        
        return {
            'conversation_id': conversation_id,
            'response': response,
            'persona_used': persona_type.value,
            'state': conversation_state.get('state', 'honeypot_engaged'),
            'extracted_intel': entities.entities,
            'models_used': ['rule_based', 'regex', 'templates'],
            'should_continue': turn < 20,  # Max 20 turns in offline mode
            'offline_mode': True,
            'risk_score': analysis['risk_score'],
            'safety_warnings': ['Running in offline mode - limited capabilities']
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get offline mode status"""
        return {
            'mode': 'offline',
            'capabilities': [
                'rule_based_detection',
                'regex_extraction',
                'template_responses'
            ],
            'limitations': [
                'no_llm_classification',
                'no_contextual_responses',
                'limited_extraction_accuracy'
            ],
            'persona_count': len(self.response_templates),
            'template_count': sum(len(t) for t in self.response_templates.values())
        }


# Singleton instance
_offline_mode: Optional[OfflineMode] = None


def get_offline_mode() -> OfflineMode:
    """Get or create offline mode singleton"""
    global _offline_mode
    if _offline_mode is None:
        _offline_mode = OfflineMode()
    return _offline_mode
