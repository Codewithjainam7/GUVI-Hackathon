"""
Model Router - Central LLM task routing
Routes tasks to the appropriate LLM (Gemini or Local LLaMA) based on task type
"""

import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from app.config import get_settings
from app.llm.gemini_client import get_gemini_client, GeminiClient
from app.llm.local_llama_client import get_local_llama_client, LocalLLaMAClient

logger = structlog.get_logger()
settings = get_settings()


class TaskType(str, Enum):
    """Types of tasks that can be routed to LLMs"""
    SCAM_CLASSIFICATION = "scam_classification"
    RISK_REASONING = "risk_reasoning"
    AGENT_PLANNING = "agent_planning"
    PERSONA_SELECTION = "persona_selection"
    RESPONSE_GENERATION = "response_generation"
    EXPLANATION_GENERATION = "explanation_generation"
    ENTITY_EXTRACTION = "entity_extraction"
    NER = "ner"
    SUMMARIZATION = "summarization"
    DEDUPLICATION = "deduplication"
    PII_PROCESSING = "pii_processing"


class ModelType(str, Enum):
    """Available LLM models"""
    GEMINI = "gemini"
    LOCAL_LLAMA = "local_llama"


# Task to model routing configuration
ROUTING_CONFIG: Dict[TaskType, Dict[str, ModelType]] = {
    # Gemini handles reasoning tasks
    TaskType.SCAM_CLASSIFICATION: {
        "primary": ModelType.GEMINI,
        "fallback": ModelType.LOCAL_LLAMA
    },
    TaskType.RISK_REASONING: {
        "primary": ModelType.GEMINI,
        "fallback": None
    },
    TaskType.AGENT_PLANNING: {
        "primary": ModelType.GEMINI,
        "fallback": None
    },
    TaskType.PERSONA_SELECTION: {
        "primary": ModelType.GEMINI,
        "fallback": ModelType.LOCAL_LLAMA
    },
    TaskType.RESPONSE_GENERATION: {
        "primary": ModelType.GEMINI,
        "fallback": ModelType.LOCAL_LLAMA
    },
    TaskType.EXPLANATION_GENERATION: {
        "primary": ModelType.GEMINI,
        "fallback": None
    },
    
    # Local LLaMA handles extraction and privacy-sensitive tasks
    TaskType.ENTITY_EXTRACTION: {
        "primary": ModelType.LOCAL_LLAMA,
        "fallback": ModelType.GEMINI
    },
    TaskType.NER: {
        "primary": ModelType.LOCAL_LLAMA,
        "fallback": ModelType.GEMINI
    },
    TaskType.SUMMARIZATION: {
        "primary": ModelType.LOCAL_LLAMA,
        "fallback": ModelType.GEMINI
    },
    TaskType.DEDUPLICATION: {
        "primary": ModelType.LOCAL_LLAMA,
        "fallback": None
    },
    TaskType.PII_PROCESSING: {
        "primary": ModelType.LOCAL_LLAMA,
        "fallback": None  # Never send PII to cloud
    },
}


class ModelRouter:
    """
    Central router for LLM task distribution
    Handles model selection, fallback, and load balancing
    """
    
    def __init__(self):
        self._gemini_client: Optional[GeminiClient] = None
        self._local_llama_client: Optional[LocalLLaMAClient] = None
        self._gemini_available: bool = True
        self._local_llama_available: bool = True
        
        logger.info("Model router initialized")
    
    @property
    def gemini(self) -> GeminiClient:
        """Get Gemini client (lazy initialization)"""
        if self._gemini_client is None:
            self._gemini_client = get_gemini_client()
        return self._gemini_client
    
    @property
    def local_llama(self) -> LocalLLaMAClient:
        """Get Local LLaMA client (lazy initialization)"""
        if self._local_llama_client is None:
            self._local_llama_client = get_local_llama_client()
        return self._local_llama_client
    
    def get_model_for_task(
        self,
        task_type: TaskType,
        prefer_local: bool = False
    ) -> ModelType:
        """
        Determine which model should handle a task
        
        Args:
            task_type: The type of task to route
            prefer_local: If True, prefer local model when possible
            
        Returns:
            The model type to use
        """
        config = ROUTING_CONFIG.get(task_type)
        if not config:
            logger.warning(f"Unknown task type: {task_type}, defaulting to Gemini")
            return ModelType.GEMINI
        
        primary = config["primary"]
        fallback = config.get("fallback")
        
        # Check if primary is available
        if primary == ModelType.GEMINI and not self._gemini_available:
            if fallback:
                logger.warning(f"Gemini unavailable, falling back to {fallback}")
                return fallback
        
        if primary == ModelType.LOCAL_LLAMA and not self._local_llama_available:
            if fallback:
                logger.warning(f"Local LLaMA unavailable, falling back to {fallback}")
                return fallback
        
        # Prefer local if requested and allowed
        if prefer_local and primary == ModelType.GEMINI:
            if fallback == ModelType.LOCAL_LLAMA and self._local_llama_available:
                return ModelType.LOCAL_LLAMA
        
        return primary
    
    async def route_task(
        self,
        task_type: TaskType,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Route a task to the appropriate model and execute it
        
        Args:
            task_type: The type of task
            **kwargs: Task-specific arguments
            
        Returns:
            Task result with model metadata
        """
        model_type = self.get_model_for_task(task_type)
        
        logger.info(
            "Routing task",
            task_type=task_type.value,
            model=model_type.value
        )
        
        try:
            if task_type == TaskType.SCAM_CLASSIFICATION:
                return await self._classify_scam(model_type, **kwargs)
            elif task_type == TaskType.ENTITY_EXTRACTION:
                return await self._extract_entities(model_type, **kwargs)
            elif task_type == TaskType.RESPONSE_GENERATION:
                return await self._generate_response(model_type, **kwargs)
            elif task_type == TaskType.SUMMARIZATION:
                return await self._summarize(model_type, **kwargs)
            elif task_type == TaskType.AGENT_PLANNING:
                return await self._plan_engagement(model_type, **kwargs)
            else:
                # Generic generation
                return await self._generic_generate(model_type, **kwargs)
                
        except Exception as e:
            # Mark model as unavailable and try fallback
            logger.error(
                "Task execution failed",
                task_type=task_type.value,
                model=model_type.value,
                error=str(e)
            )
            
            # Try fallback
            config = ROUTING_CONFIG.get(task_type, {})
            fallback = config.get("fallback")
            
            if fallback and fallback != model_type:
                logger.info(f"Attempting fallback to {fallback}")
                if model_type == ModelType.GEMINI:
                    self._gemini_available = False
                else:
                    self._local_llama_available = False
                
                return await self.route_task(task_type, **kwargs)
            
            raise
    
    async def _classify_scam(
        self,
        model_type: ModelType,
        message: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Route scam classification task"""
        if model_type == ModelType.GEMINI:
            return await self.gemini.classify_scam(message, context)
        else:
            # Use local LLaMA for classification
            result = await self.local_llama.generate(
                prompt=f"Classify if this is a scam message:\n\n{message}",
                system_prompt="You are a scam detection expert. Respond with JSON: {is_scam, confidence, reasons}",
                json_mode=True,
                temperature=0.2
            )
            import json
            try:
                return json.loads(result["text"])
            except:
                return {"is_scam": False, "confidence": 0.0, "raw": result["text"]}
    
    async def _extract_entities(
        self,
        model_type: ModelType,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Route entity extraction task"""
        if model_type == ModelType.LOCAL_LLAMA:
            return await self.local_llama.extract_entities(text, entity_types)
        else:
            # Fallback to Gemini (less preferred for privacy)
            result = await self.gemini.generate(
                prompt=f"Extract entities from:\n\n{text}",
                system_prompt="Extract UPI IDs, phone numbers, bank accounts, URLs. Respond as JSON.",
                json_mode=True,
                temperature=0.1
            )
            import json
            try:
                return json.loads(result["text"])
            except:
                return {"entities": {}, "raw": result["text"]}
    
    async def _generate_response(
        self,
        model_type: ModelType,
        conversation_history: List[Dict],
        persona_prompt: str,
        scammer_message: str
    ) -> Dict[str, Any]:
        """Route response generation task"""
        if model_type == ModelType.GEMINI:
            return await self.gemini.generate_response(
                conversation_history, persona_prompt, scammer_message
            )
        else:
            # Format for local LLaMA
            history_text = "\n".join([
                f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                for m in conversation_history[-5:]
            ])
            result = await self.local_llama.generate(
                prompt=f"History:\n{history_text}\n\nScammer: {scammer_message}\n\nRespond in character:",
                system_prompt=persona_prompt,
                temperature=0.8
            )
            return {"response": result["text"], "model": "local_llama"}
    
    async def _summarize(
        self,
        model_type: ModelType,
        messages: List[Dict],
        max_length: int = 200
    ) -> Dict[str, Any]:
        """Route summarization task"""
        if model_type == ModelType.LOCAL_LLAMA:
            return await self.local_llama.summarize_conversation(messages, max_length)
        else:
            # Use Gemini for summarization
            text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])
            result = await self.gemini.generate(
                prompt=f"Summarize in {max_length} words:\n\n{text}",
                temperature=0.3
            )
            return {"summary": result["text"]}
    
    async def _plan_engagement(
        self,
        model_type: ModelType,
        scammer_profile: Dict,
        current_state: str,
        extracted_intel: Dict
    ) -> Dict[str, Any]:
        """Route engagement planning task"""
        # Planning always uses Gemini
        return await self.gemini.plan_engagement(
            scammer_profile, current_state, extracted_intel
        )
    
    async def _generic_generate(
        self,
        model_type: ModelType,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generic generation for unspecified tasks"""
        if model_type == ModelType.GEMINI:
            return await self.gemini.generate(prompt, system_prompt, **kwargs)
        else:
            return await self.local_llama.generate(prompt, system_prompt, **kwargs)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all models"""
        gemini_ok = await self.gemini.health_check()
        local_ok = await self.local_llama.health_check()
        
        self._gemini_available = gemini_ok
        self._local_llama_available = local_ok
        
        return {
            "gemini": gemini_ok,
            "local_llama": local_ok
        }
    
    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """Get usage statistics for all models"""
        return {
            "gemini": self.gemini.get_usage_stats(),
            "local_llama": self.local_llama.get_usage_stats()
        }


# Singleton instance
_model_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get or create the model router singleton"""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router
