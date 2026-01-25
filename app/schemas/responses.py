"""
Response Schemas - Unified response format for all API endpoints
"""

from typing import Generic, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error details for failed responses"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


class UnifiedResponse(BaseModel, Generic[T]):
    """Unified response wrapper for all API responses"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(default=None, description="Response data")
    error: Optional[ErrorDetail] = Field(default=None, description="Error details if failed")


class AnalysisResult(BaseModel):
    """Result of scam message analysis"""
    
    scam_detected: bool = Field(..., description="Whether a scam was detected")
    risk_score: float = Field(..., ge=0, le=1, description="Risk score from 0 to 1")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence")
    reasons: List[str] = Field(default=[], description="Reasons for detection")
    models_used: List[str] = Field(default=[], description="LLM models used")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    
    # Optional detailed breakdown
    rule_based_score: Optional[float] = Field(default=None, description="Score from rule-based detection")
    llm_score: Optional[float] = Field(default=None, description="Score from LLM classification")
    signals: Optional[List[Dict[str, Any]]] = Field(default=None, description="Individual detection signals")
    
    class Config:
        json_schema_extra = {
            "example": {
                "scam_detected": True,
                "risk_score": 0.94,
                "confidence": 0.87,
                "reasons": [
                    "Urgency language detected: 'act now or lose'",
                    "Payment request identified",
                    "Impersonation of authority figure"
                ],
                "models_used": ["gemini"],
                "processing_time_ms": 245
            }
        }


class ConversationResult(BaseModel):
    """Result of honeypot conversation turn"""
    
    conversation_id: str = Field(..., description="Conversation identifier")
    response: str = Field(..., description="Generated response to send to scammer")
    persona_used: str = Field(..., description="Persona used for response")
    state: str = Field(..., description="Current conversation state")
    extracted_intel: Dict[str, Any] = Field(default={}, description="Extracted intelligence")
    models_used: List[str] = Field(default=[], description="LLM models used")
    should_continue: bool = Field(..., description="Whether to continue engagement")
    
    # Safety info
    engagement_depth: Optional[int] = Field(default=None, description="Number of turns so far")
    safety_warnings: Optional[List[str]] = Field(default=None, description="Any safety concerns")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_abc123",
                "response": "Oh dear, I'm not very good with technology. Could you explain that again?",
                "persona_used": "senior_citizen",
                "state": "honeypot_engaged",
                "extracted_intel": {
                    "upi_ids": ["scammer@upi"],
                    "phone_numbers": []
                },
                "models_used": ["gemini", "local_llama"],
                "should_continue": True,
                "engagement_depth": 5
            }
        }


class IntelligenceReport(BaseModel):
    """Extracted intelligence report"""
    
    conversation_id: str
    scammer_profile_id: Optional[str] = None
    
    # Extracted identifiers
    upi_ids: List[str] = Field(default=[])
    phone_numbers: List[str] = Field(default=[])
    bank_accounts: List[Dict[str, str]] = Field(default=[])
    urls: List[str] = Field(default=[])
    email_addresses: List[str] = Field(default=[])
    
    # Analysis
    scam_type: Optional[str] = None
    confidence: float = 0.0
    extraction_method: str = ""  # "regex", "llm", or "hybrid"
    
    # Network
    linked_profiles: List[str] = Field(default=[])


class ScammerProfile(BaseModel):
    """Scammer profile with risk evolution"""
    
    profile_id: str
    risk_score: float = Field(ge=0, le=1)
    first_seen: str
    last_seen: str
    
    # Identifiers
    known_identifiers: Dict[str, List[str]] = Field(default={})
    
    # Conversations
    conversation_count: int = 0
    total_messages: int = 0
    
    # Behavior analysis
    scam_types: List[str] = Field(default=[])
    behavior_patterns: List[str] = Field(default=[])
    
    # Network
    network_connections: List[str] = Field(default=[])
