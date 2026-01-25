"""
Rule-Based Scam Detection - Layer 1
Fast heuristic detection using patterns and keywords
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


@dataclass
class DetectionSignal:
    """A single detection signal"""
    signal_type: str
    description: str
    weight: float
    matched_text: Optional[str] = None
    confidence: float = 1.0


@dataclass
class RuleBasedResult:
    """Result from rule-based detection"""
    score: float
    signals: List[DetectionSignal] = field(default_factory=list)
    is_suspicious: bool = False
    
    def add_signal(self, signal: DetectionSignal):
        self.signals.append(signal)
        self._recalculate_score()
    
    def _recalculate_score(self):
        if not self.signals:
            self.score = 0.0
            return
        
        total_weight = sum(s.weight * s.confidence for s in self.signals)
        max_possible = len(self.signals) * 1.0  # Max weight is 1.0
        self.score = min(total_weight / max(max_possible, 1), 1.0)
        self.is_suspicious = self.score > 0.3


class RuleBasedDetector:
    """
    Layer 1: Fast rule-based scam detection
    Uses patterns, keywords, and heuristics
    """
    
    def __init__(self):
        # Urgency patterns
        self.urgency_patterns = [
            (r'\b(urgent|immediately|right now|act now|hurry|asap|limited time)\b', 'urgency', 0.4),
            (r'\b(last chance|final notice|expires? today|deadline)\b', 'urgency', 0.5),
            (r'\b(don\'t wait|don\'t delay|time sensitive|act fast)\b', 'urgency', 0.4),
            (r'\b(within \d+ hours?|within \d+ minutes?)\b', 'urgency', 0.5),
        ]
        
        # Payment/money patterns
        self.payment_patterns = [
            (r'\b(send money|transfer funds?|wire transfer|payment required)\b', 'payment_request', 0.7),
            (r'\b(bank account|account number|routing number)\b', 'financial_info_request', 0.6),
            (r'\b(upi|@paytm|@phonepe|@upi|@ybl|@oksbi|@okicici)\b', 'upi_mention', 0.5),
            (r'\b(pay now|pay immediately|make payment|send \$?\d+)\b', 'payment_request', 0.7),
            (r'\b(processing fee|advance fee|registration fee|clearance fee)\b', 'fee_request', 0.8),
            (r'\b(gift cards?|itunes|google play cards?|amazon cards?)\b', 'gift_card_request', 0.9),
        ]
        
        # Prize/lottery patterns
        self.prize_patterns = [
            (r'\b(you\'ve won|you have won|winner|congratulations)\b', 'prize_claim', 0.6),
            (r'\b(lottery|jackpot|prize money|cash prize)\b', 'lottery_scam', 0.8),
            (r'\b(million dollars?|lakh rupees?|crore rupees?)\b', 'large_amount', 0.5),
            (r'\b(selected|chosen|lucky winner|random selection)\b', 'prize_claim', 0.5),
        ]
        
        # Impersonation patterns
        self.impersonation_patterns = [
            (r'\b(income tax|it department|irs|tax authority)\b', 'tax_impersonation', 0.7),
            (r'\b(rbi|reserve bank|central bank)\b', 'bank_impersonation', 0.7),
            (r'\b(police|cyber cell|crime branch|fbi|cia)\b', 'authority_impersonation', 0.6),
            (r'\b(microsoft|apple|google|amazon) (support|team|security)\b', 'tech_impersonation', 0.7),
            (r'\b(customer care|helpdesk|technical support)\b', 'support_impersonation', 0.4),
        ]
        
        # Threat patterns
        self.threat_patterns = [
            (r'\b(arrest|legal action|police complaint|case filed)\b', 'threat', 0.7),
            (r'\b(account (blocked|suspended|frozen)|access denied)\b', 'threat', 0.6),
            (r'\b(warrant|summons|court order)\b', 'legal_threat', 0.8),
            (r'\b(penalty|fine of|charged with)\b', 'threat', 0.5),
        ]
        
        # Personal info request patterns
        self.info_request_patterns = [
            (r'\b(otp|one time password|verification code)\b', 'otp_request', 0.8),
            (r'\b(cvv|card number|expiry date|pin number)\b', 'card_info_request', 0.9),
            (r'\b(aadhaar|pan card|passport number|ssn)\b', 'id_request', 0.7),
            (r'\b(password|login credentials|username)\b', 'credential_request', 0.8),
        ]
        
        # Suspicious link patterns
        self.link_patterns = [
            (r'bit\.ly/\w+', 'shortened_link', 0.4),
            (r'tinyurl\.com/\w+', 'shortened_link', 0.4),
            (r'click here|click this link|click below', 'click_bait', 0.3),
            (r'http[s]?://[^\s]+\.(tk|ml|ga|cf|gq)', 'suspicious_tld', 0.6),
        ]
        
        # Compile all patterns
        self._compile_patterns()
        
        logger.info("Rule-based detector initialized")
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        self.compiled_patterns: List[Tuple[re.Pattern, str, str, float]] = []
        
        pattern_groups = [
            (self.urgency_patterns, 'urgency'),
            (self.payment_patterns, 'financial'),
            (self.prize_patterns, 'prize'),
            (self.impersonation_patterns, 'impersonation'),
            (self.threat_patterns, 'threat'),
            (self.info_request_patterns, 'info_request'),
            (self.link_patterns, 'link'),
        ]
        
        for patterns, category in pattern_groups:
            for pattern, signal_type, weight in patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    self.compiled_patterns.append((compiled, category, signal_type, weight))
                except re.error as e:
                    logger.warning(f"Failed to compile pattern: {pattern}", error=str(e))
    
    def detect(self, message: str, context: Optional[Dict[str, Any]] = None) -> RuleBasedResult:
        """
        Analyze a message for scam indicators
        
        Args:
            message: The message to analyze
            context: Optional context (sender info, etc.)
            
        Returns:
            RuleBasedResult with score and signals
        """
        result = RuleBasedResult(score=0.0)
        
        # Normalize message
        normalized = message.lower().strip()
        
        # Check all patterns
        for pattern, category, signal_type, weight in self.compiled_patterns:
            matches = pattern.findall(normalized)
            if matches:
                # Get first match for display
                matched_text = matches[0] if isinstance(matches[0], str) else matches[0][0]
                
                signal = DetectionSignal(
                    signal_type=signal_type,
                    description=f"{category.title()}: {signal_type.replace('_', ' ')}",
                    weight=weight,
                    matched_text=matched_text,
                    confidence=min(1.0, 0.5 + (len(matches) * 0.1))
                )
                result.add_signal(signal)
        
        # Additional heuristic checks
        self._check_heuristics(normalized, result)
        
        # Context-based adjustments
        if context:
            self._apply_context(context, result)
        
        logger.debug(
            "Rule-based detection complete",
            score=result.score,
            signal_count=len(result.signals),
            is_suspicious=result.is_suspicious
        )
        
        return result
    
    def _check_heuristics(self, message: str, result: RuleBasedResult):
        """Apply additional heuristic checks"""
        
        # Check for ALL CAPS (common in scams)
        words = message.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 2]
        if len(caps_words) > 3:
            result.add_signal(DetectionSignal(
                signal_type='excessive_caps',
                description='Excessive use of capital letters',
                weight=0.3,
                matched_text=' '.join(caps_words[:3]),
                confidence=0.7
            ))
        
        # Check for excessive punctuation
        exclamation_count = message.count('!')
        if exclamation_count > 3:
            result.add_signal(DetectionSignal(
                signal_type='excessive_punctuation',
                description='Excessive exclamation marks',
                weight=0.2,
                matched_text=f"{exclamation_count} exclamation marks",
                confidence=0.6
            ))
        
        # Check message length (very short messages with links are suspicious)
        if len(message) < 50 and ('http' in message or 'www' in message):
            result.add_signal(DetectionSignal(
                signal_type='short_with_link',
                description='Short message with link',
                weight=0.4,
                confidence=0.5
            ))
        
        # Check for phone numbers (Indian format)
        phone_pattern = r'(\+91[-\s]?)?[6-9]\d{9}'
        phones = re.findall(phone_pattern, message)
        if phones:
            result.add_signal(DetectionSignal(
                signal_type='phone_number',
                description='Phone number detected',
                weight=0.2,  # Not inherently suspicious
                matched_text=phones[0] if phones else None,
                confidence=0.9
            ))
    
    def _apply_context(self, context: Dict[str, Any], result: RuleBasedResult):
        """Apply context-based adjustments to scoring"""
        
        # Unknown sender is more suspicious
        if context.get('is_unknown_sender'):
            for signal in result.signals:
                signal.weight *= 1.2
            result._recalculate_score()
        
        # First message from sender is more suspicious if it contains payment requests
        if context.get('is_first_message'):
            payment_signals = [s for s in result.signals if 'payment' in s.signal_type or 'fee' in s.signal_type]
            if payment_signals:
                result.add_signal(DetectionSignal(
                    signal_type='first_message_payment',
                    description='Payment request in first message',
                    weight=0.4,
                    confidence=0.8
                ))


# Singleton instance
_detector: Optional[RuleBasedDetector] = None


def get_rule_based_detector() -> RuleBasedDetector:
    """Get or create the rule-based detector singleton"""
    global _detector
    if _detector is None:
        _detector = RuleBasedDetector()
    return _detector
