"""
Safety Module - Kill switches, guardrails, and ethics enforcement
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class SafetyCheckResult:
    """Result of a safety check"""
    is_safe: bool
    violations: List[str]
    risk_level: str  # 'safe', 'warning', 'critical'
    should_terminate: bool
    action_required: Optional[str] = None


class SafetyGuardrails:
    """
    Implements ethical guardrails and safety mechanisms:
    - No real payments
    - Auto-stop triggers
    - Max engagement depth
    - PII protection
    - Prompt injection detection
    """
    
    def __init__(self):
        # Kill switch state
        self.global_kill_switch = False
        self.terminated_conversations: Set[str] = set()
        
        # Daily engagement tracking
        self.daily_engagements = 0
        self.engagement_date = datetime.utcnow().date()
        
        # Blocked patterns (things we should NEVER generate)
        self.forbidden_output_patterns = [
            r'(?:my|our|the)\s+(?:bank|account)\s+(?:number|details?)\s+(?:is|are)',
            r'(?:my|our)\s+(?:upi|payment)\s+(?:id|address)\s+(?:is)',
            r'(?:here|take)\s+(?:is|are)?\s*(?:my|our|the)\s+(?:card|cvv|pin)',
            r'(?:i|we)\s+(?:will|shall|am going to)\s+(?:send|transfer|pay)',
            r'(?:sending|transferring)\s+(?:\$|₹|rs\.?|inr|usd)',
        ]
        
        # Prompt injection patterns
        self.injection_patterns = [
            r'ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions?|rules?|prompts?)',
            r'disregard\s+(?:all\s+)?(?:previous|above|prior)',
            r'you\s+are\s+now\s+(?:a|an)',
            r'forget\s+(?:everything|your\s+(?:training|instructions?))',
            r'(?:new|override|replace)\s+(?:instructions?|rules?|prompts?)',
            r'pretend\s+(?:to\s+be|you\s+are)',
            r'roleplay\s+as',
            r'\[system\]',
            r'</s>|<\|im_end\|>|<\|endoftext\|>',
        ]
        
        # Compile patterns
        self.compiled_forbidden = [re.compile(p, re.IGNORECASE) for p in self.forbidden_output_patterns]
        self.compiled_injection = [re.compile(p, re.IGNORECASE) for p in self.injection_patterns]
        
        logger.info("Safety guardrails initialized")
    
    def check_input_safety(self, message: str) -> SafetyCheckResult:
        """
        Check if an incoming message is safe to process
        
        Args:
            message: The incoming message
            
        Returns:
            SafetyCheckResult
        """
        violations = []
        should_terminate = False
        
        # Check for prompt injection
        for pattern in self.compiled_injection:
            if pattern.search(message):
                violations.append(f"Prompt injection detected: {pattern.pattern[:30]}...")
                should_terminate = True
        
        # Determine risk level
        if should_terminate:
            risk_level = 'critical'
        elif violations:
            risk_level = 'warning'
        else:
            risk_level = 'safe'
        
        return SafetyCheckResult(
            is_safe=len(violations) == 0,
            violations=violations,
            risk_level=risk_level,
            should_terminate=should_terminate,
            action_required='terminate_conversation' if should_terminate else None
        )
    
    def check_output_safety(self, response: str) -> SafetyCheckResult:
        """
        Check if a generated response is safe to send
        
        Args:
            response: The generated response
            
        Returns:
            SafetyCheckResult
        """
        violations = []
        
        # Check for forbidden patterns
        for pattern in self.compiled_forbidden:
            if pattern.search(response):
                violations.append(f"Forbidden output pattern: {pattern.pattern[:30]}...")
        
        # Check for real payment information patterns
        real_upi_pattern = r'[a-z]+@(?:ok(?:sbi|icici|axis|hdfc)|ybl|paytm|phonepe)'
        real_account_pattern = r'\b\d{9,18}\b'
        
        if re.search(real_upi_pattern, response.lower()):
            violations.append("Response contains UPI-like pattern")
        
        # Check for PII leakage
        pii_patterns = [
            (r'\b\d{12}\b', 'Aadhaar-like number'),
            (r'[A-Z]{5}\d{4}[A-Z]', 'PAN-like pattern'),
        ]
        
        for pattern, description in pii_patterns:
            if re.search(pattern, response):
                violations.append(f"Possible PII: {description}")
        
        # Determine action
        should_terminate = len(violations) > 0
        
        return SafetyCheckResult(
            is_safe=len(violations) == 0,
            violations=violations,
            risk_level='critical' if violations else 'safe',
            should_terminate=should_terminate,
            action_required='block_response' if violations else None
        )
    
    def check_engagement_limits(
        self,
        conversation_id: str,
        turn_count: int,
        started_at: datetime
    ) -> SafetyCheckResult:
        """
        Check if engagement limits have been exceeded
        """
        violations = []
        should_terminate = False
        
        # Check max turns
        if turn_count >= settings.max_conversation_turns:
            violations.append(f"Max turns reached: {turn_count}")
            should_terminate = True
        
        # Check duration
        duration = datetime.utcnow() - started_at
        max_duration = timedelta(minutes=settings.max_engagement_duration_minutes)
        
        if duration > max_duration:
            violations.append(f"Max duration exceeded: {duration}")
            should_terminate = True
        
        # Check daily limit
        self._update_daily_counter()
        if self.daily_engagements >= settings.max_daily_engagements:
            violations.append(f"Daily engagement limit reached: {self.daily_engagements}")
            should_terminate = True
        
        return SafetyCheckResult(
            is_safe=len(violations) == 0,
            violations=violations,
            risk_level='warning' if violations else 'safe',
            should_terminate=should_terminate,
            action_required='terminate_conversation' if should_terminate else None
        )
    
    def _update_daily_counter(self):
        """Reset daily counter if date changed"""
        today = datetime.utcnow().date()
        if today != self.engagement_date:
            self.daily_engagements = 0
            self.engagement_date = today
    
    def increment_daily_engagements(self):
        """Increment daily engagement counter"""
        self._update_daily_counter()
        self.daily_engagements += 1
    
    def activate_kill_switch(self, reason: str):
        """
        Activate global kill switch - stops all conversations
        """
        self.global_kill_switch = True
        logger.critical(
            "KILL SWITCH ACTIVATED",
            reason=reason,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def deactivate_kill_switch(self):
        """Deactivate global kill switch"""
        self.global_kill_switch = False
        logger.warning("Kill switch deactivated")
    
    def is_kill_switch_active(self) -> bool:
        """Check if kill switch is active"""
        return self.global_kill_switch
    
    def terminate_conversation(self, conversation_id: str, reason: str):
        """Mark a conversation as terminated"""
        self.terminated_conversations.add(conversation_id)
        logger.warning(
            "Conversation terminated by safety system",
            conversation_id=conversation_id,
            reason=reason
        )
    
    def is_conversation_terminated(self, conversation_id: str) -> bool:
        """Check if a conversation has been terminated"""
        return conversation_id in self.terminated_conversations
    
    def sanitize_response(self, response: str) -> str:
        """
        Sanitize a response by removing potentially dangerous content
        
        Args:
            response: The response to sanitize
            
        Returns:
            Sanitized response
        """
        # Remove any actual payment info patterns
        sanitized = response
        
        # Replace potential UPI IDs with placeholder
        sanitized = re.sub(
            r'[a-zA-Z0-9._]+@(?:ok(?:sbi|icici|axis|hdfc)|ybl|paytm|phonepe|upi)',
            '[UPI_REDACTED]',
            sanitized,
            flags=re.IGNORECASE
        )
        
        # Replace phone number patterns
        sanitized = re.sub(
            r'(?:\+91[-\s]?)?[6-9]\d{9}',
            '[PHONE_REDACTED]',
            sanitized
        )
        
        # Replace account number patterns (long digit sequences)
        sanitized = re.sub(
            r'\b\d{10,18}\b',
            '[ACCOUNT_REDACTED]',
            sanitized
        )
        
        return sanitized
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety system status"""
        return {
            'kill_switch_active': self.global_kill_switch,
            'daily_engagements': self.daily_engagements,
            'daily_limit': settings.max_daily_engagements,
            'terminated_conversations': len(self.terminated_conversations),
            'engagement_date': self.engagement_date.isoformat()
        }


# Singleton instance
_guardrails: Optional[SafetyGuardrails] = None


def get_safety_guardrails() -> SafetyGuardrails:
    """Get or create the safety guardrails singleton"""
    global _guardrails
    if _guardrails is None:
        _guardrails = SafetyGuardrails()
    return _guardrails
