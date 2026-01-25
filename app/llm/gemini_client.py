"""
Gemini API Client - The Reasoning Brain
Handles scam classification, risk reasoning, agent planning, and response generation
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class GeminiClient:
    """
    Gemini API client wrapper with retry logic, structured output, and cost tracking
    """
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.max_tokens = settings.gemini_max_tokens
        self.temperature = settings.gemini_temperature
        self.timeout = settings.gemini_timeout
        
        # Initialize the Gemini client
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        logger.info(
            "Gemini client initialized",
            model=self.model_name,
            max_tokens=self.max_tokens
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a response from Gemini
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system instructions
            temperature: Override default temperature
            max_tokens: Override default max tokens
            json_mode: If True, enforce JSON output
            
        Returns:
            Dict with response text, tokens used, and timing
        """
        start_time = time.time()
        
        # Build the prompt
        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        full_prompt += prompt
        
        if json_mode:
            full_prompt += "\n\nRespond ONLY with valid JSON. No other text."
        
        # Generation config
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens or self.max_tokens,
            temperature=temperature or self.temperature,
        )
        
        try:
            # Run generation in thread pool for async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
            )
            
            # Extract response
            response_text = response.text
            
            # Track tokens (approximate - Gemini doesn't always provide exact counts)
            input_tokens = len(full_prompt.split()) * 1.3  # Rough estimate
            output_tokens = len(response_text.split()) * 1.3
            
            self.total_input_tokens += int(input_tokens)
            self.total_output_tokens += int(output_tokens)
            
            elapsed_time = time.time() - start_time
            
            logger.info(
                "Gemini generation complete",
                model=self.model_name,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                elapsed_ms=int(elapsed_time * 1000)
            )
            
            return {
                "text": response_text,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "elapsed_ms": int(elapsed_time * 1000),
                "model": self.model_name
            }
            
        except Exception as e:
            logger.error(
                "Gemini generation failed",
                error=str(e),
                model=self.model_name
            )
            raise
    
    async def classify_scam(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify whether a message is a scam
        
        Returns:
            Dict with is_scam, confidence, scam_type, and reasons
        """
        system_prompt = """You are a scam detection expert. Analyze the given message and determine if it's a scam.

Consider these scam indicators:
- Urgency language ("act now", "limited time", "immediately")
- Requests for money or financial information
- Promises of prizes, lottery wins, or inheritances
- Impersonation of authorities, banks, or companies
- Suspicious links or requests for personal information
- Grammar/spelling errors common in scam messages
- Pressure tactics or threats

Respond in JSON format:
{
    "is_scam": true/false,
    "confidence": 0.0-1.0,
    "scam_type": "lottery_scam|banking_scam|impersonation|romance_scam|tech_support|other|none",
    "reasons": ["reason1", "reason2"],
    "risk_level": "low|medium|high|critical"
}"""
        
        prompt = f"Message to analyze:\n\n{message}"
        
        if context:
            prompt += f"\n\nAdditional context:\n{context}"
        
        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for classification
            json_mode=True
        )
        
        # Parse JSON response
        import json
        try:
            classification = json.loads(result["text"])
            classification["model"] = self.model_name
            classification["processing_time_ms"] = result["elapsed_ms"]
            return classification
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini classification response as JSON")
            return {
                "is_scam": False,
                "confidence": 0.0,
                "scam_type": "unknown",
                "reasons": ["Failed to parse response"],
                "risk_level": "low",
                "raw_response": result["text"]
            }
    
    async def generate_response(
        self,
        conversation_history: List[Dict[str, str]],
        persona_prompt: str,
        scammer_message: str
    ) -> Dict[str, Any]:
        """
        Generate a believable honeypot response using a persona
        
        Args:
            conversation_history: Previous messages in the conversation
            persona_prompt: The persona's system prompt
            scammer_message: The scammer's latest message
            
        Returns:
            Dict with response text and metadata
        """
        # Build conversation context
        history_text = ""
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = "Scammer" if msg.get("role") == "scammer" else "You"
            history_text += f"{role}: {msg.get('content', '')}\n"
        
        prompt = f"""Previous conversation:
{history_text}

Scammer's latest message:
{scammer_message}

Generate a response that:
1. Stays in character as the persona
2. Shows interest but asks clarifying questions
3. Delays providing any real information
4. Tries to extract more details about the scam
5. Sounds natural and human (include typos, hesitations)

Respond with ONLY the message text, no JSON or explanation."""
        
        result = await self.generate(
            prompt=prompt,
            system_prompt=persona_prompt,
            temperature=0.8  # Higher temperature for natural responses
        )
        
        return {
            "response": result["text"],
            "model": self.model_name,
            "processing_time_ms": result["elapsed_ms"]
        }
    
    async def plan_engagement(
        self,
        scammer_profile: Dict[str, Any],
        current_state: str,
        extracted_intel: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Plan the next steps in the honeypot engagement
        
        Returns:
            Dict with recommended action, persona switch, and goals
        """
        system_prompt = """You are a honeypot strategist. Based on the scammer's behavior and current state, recommend the optimal engagement strategy.

Respond in JSON format:
{
    "recommended_action": "continue|escalate|extract|terminate",
    "persona_recommendation": "senior_citizen|student|business_owner|current",
    "engagement_goals": ["goal1", "goal2"],
    "risk_assessment": "low|medium|high",
    "intel_priorities": ["upi_id", "phone_number", "bank_account"],
    "reasoning": "explanation of strategy"
}"""
        
        prompt = f"""Current engagement state: {current_state}

Scammer profile:
{scammer_profile}

Extracted intelligence so far:
{extracted_intel}

What should be the next move?"""
        
        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4,
            json_mode=True
        )
        
        import json
        try:
            return json.loads(result["text"])
        except json.JSONDecodeError:
            return {
                "recommended_action": "continue",
                "reasoning": "Failed to parse planning response"
            }
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get token usage statistics"""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }
    
    async def health_check(self) -> bool:
        """Check if the Gemini API is accessible"""
        try:
            result = await self.generate(
                prompt="Say 'ok'",
                max_tokens=10,
                temperature=0
            )
            return len(result.get("text", "")) > 0
        except Exception as e:
            logger.error("Gemini health check failed", error=str(e))
            return False


# Singleton instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get or create the Gemini client singleton"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
