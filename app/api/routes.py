"""
API Routes - Thin routing layer
All business logic is delegated to orchestrator/agents
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.config import get_settings
from app.schemas.requests import AnalyzeMessageRequest, ContinueConversationRequest, StartConversationRequest
from app.schemas.responses import UnifiedResponse, AnalysisResult, ConversationResult
from app.orchestrator.honeypot_orchestrator import get_orchestrator
from app.safety.guardrails import get_safety_guardrails

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
    # Check kill switch
    guardrails = get_safety_guardrails()
    if guardrails.is_kill_switch_active():
        raise HTTPException(
            status_code=503,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "System is in safe mode"}
        )
    
    orchestrator = get_orchestrator()
    
    try:
        result = await orchestrator.analyze_message(
            message=request.message,
            context=request.context
        )
        
        return UnifiedResponse(
            success=True,
            data=AnalysisResult(
                scam_detected=result.scam_detected,
                risk_score=result.risk_score,
                confidence=result.confidence,
                reasons=result.reasons,
                models_used=result.models_used,
                processing_time_ms=result.processing_time_ms,
                rule_based_score=result.rule_based_score,
                llm_score=result.llm_score,
                signals=[s.__dict__ for s in result.signals] if hasattr(result, 'signals') else None
            ),
            error=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "ANALYSIS_FAILED", "message": str(e)}
        )


@router.post("/start-conversation", response_model=UnifiedResponse[ConversationResult])
async def start_conversation(
    request: StartConversationRequest,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[ConversationResult]:
    """
    Start a new honeypot conversation
    
    This endpoint:
    1. Analyzes the initial scam message
    2. Selects an appropriate persona
    3. Generates the first honeypot response
    4. Begins intelligence extraction
    """
    guardrails = get_safety_guardrails()
    
    if guardrails.is_kill_switch_active():
        raise HTTPException(
            status_code=503,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "System is in safe mode"}
        )
    
    orchestrator = get_orchestrator()
    
    try:
        result = await orchestrator.start_engagement(
            initial_message=request.initial_message,
            scammer_identifier=request.scammer_identifier,
            context=request.metadata
        )
        
        # Increment daily engagement counter
        guardrails.increment_daily_engagements()
        
        return UnifiedResponse(
            success=True,
            data=ConversationResult(
                conversation_id=result.conversation_id,
                response=result.response,
                persona_used=result.persona_used,
                state=result.state,
                extracted_intel=result.extracted_intel,
                models_used=result.models_used,
                should_continue=result.should_continue,
                engagement_depth=1,
                safety_warnings=result.safety_warnings
            ),
            error=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "ENGAGEMENT_FAILED", "message": str(e)}
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
    2. Validates safety constraints
    3. Generates believable response using persona
    4. Extracts intelligence
    5. Returns response and updated state
    """
    guardrails = get_safety_guardrails()
    
    if guardrails.is_kill_switch_active():
        raise HTTPException(
            status_code=503,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "System is in safe mode"}
        )
    
    if guardrails.is_conversation_terminated(request.conversation_id):
        raise HTTPException(
            status_code=400,
            detail={"code": "CONVERSATION_TERMINATED", "message": "This conversation has been terminated"}
        )
    
    orchestrator = get_orchestrator()
    
    try:
        result = await orchestrator.continue_engagement(
            conversation_id=request.conversation_id,
            scammer_message=request.message
        )
        
        return UnifiedResponse(
            success=True,
            data=ConversationResult(
                conversation_id=result.conversation_id,
                response=result.response,
                persona_used=result.persona_used,
                state=result.state,
                extracted_intel=result.extracted_intel,
                models_used=result.models_used,
                should_continue=result.should_continue,
                safety_warnings=result.safety_warnings
            ),
            error=None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={"code": "CONVERSATION_NOT_FOUND", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "CONVERSATION_FAILED", "message": str(e)}
        )


@router.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[dict]:
    """
    Get conversation summary and extracted intelligence
    """
    orchestrator = get_orchestrator()
    
    try:
        summary = orchestrator.get_conversation_summary(conversation_id)
        
        if 'error' in summary:
            raise HTTPException(
                status_code=404,
                detail={"code": "CONVERSATION_NOT_FOUND", "message": summary['error']}
            )
        
        return UnifiedResponse(
            success=True,
            data=summary,
            error=None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "FETCH_FAILED", "message": str(e)}
        )


@router.post("/kill-switch/activate")
async def activate_kill_switch(
    api_key: str = Depends(verify_api_key),
    reason: str = "Manual activation"
) -> UnifiedResponse[dict]:
    """
    Activate the global kill switch (emergency stop)
    """
    guardrails = get_safety_guardrails()
    guardrails.activate_kill_switch(reason)
    
    return UnifiedResponse(
        success=True,
        data={"status": "kill_switch_activated", "reason": reason},
        error=None
    )


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[dict]:
    """
    Deactivate the global kill switch
    """
    guardrails = get_safety_guardrails()
    guardrails.deactivate_kill_switch()
    
    return UnifiedResponse(
        success=True,
        data={"status": "kill_switch_deactivated"},
        error=None
    )


@router.get("/safety/status")
async def get_safety_status(
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[dict]:
    """
    Get current safety system status
    """
    guardrails = get_safety_guardrails()
    
    return UnifiedResponse(
        success=True,
        data=guardrails.get_safety_status(),
        error=None
    )
