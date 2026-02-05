"""
Groq Client - High-speed LLM inference
"""

import json
from typing import Any, Dict, List, Optional
import structlog
from groq import AsyncGroq

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class GroqClient:
    """Client for Groq's high-speed API"""
    
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.client = None
        
        if self.api_key:
            try:
                self.client = AsyncGroq(api_key=self.api_key)
                logger.info("Groq client initialized", model=self.model)
            except Exception as e:
                logger.error("Failed to initialize Groq client", error=str(e))
        else:
            logger.warning("Groq API key not found")
    
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """
        Generate response from Groq
        """
        if not self.client:
            raise RuntimeError("Groq client not initialized")
            
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or settings.groq_temperature,
                "max_tokens": max_tokens or settings.groq_max_tokens,
            }
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            completion = await self.client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error("Groq generation failed", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check if Groq API is reachable"""
        if not self.client:
            return False
        try:
            await self.generate_response(
                system_prompt="Test",
                user_prompt="Hi",
                max_tokens=5
            )
            return True
        except Exception:
            return False


# Singleton instance
_groq_client: Optional[GroqClient] = None

def get_groq_client() -> GroqClient:
    """Get or create Groq client singleton"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
