"""
Local LLaMA Client - The Execution Hands
Handles entity extraction, NER, summarization, and privacy-sensitive processing
Uses Ollama or any OpenAI-compatible local inference server
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class LocalLLaMAClient:
    """
    Local LLaMA client for privacy-sensitive operations
    Connects to Ollama or any OpenAI-compatible API
    """
    
    def __init__(self):
        self.base_url = settings.local_llm_base_url
        self.model = settings.local_llm_model
        self.max_tokens = settings.local_llm_max_tokens
        self.temperature = settings.local_llm_temperature
        self.timeout = settings.local_llm_timeout
        
        # HTTP client for async requests
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        logger.info(
            "Local LLaMA client initialized",
            base_url=self.base_url,
            model=self.model
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
        Generate a response from local LLaMA
        
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
        
        # Build messages for chat format
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        user_content = prompt
        if json_mode:
            user_content += "\n\nRespond ONLY with valid JSON. No other text."
        
        messages.append({"role": "user", "content": user_content})
        
        # Ollama API format
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens or self.max_tokens
            }
        }
        
        if json_mode:
            payload["format"] = "json"
        
        try:
            # Try Ollama API first
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get("message", {}).get("content", "")
            
            # Get token counts if available
            input_tokens = result.get("prompt_eval_count", 0)
            output_tokens = result.get("eval_count", 0)
            
            # Fallback to estimation if not provided
            if input_tokens == 0:
                input_tokens = len(prompt.split()) * 1.3
            if output_tokens == 0:
                output_tokens = len(response_text.split()) * 1.3
            
            self.total_input_tokens += int(input_tokens)
            self.total_output_tokens += int(output_tokens)
            
            elapsed_time = time.time() - start_time
            
            logger.info(
                "Local LLaMA generation complete",
                model=self.model,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                elapsed_ms=int(elapsed_time * 1000)
            )
            
            return {
                "text": response_text,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "elapsed_ms": int(elapsed_time * 1000),
                "model": self.model
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "Local LLaMA HTTP error",
                status_code=e.response.status_code,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Local LLaMA generation failed",
                error=str(e),
                model=self.model
            )
            raise
    
    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract entities from text using NER
        
        Args:
            text: The text to extract entities from
            entity_types: Specific entity types to look for
            
        Returns:
            Dict with extracted entities by type
        """
        if entity_types is None:
            entity_types = [
                "upi_id", "phone_number", "bank_account", "ifsc_code",
                "email", "url", "person_name", "organization", "amount"
            ]
        
        system_prompt = """You are an entity extraction expert. Extract all relevant entities from the given text.

Focus on these entity types:
- upi_id: UPI payment IDs (example: name@upi, name@paytm)
- phone_number: Indian phone numbers (+91, 10 digits)
- bank_account: Bank account numbers
- ifsc_code: IFSC codes for Indian banks
- email: Email addresses
- url: URLs and links
- person_name: Names of people mentioned
- organization: Company or organization names
- amount: Monetary amounts mentioned

Respond in JSON format:
{
    "entities": {
        "upi_id": ["id1", "id2"],
        "phone_number": ["+91-9876543210"],
        "bank_account": [],
        "ifsc_code": [],
        "email": [],
        "url": [],
        "person_name": [],
        "organization": [],
        "amount": []
    },
    "confidence": 0.0-1.0,
    "raw_mentions": ["exact text snippets where entities were found"]
}"""
        
        result = await self.generate(
            prompt=f"Extract entities from this text:\n\n{text}",
            system_prompt=system_prompt,
            temperature=0.1,  # Very low for extraction accuracy
            json_mode=True
        )
        
        import json
        try:
            extraction = json.loads(result["text"])
            extraction["model"] = self.model
            extraction["processing_time_ms"] = result["elapsed_ms"]
            return extraction
        except json.JSONDecodeError:
            logger.warning("Failed to parse entity extraction response as JSON")
            return {
                "entities": {et: [] for et in entity_types},
                "confidence": 0.0,
                "raw_response": result["text"]
            }
    
    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 200
    ) -> Dict[str, Any]:
        """
        Summarize a conversation for memory storage
        
        Args:
            messages: List of conversation messages
            max_length: Maximum summary length in words
            
        Returns:
            Dict with summary, key points, and scam indicators
        """
        # Format conversation
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"
        
        system_prompt = f"""Summarize the following conversation in {max_length} words or less.

Respond in JSON format:
{{
    "summary": "Brief summary of the conversation",
    "key_points": ["point1", "point2"],
    "scam_indicators": ["indicator1", "indicator2"],
    "extracted_requests": ["what the scammer asked for"],
    "victim_response_pattern": "how the victim is responding"
}}"""
        
        result = await self.generate(
            prompt=f"Conversation to summarize:\n\n{conversation_text}",
            system_prompt=system_prompt,
            temperature=0.2,
            json_mode=True
        )
        
        import json
        try:
            return json.loads(result["text"])
        except json.JSONDecodeError:
            return {
                "summary": result["text"][:max_length * 5],  # Approximate
                "key_points": [],
                "scam_indicators": []
            }
    
    async def deduplicate_entities(
        self,
        entities: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Deduplicate and normalize extracted entities
        
        Args:
            entities: Dict of entity lists by type
            
        Returns:
            Deduplicated and normalized entities
        """
        system_prompt = """You are a data cleaning expert. Deduplicate and normalize the given entities.

Rules:
- Remove exact duplicates
- Normalize phone numbers to +91-XXXXXXXXXX format
- Normalize UPI IDs to lowercase
- Merge similar entries (e.g., "John" and "John Doe")
- Remove obviously fake/placeholder entries

Respond in JSON with the same structure as input, but cleaned."""

        import json
        prompt = f"Clean and deduplicate these entities:\n\n{json.dumps(entities, indent=2)}"
        
        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            json_mode=True
        )
        
        try:
            return json.loads(result["text"])
        except json.JSONDecodeError:
            # Return original if parsing fails
            return entities
    
    async def health_check(self) -> bool:
        """Check if the local LLaMA server is accessible"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error("Local LLaMA health check failed", error=str(e))
            return False
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get token usage statistics"""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
_local_llama_client: Optional[LocalLLaMAClient] = None


def get_local_llama_client() -> LocalLLaMAClient:
    """Get or create the Local LLaMA client singleton"""
    global _local_llama_client
    if _local_llama_client is None:
        _local_llama_client = LocalLLaMAClient()
    return _local_llama_client
