"""
Fake Data Detector - Validates extracted entities for authenticity
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class ValidationResult:
    """Result of entity validation"""
    entity_type: str
    entity_value: str
    is_valid: bool
    is_fake: bool
    confidence: float
    reason: str


class FakeDataDetector:
    """
    Detects fake/placeholder data in extracted entities
    
    Checks for:
    - Test/dummy patterns
    - Invalid format
    - Known fake values
    - Statistical anomalies
    """
    
    def __init__(self):
        # Known fake UPI patterns
        self.fake_upi_patterns = [
            r'^test',
            r'^demo',
            r'^fake',
            r'^dummy',
            r'^example',
            r'^sample',
            r'^xxx+',
            r'^abc+',
            r'^123+',
            r'@example',
            r'@test',
        ]
        
        # Known fake phone patterns
        self.fake_phone_patterns = [
            r'^(\+91[-\s]?)?0{10}$',  # All zeros
            r'^(\+91[-\s]?)?1{10}$',  # All ones
            r'^(\+91[-\s]?)?1234567890$',  # Sequential
            r'^(\+91[-\s]?)?9876543210$',  # Reverse sequential
            r'^(\+91[-\s]?)?9999999999$',  # All nines
        ]
        
        # Known fake bank account patterns
        self.fake_account_patterns = [
            r'^0+$',  # All zeros
            r'^1+$',  # All ones
            r'^123456789',  # Sequential
            r'^987654321',  # Reverse sequential
            r'^(\d)\1+$',  # All same digit
        ]
        
        # Compile patterns
        self.compiled_upi = [re.compile(p, re.IGNORECASE) for p in self.fake_upi_patterns]
        self.compiled_phone = [re.compile(p) for p in self.fake_phone_patterns]
        self.compiled_account = [re.compile(p) for p in self.fake_account_patterns]
        
        logger.info("Fake data detector initialized")
    
    def validate_entity(
        self,
        entity_type: str,
        value: str
    ) -> ValidationResult:
        """
        Validate a single entity
        
        Args:
            entity_type: Type of entity
            value: Entity value to validate
            
        Returns:
            ValidationResult
        """
        if entity_type == 'upi_id':
            return self._validate_upi(value)
        elif entity_type == 'phone_number':
            return self._validate_phone(value)
        elif entity_type == 'bank_account':
            return self._validate_bank_account(value)
        elif entity_type == 'ifsc_code':
            return self._validate_ifsc(value)
        elif entity_type == 'email':
            return self._validate_email(value)
        elif entity_type == 'url':
            return self._validate_url(value)
        else:
            return ValidationResult(
                entity_type=entity_type,
                entity_value=value,
                is_valid=True,
                is_fake=False,
                confidence=0.5,
                reason="Unknown entity type, no validation applied"
            )
    
    def _validate_upi(self, value: str) -> ValidationResult:
        """Validate UPI ID"""
        # Check basic format
        if '@' not in value:
            return ValidationResult(
                entity_type='upi_id',
                entity_value=value,
                is_valid=False,
                is_fake=True,
                confidence=0.95,
                reason="Invalid UPI format: missing @"
            )
        
        # Check for fake patterns
        for pattern in self.compiled_upi:
            if pattern.search(value):
                return ValidationResult(
                    entity_type='upi_id',
                    entity_value=value,
                    is_valid=True,
                    is_fake=True,
                    confidence=0.85,
                    reason=f"Matches fake pattern: {pattern.pattern}"
                )
        
        # Check provider
        valid_providers = [
            'upi', 'paytm', 'phonepe', 'ybl', 'oksbi', 'okicici', 
            'okaxis', 'okhdfcbank', 'axl', 'ibl', 'sbi', 'apl',
            'axisbank', 'hdfcbank', 'icici', 'kotak', 'indus'
        ]
        
        provider = value.split('@')[-1].lower()
        if provider not in valid_providers:
            return ValidationResult(
                entity_type='upi_id',
                entity_value=value,
                is_valid=False,
                is_fake=True,
                confidence=0.9,
                reason=f"Unknown UPI provider: {provider}"
            )
        
        return ValidationResult(
            entity_type='upi_id',
            entity_value=value,
            is_valid=True,
            is_fake=False,
            confidence=0.8,
            reason="Valid UPI format"
        )
    
    def _validate_phone(self, value: str) -> ValidationResult:
        """Validate phone number"""
        # Normalize
        digits = re.sub(r'\D', '', value)
        
        # Check length
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        
        if len(digits) != 10:
            return ValidationResult(
                entity_type='phone_number',
                entity_value=value,
                is_valid=False,
                is_fake=True,
                confidence=0.95,
                reason=f"Invalid length: {len(digits)} digits"
            )
        
        # Check first digit (must be 6-9 for Indian mobile)
        if digits[0] not in '6789':
            return ValidationResult(
                entity_type='phone_number',
                entity_value=value,
                is_valid=False,
                is_fake=True,
                confidence=0.9,
                reason="Invalid first digit for Indian mobile"
            )
        
        # Check for fake patterns
        for pattern in self.compiled_phone:
            if pattern.match(value) or pattern.match(f"+91-{digits}"):
                return ValidationResult(
                    entity_type='phone_number',
                    entity_value=value,
                    is_valid=True,
                    is_fake=True,
                    confidence=0.9,
                    reason="Matches fake phone pattern"
                )
        
        # Check for repeated digits
        if len(set(digits)) <= 2:
            return ValidationResult(
                entity_type='phone_number',
                entity_value=value,
                is_valid=True,
                is_fake=True,
                confidence=0.85,
                reason="Too few unique digits"
            )
        
        return ValidationResult(
            entity_type='phone_number',
            entity_value=value,
            is_valid=True,
            is_fake=False,
            confidence=0.75,
            reason="Valid phone format"
        )
    
    def _validate_bank_account(self, value: str) -> ValidationResult:
        """Validate bank account number"""
        digits = re.sub(r'\D', '', value)
        
        # Check length (Indian accounts are typically 9-18 digits)
        if not (9 <= len(digits) <= 18):
            return ValidationResult(
                entity_type='bank_account',
                entity_value=value,
                is_valid=False,
                is_fake=True,
                confidence=0.9,
                reason=f"Invalid length: {len(digits)} digits"
            )
        
        # Check for fake patterns
        for pattern in self.compiled_account:
            if pattern.match(digits):
                return ValidationResult(
                    entity_type='bank_account',
                    entity_value=value,
                    is_valid=True,
                    is_fake=True,
                    confidence=0.9,
                    reason="Matches fake account pattern"
                )
        
        return ValidationResult(
            entity_type='bank_account',
            entity_value=value,
            is_valid=True,
            is_fake=False,
            confidence=0.6,  # Lower confidence without bank verification
            reason="Valid account format"
        )
    
    def _validate_ifsc(self, value: str) -> ValidationResult:
        """Validate IFSC code"""
        # Format: 4 letters + 0 + 6 alphanumeric
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', value.upper()):
            return ValidationResult(
                entity_type='ifsc_code',
                entity_value=value,
                is_valid=False,
                is_fake=True,
                confidence=0.95,
                reason="Invalid IFSC format"
            )
        
        # Check for known banks
        known_banks = ['SBIN', 'HDFC', 'ICIC', 'AXIS', 'PUNB', 'BARB', 'UBIN', 'CBIN', 'UTIB']
        bank_code = value[:4].upper()
        
        if bank_code in known_banks:
            return ValidationResult(
                entity_type='ifsc_code',
                entity_value=value,
                is_valid=True,
                is_fake=False,
                confidence=0.85,
                reason=f"Valid IFSC for known bank: {bank_code}"
            )
        
        return ValidationResult(
            entity_type='ifsc_code',
            entity_value=value,
            is_valid=True,
            is_fake=False,
            confidence=0.7,
            reason="Valid IFSC format, unknown bank"
        )
    
    def _validate_email(self, value: str) -> ValidationResult:
        """Validate email address"""
        # Check format
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            return ValidationResult(
                entity_type='email',
                entity_value=value,
                is_valid=False,
                is_fake=True,
                confidence=0.95,
                reason="Invalid email format"
            )
        
        # Check for fake domains
        fake_domains = ['example.com', 'test.com', 'fake.com', 'dummy.com', 'tempmail.com']
        domain = value.split('@')[-1].lower()
        
        if domain in fake_domains:
            return ValidationResult(
                entity_type='email',
                entity_value=value,
                is_valid=True,
                is_fake=True,
                confidence=0.9,
                reason=f"Known fake domain: {domain}"
            )
        
        return ValidationResult(
            entity_type='email',
            entity_value=value,
            is_valid=True,
            is_fake=False,
            confidence=0.75,
            reason="Valid email format"
        )
    
    def _validate_url(self, value: str) -> ValidationResult:
        """Validate URL"""
        # Check for suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq']
        
        for tld in suspicious_tlds:
            if value.lower().endswith(tld):
                return ValidationResult(
                    entity_type='url',
                    entity_value=value,
                    is_valid=True,
                    is_fake=False,  # Not fake, but suspicious
                    confidence=0.7,
                    reason=f"Suspicious TLD: {tld}"
                )
        
        # Check for localhost/test URLs
        if 'localhost' in value or '127.0.0.1' in value or 'example.com' in value:
            return ValidationResult(
                entity_type='url',
                entity_value=value,
                is_valid=True,
                is_fake=True,
                confidence=0.95,
                reason="Test/localhost URL"
            )
        
        return ValidationResult(
            entity_type='url',
            entity_value=value,
            is_valid=True,
            is_fake=False,
            confidence=0.8,
            reason="Valid URL"
        )
    
    def validate_all(
        self,
        entities: Dict[str, List[str]]
    ) -> Dict[str, List[ValidationResult]]:
        """
        Validate all entities
        
        Args:
            entities: Dict of entity lists by type
            
        Returns:
            Dict of validation results by type
        """
        results = {}
        
        for entity_type, values in entities.items():
            results[entity_type] = [
                self.validate_entity(entity_type, value)
                for value in values
            ]
        
        return results
    
    def filter_fake(
        self,
        entities: Dict[str, List[str]]
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Filter out fake entities
        
        Returns:
            Tuple of (valid_entities, fake_entities)
        """
        valid = {}
        fake = {}
        
        for entity_type, values in entities.items():
            valid[entity_type] = []
            fake[entity_type] = []
            
            for value in values:
                result = self.validate_entity(entity_type, value)
                if result.is_fake:
                    fake[entity_type].append(value)
                else:
                    valid[entity_type].append(value)
        
        return valid, fake


# Singleton instance
_detector: Optional[FakeDataDetector] = None


def get_fake_detector() -> FakeDataDetector:
    """Get or create fake data detector singleton"""
    global _detector
    if _detector is None:
        _detector = FakeDataDetector()
    return _detector
