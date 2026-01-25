"""
Regex-Based Entity Extraction - Baseline extractor
Fast extraction of common patterns without LLM
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import structlog

logger = structlog.get_logger()


@dataclass
class ExtractedEntity:
    """A single extracted entity"""
    entity_type: str
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    raw_match: str


@dataclass
class ExtractionResult:
    """Result from entity extraction"""
    entities: Dict[str, List[str]] = field(default_factory=dict)
    detailed_entities: List[ExtractedEntity] = field(default_factory=list)
    confidence: float = 0.0
    
    def add_entity(self, entity: ExtractedEntity):
        self.detailed_entities.append(entity)
        
        if entity.entity_type not in self.entities:
            self.entities[entity.entity_type] = []
        
        # Avoid duplicates
        if entity.value not in self.entities[entity.entity_type]:
            self.entities[entity.entity_type].append(entity.value)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entities': self.entities,
            'confidence': self.confidence,
            'entity_count': sum(len(v) for v in self.entities.values())
        }


class RegexExtractor:
    """
    Fast regex-based entity extraction for common patterns
    Used as Layer 1 before LLM extraction
    """
    
    def __init__(self):
        # UPI ID patterns
        self.upi_patterns = [
            # Standard UPI format: name@provider
            r'[a-zA-Z0-9._-]+@(paytm|phonepe|upi|ybl|oksbi|okicici|okaxis|okhdfcbank|axl|ibl|sbi|apl|waicici|wahdfcbank|waaxis|wasbi|axisbank|hdfcbank|icici|kotak|indus)',
        ]
        
        # Indian phone number patterns
        self.phone_patterns = [
            r'(?:\+91[-\s]?)?[6-9]\d{9}',  # +91-9876543210 or 9876543210
            r'(?:\+91[-\s]?)?\d{5}[-\s]?\d{5}',  # +91-98765-43210
        ]
        
        # Bank account patterns
        self.bank_account_patterns = [
            r'\b\d{9,18}\b',  # 9-18 digit numbers (context-dependent)
        ]
        
        # IFSC code patterns
        self.ifsc_patterns = [
            r'\b[A-Z]{4}0[A-Z0-9]{6}\b',  # SBIN0001234 format
        ]
        
        # Email patterns
        self.email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]
        
        # URL patterns
        self.url_patterns = [
            r'https?://[^\s<>"\']+',
            r'www\.[^\s<>"\']+',
            r'bit\.ly/[a-zA-Z0-9]+',
            r'tinyurl\.com/[a-zA-Z0-9]+',
        ]
        
        # Amount patterns (Indian currency)
        self.amount_patterns = [
            r'(?:Rs\.?|₹|INR)\s*[\d,]+(?:\.\d{2})?',  # Rs. 1,00,000 or ₹50000
            r'[\d,]+(?:\.\d{2})?\s*(?:rupees?|rs\.?|inr)',  # 50000 rupees
            r'(?:\$|USD)\s*[\d,]+(?:\.\d{2})?',  # $1000
        ]
        
        # Compile patterns
        self._compile_patterns()
        
        logger.info("Regex extractor initialized")
    
    def _compile_patterns(self):
        """Compile all regex patterns"""
        self.compiled = {
            'upi_id': [re.compile(p, re.IGNORECASE) for p in self.upi_patterns],
            'phone_number': [re.compile(p) for p in self.phone_patterns],
            'bank_account': [re.compile(p) for p in self.bank_account_patterns],
            'ifsc_code': [re.compile(p) for p in self.ifsc_patterns],
            'email': [re.compile(p, re.IGNORECASE) for p in self.email_patterns],
            'url': [re.compile(p, re.IGNORECASE) for p in self.url_patterns],
            'amount': [re.compile(p, re.IGNORECASE) for p in self.amount_patterns],
        }
    
    def extract(self, text: str) -> ExtractionResult:
        """
        Extract all entities from text
        
        Args:
            text: The text to extract from
            
        Returns:
            ExtractionResult with all found entities
        """
        result = ExtractionResult()
        
        for entity_type, patterns in self.compiled.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    value = match.group(0)
                    
                    # Validate and normalize
                    normalized = self._normalize_entity(entity_type, value)
                    if normalized:
                        # Calculate confidence based on pattern specificity
                        confidence = self._calculate_confidence(entity_type, value)
                        
                        entity = ExtractedEntity(
                            entity_type=entity_type,
                            value=normalized,
                            confidence=confidence,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            raw_match=value
                        )
                        result.add_entity(entity)
        
        # Calculate overall confidence
        if result.detailed_entities:
            result.confidence = sum(e.confidence for e in result.detailed_entities) / len(result.detailed_entities)
        
        logger.debug(
            "Regex extraction complete",
            entity_count=len(result.detailed_entities),
            types=list(result.entities.keys())
        )
        
        return result
    
    def _normalize_entity(self, entity_type: str, value: str) -> Optional[str]:
        """Normalize and validate an entity value"""
        
        if entity_type == 'phone_number':
            # Normalize to +91-XXXXXXXXXX format
            digits = re.sub(r'\D', '', value)
            if len(digits) == 10:
                return f"+91-{digits}"
            elif len(digits) == 12 and digits.startswith('91'):
                return f"+91-{digits[2:]}"
            return None
        
        elif entity_type == 'upi_id':
            # Lowercase and validate
            normalized = value.lower().strip()
            if '@' in normalized:
                return normalized
            return None
        
        elif entity_type == 'email':
            # Basic email validation
            normalized = value.lower().strip()
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', normalized):
                return normalized
            return None
        
        elif entity_type == 'ifsc_code':
            # Uppercase IFSC
            return value.upper().strip()
        
        elif entity_type == 'url':
            # Ensure proper URL format
            url = value.strip()
            if not url.startswith('http'):
                url = 'https://' + url
            return url
        
        elif entity_type == 'amount':
            # Keep as-is for now
            return value.strip()
        
        elif entity_type == 'bank_account':
            # Only return if it looks like a bank account (context needed)
            digits = re.sub(r'\D', '', value)
            if 9 <= len(digits) <= 18:
                return digits
            return None
        
        return value.strip()
    
    def _calculate_confidence(self, entity_type: str, value: str) -> float:
        """Calculate confidence score for an extracted entity"""
        
        # High confidence for specific patterns
        if entity_type == 'upi_id':
            return 0.95
        elif entity_type == 'ifsc_code':
            return 0.95
        elif entity_type == 'email':
            return 0.9
        elif entity_type == 'phone_number':
            digits = re.sub(r'\D', '', value)
            if len(digits) == 10 and digits[0] in '6789':
                return 0.9
            return 0.7
        elif entity_type == 'url':
            if any(sus in value for sus in ['bit.ly', 'tinyurl', '.tk', '.ml']):
                return 0.8  # Suspicious but valid
            return 0.85
        elif entity_type == 'amount':
            return 0.85
        elif entity_type == 'bank_account':
            return 0.6  # Low confidence without context
        
        return 0.5
    
    def extract_upi_ids(self, text: str) -> List[str]:
        """Extract only UPI IDs"""
        result = self.extract(text)
        return result.entities.get('upi_id', [])
    
    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract only phone numbers"""
        result = self.extract(text)
        return result.entities.get('phone_number', [])
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract only URLs"""
        result = self.extract(text)
        return result.entities.get('url', [])


# Singleton instance
_extractor: Optional[RegexExtractor] = None


def get_regex_extractor() -> RegexExtractor:
    """Get or create the regex extractor singleton"""
    global _extractor
    if _extractor is None:
        _extractor = RegexExtractor()
    return _extractor
