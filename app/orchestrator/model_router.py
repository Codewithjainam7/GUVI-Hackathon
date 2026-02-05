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
from app.llm.groq_client import get_groq_client, GroqClient
from app.llm.openrouter_client import get_openrouter_client, OpenRouterClient

logger = structlog.get_logger()

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
    GROQ = "groq"
    OPENROUTER = "openrouter"


# Task to model routing configuration
ROUTING_CONFIG: Dict[TaskType, Dict[str, ModelType]] = {
    # Groq handles reasoning tasks (Fastest)
    TaskType.SCAM_CLASSIFICATION: {
        "primary": ModelType.GROQ,
        "fallback": ModelType.OPENROUTER
    },
    TaskType.RISK_REASONING: {
        "primary": ModelType.GROQ,
        "fallback": ModelType.OPENROUTER
    },
    TaskType.AGENT_PLANNING: {
        "primary": ModelType.GROQ,
        "fallback": ModelType.OPENROUTER
    },
    TaskType.PERSONA_SELECTION: {
        "primary": ModelType.GROQ,
        "fallback": ModelType.OPENROUTER
    },
    TaskType.RESPONSE_GENERATION: {
        "primary": ModelType.GROQ,
        "fallback": ModelType.OPENROUTER
    },
    TaskType.EXPLANATION_GENERATION: {
        "primary": ModelType.GROQ,
        "fallback": ModelType.OPENROUTER
    },
    
    # Local LLaMA handles extraction and privacy-sensitive tasks
    TaskType.ENTITY_EXTRACTION: {
        "primary": ModelType.LOCAL_LLAMA,
        "fallback": ModelType.GROQ
    },
    TaskType.NER: {
        "primary": ModelType.LOCAL_LLAMA,
        "fallback": ModelType.GROQ
    },
    TaskType.SUMMARIZATION: {
        "primary": ModelType.LOCAL_LLAMA,
        "fallback": ModelType.GROQ
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
        self._groq_client: Optional[GroqClient] = None
        self._openrouter_client: Optional[OpenRouterClient] = None
        
        self._gemini_available: bool = True
        self._local_llama_available: bool = True
        self._groq_available: bool = True
        self._openrouter_available: bool = True
        
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
        
    @property
    def groq(self) -> GroqClient:
        """Get Groq client (lazy initialization)"""
        if self._groq_client is None:
            self._groq_client = get_groq_client()
        return self._groq_client

    @property
    def openrouter(self) -> OpenRouterClient:
        """Get OpenRouter client (lazy initialization)"""
        if self._openrouter_client is None:
            self._openrouter_client = get_openrouter_client()
        return self._openrouter_client
    
    def get_model_for_task(
        self,
        task_type: TaskType,
        prefer_local: bool = False
    ) -> ModelType:
        """
        Determine which model should handle a task
        """
        config = ROUTING_CONFIG.get(task_type)
        if not config:
            logger.warning(f"Unknown task type: {task_type}, defaulting to Groq")
            return ModelType.GROQ
        
        primary = config["primary"]
        fallback = config.get("fallback")
        
        # Check availability logic
        if primary == ModelType.GROQ and not self._groq_available:
            if fallback and fallback == ModelType.OPENROUTER and self._openrouter_available:
                return ModelType.OPENROUTER
            return fallback if fallback else ModelType.GEMINI
            
        if primary == ModelType.GEMINI and not self._gemini_available:
            return fallback if fallback else ModelType.GROQ
            
        if primary == ModelType.LOCAL_LLAMA and not self._local_llama_available:
            return fallback if fallback else ModelType.GROQ
        
        # Prefer local if requested
        if prefer_local and primary != ModelType.LOCAL_LLAMA:
            if self._local_llama_available:
                return ModelType.LOCAL_LLAMA
        
        return primary
    
    async def route_task(
        self,
        task_type: TaskType,
        **kwargs
    ) -> Dict[str, Any]:
        """Route a task to the appropriate model"""
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
                return await self._generic_generate(model_type, **kwargs)
                
        except Exception as e:
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
                if model_type == ModelType.GROQ:
                    self._groq_available = False
                elif model_type == ModelType.GEMINI:
                    self._gemini_available = False
                elif model_type == ModelType.OPENROUTER:
                    self._openrouter_available = False
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
        # Import few-shot examples
        from app.prompts.scam_examples import get_few_shot_prompt
        few_shot = get_few_shot_prompt()
        
        if model_type == ModelType.GEMINI:
            return await self.gemini.classify_scam(message, context)
        elif model_type == ModelType.GROQ:
            # Use Groq for classification (with Few-Shot)
            prompt = f"""You are a scam detection expert specialized in Indian cyber fraud. 
            
{few_shot}

Analyze this message:
"{message}"

Context: {context or {}}

Return JSON with:
- is_scam (bool)
- confidence (float 0-1)
- risk_level (low/medium/high/critical)
- scam_type (string)
- reasons (list of strings)
"""
            result = await self.groq.generate_response(
                system_prompt="Respond in valid JSON only.",
                user_prompt=prompt,
                json_mode=True
            )
            import json
            try:
                return json.loads(result)
            except:
                return {"is_scam": False, "confidence": 0.0, "raw": result}

        elif model_type == ModelType.OPENROUTER:
            # Use OpenRouter for classification
            prompt = f"""You are a scam detection expert.
            
Analyze this message:
"{message}"

Context: {context or {}}

Return JSON with:
- is_scam (bool)
- confidence (float 0-1)
- risk_level (low/medium/high/critical)
- scam_type (string)
- reasons (list of strings)
"""
            result = await self.openrouter.generate(
                prompt=prompt,
                system_prompt="Respond in valid JSON only.",
                temperature=0.1
            )
            import json
            try:
                return json.loads(result)
            except:
                return {"is_scam": False, "confidence": 0.0, "raw": result}
        else:
            # Use local LLaMA
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
        elif model_type == ModelType.GROQ:
             result = await self.groq.generate_response(
                system_prompt="Extract entities (UPI, phone, bank, URL) as JSON.",
                user_prompt=f"Extract from:\n{text}",
                json_mode=True
            )
             import json
             try:
                return json.loads(result)
             except:
                return {"entities": {}, "raw": result}
        elif model_type == ModelType.OPENROUTER:
            system_prompt = "Extract entities (UPI, phone, bank, URL) as JSON."
            user_prompt = f"Extract from:\n{text}"
            result = await self.openrouter.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
            import json
            try:
                return json.loads(result)
            except:
                return {"entities": {}, "raw": result}
        else:
            # Fallback to Gemini
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
        elif model_type == ModelType.GROQ:
            history_text = "\n".join([
                f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                for m in conversation_history[-5:]
            ])
            result = await self.groq.generate_response(
                system_prompt=persona_prompt,
                user_prompt=f"History:\n{history_text}\n\nScammer: {scammer_message}\n\nRespond in character:",
            )
            return {"response": result, "model": "groq"}
        elif model_type == ModelType.OPENROUTER:
            history_text = "\n".join([
                f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                for m in conversation_history[-5:]
            ])
            user_prompt = f"History:\n{history_text}\n\nScammer: {scammer_message}\n\nRespond in character:"
            result = await self.openrouter.generate(
                prompt=user_prompt,
                system_prompt=persona_prompt,
                temperature=0.7
            )
            return {"response": result, "model": "openrouter"}
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
        text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])
        
        if model_type == ModelType.LOCAL_LLAMA:
            return await self.local_llama.summarize_conversation(messages, max_length)
        elif model_type == ModelType.GROQ:
             result = await self.groq.generate_response(
                system_prompt=f"Summarize conversation in {max_length} words.",
                user_prompt=text
            )
             return {"summary": result}
        elif model_type == ModelType.OPENROUTER:
            result = await self.openrouter.generate(
                prompt=f"Summarize in {max_length} words:\n\n{text}",
                temperature=0.3
            )
            return {"summary": result}
        else:
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
        if model_type == ModelType.GROQ:
             prompt = f"""Plan next step.
Profile: {scammer_profile}
State: {current_state}
Intel: {extracted_intel}

Return JSON:
- goal (string)
- next_action (string)
- risk_assessment (string)
"""
             result = await self.groq.generate_response(
                system_prompt="You are an expert scam baiter. Respond in JSON.",
                user_prompt=prompt,
                json_mode=True
            )
             import json
             try:
                return json.loads(result)
             except:
                return {"goal": "engage", "next_action": "reply"}
        elif model_type == ModelType.OPENROUTER:
             prompt = f"""Plan next step.
Profile: {scammer_profile}
State: {current_state}
Intel: {extracted_intel}

Return JSON:
- goal (string)
- next_action (string)
- risk_assessment (string)
"""
             result = await self.openrouter.generate(
                prompt=prompt,
                system_prompt="You are an expert scam baiter. Respond in JSON.",
             )
             import json
             try:
                return json.loads(result)
             except:
                 return {"goal": "engage", "next_action": "reply"}
                
        # Gemini handles planning well too
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
        """Generic generation"""
        if model_type == ModelType.GEMINI:
            return await self.gemini.generate(prompt, system_prompt, **kwargs)
        elif model_type == ModelType.GROQ:
             result = await self.groq.generate_response(
                system_prompt=system_prompt or "You are a helpful assistant.",
                user_prompt=prompt
            )
             return {"text": result}
        elif model_type == ModelType.OPENROUTER:
             result = await self.openrouter.generate(prompt, system_prompt, **kwargs)
             return {"text": result}
        else:
            return await self.local_llama.generate(prompt, system_prompt, **kwargs)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all models"""
        gemini_ok = await self.gemini.health_check()
        local_ok = await self.local_llama.health_check()
        groq_ok = await self.groq.health_check()
        openrouter_ok = await self.openrouter.health_check()
        
        self._gemini_available = gemini_ok
        self._local_llama_available = local_ok
        self._groq_available = groq_ok
        self._openrouter_available = openrouter_ok
        
        return {
            "gemini": gemini_ok,
            "local_llama": local_ok,
            "groq": groq_ok,
            "openrouter": openrouter_ok
        }
    
    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """Get usage statistics"""
        return {
            "gemini": self.gemini.get_usage_stats(),
            "local_llama": self.local_llama.get_usage_stats(),
            "groq": {},
            "openrouter": {}
        }


# Singleton instance
_model_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get or create the model router singleton"""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router
