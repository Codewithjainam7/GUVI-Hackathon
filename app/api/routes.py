"""
API Routes - Thin routing layer
All business logic is delegated to orchestrator/agents
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.config import get_settings
from app.schemas.requests import AnalyzeMessageRequest, ContinueConversationRequest
from app.schemas.responses import UnifiedResponse, AnalysisResult, ConversationResult

router = APIRouter()
settings = get_settings()

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    """Verify API key from header"""
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing API key"
            }
        )
    return api_key


@router.post("/analyze-message", response_model=UnifiedResponse[AnalysisResult])
async def analyze_message(
    request: AnalyzeMessageRequest,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[AnalysisResult]:
    """
    Analyze a message for scam detection
    
    This endpoint:
    1. Runs rule-based detection (Layer 1)
    2. Runs Gemini-based classification (Layer 2)
    3. Calculates ensemble risk score
    4. Returns detailed analysis with explainability
    """
    # TODO: Import and call orchestrator
    # from app.orchestrator.analyzer import analyze_message as analyze
    # result = await analyze(request.message, request.context)
    
    # Placeholder response
    return UnifiedResponse(
        success=True,
        data=AnalysisResult(
            scam_detected=False,
            risk_score=0.0,
            confidence=0.0,
            reasons=[],
            models_used=["gemini"],
            processing_time_ms=0
        ),
        error=None
    )


@router.post("/continue-conversation", response_model=UnifiedResponse[ConversationResult])
async def continue_conversation(
    request: ContinueConversationRequest,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[ConversationResult]:
    """
    Continue a honeypot conversation with a scammer
    
    This endpoint:
    1. Retrieves conversation context from memory
    2. Selects appropriate persona
    3. Generates believable response
    4. Extracts intelligence
    5. Updates scammer profile
    """
    # TODO: Import and call orchestrator
    # from app.orchestrator.conversation import continue_conversation as converse
    # result = await converse(request.conversation_id, request.message)
    
    # Placeholder response
    return UnifiedResponse(
        success=True,
        data=ConversationResult(
            conversation_id=request.conversation_id,
            response="",
            persona_used="",
            state="normal_chat",
            extracted_intel={},
            models_used=["gemini", "local_llama"],
            should_continue=True
        ),
        error=None
    )


@router.get("/intelligence/{conversation_id}")
async def get_intelligence(
    conversation_id: str,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[dict]:
    """
    Get extracted intelligence for a conversation
    """
    # TODO: Implement intelligence retrieval
    return UnifiedResponse(
        success=True,
        data={
            "conversation_id": conversation_id,
            "upi_ids": [],
            "phone_numbers": [],
            "bank_accounts": [],
            "urls": [],
            "scammer_profile": {}
        },
        error=None
    )


@router.get("/scammer-profile/{profile_id}")
async def get_scammer_profile(
    profile_id: str,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[dict]:
    """
    Get a scammer's profile with risk evolution
    """
    # TODO: Implement profile retrieval
    return UnifiedResponse(
        success=True,
        data={
            "profile_id": profile_id,
            "risk_score": 0.0,
            "conversations": [],
            "known_identifiers": {},
            "behavior_patterns": []
        },
        error=None
    )
