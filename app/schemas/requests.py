"""
Request Schemas - Pydantic models for API requests
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AnalyzeMessageRequest(BaseModel):
    """Request schema for message analysis"""
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The message to analyze for scam detection"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (sender info, platform, timestamp, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Congratulations! You've won $1,000,000. Send us your bank details to claim.",
                "context": {
                    "sender": "+91-9876543210",
                    "platform": "whatsapp",
                    "timestamp": "2026-01-26T00:00:00Z"
                }
            }
        }


class ContinueConversationRequest(BaseModel):
    """Request schema for continuing a honeypot conversation"""
    
    conversation_id: str = Field(
        ...,
        description="Unique identifier for the conversation"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The scammer's latest message"
    )
    force_persona: Optional[str] = Field(
        default=None,
        description="Force a specific persona (optional)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_abc123",
                "message": "Please share your bank account number to process the payment",
                "force_persona": None
            }
        }


class StartConversationRequest(BaseModel):
    """Request schema for starting a new honeypot conversation"""
    
    initial_message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The initial scam message"
    )
    scammer_identifier: Optional[str] = Field(
        default=None,
        description="Phone number, email, or other identifier"
    )
    platform: Optional[str] = Field(
        default=None,
        description="Platform where the scam originated"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )
