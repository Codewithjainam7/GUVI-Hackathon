"""
OpenRouter API Client - Aggregates 100+ LLM models with unified API
Free models available, fallback for Groq/Gemini rate limits
"""

from typing import Any, Dict, Optional
import structlog
from openai import AsyncOpenAI

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class OpenRouterClient:
    """
    OpenRouter client using OpenAI-compatible API
    Free models: meta-llama/llama-3.1-8b-instruct:free
    """
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.base_url = settings.openrouter_base_url
        
        if self.api_key and self.api_key != "your-openrouter-key-here":
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.available = True
            logger.info(
                "OpenRouter client initialized",
                model=self.model,
                base_url=self.base_url
            )
        else:
            self.client = None
            self.available = False
            logger.warning("OpenRouter API key not configured")
    
    async def health_check(self) -> bool:
        """Check if OpenRouter is available"""
        if not self.available:
            return False
        
        try:
            # Simple test generation
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            logger.info("OpenRouter health check passed")
            return True
        except Exception as e:
            logger.error("OpenRouter health check failed", error=str(e))
            return False
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text using OpenRouter"""
        if not self.available:
            raise RuntimeError("OpenRouter not available")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            content = response.choices[0].message.content
            logger.info("OpenRouter generation successful", model=self.model)
            return content
            
        except Exception as e:
            logger.error("OpenRouter generation failed", error=str(e))
            raise
    
    async def chat(
        self,
        messages: list,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Chat completion using OpenRouter"""
        if not self.available:
            raise RuntimeError("OpenRouter not available")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("OpenRouter chat failed", error=str(e))
            raise


# Singleton instance
_openrouter_client: Optional[OpenRouterClient] = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create the OpenRouter client singleton"""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient()
    return _openrouter_client
