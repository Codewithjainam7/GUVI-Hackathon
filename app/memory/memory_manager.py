"""
Memory Manager - Short-term and long-term memory using Redis
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Optional Redis import (graceful fallback if not available)
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory fallback")


class InMemoryStore:
    """Fallback in-memory store when Redis is not available"""
    
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}
    
    async def get(self, key: str) -> Optional[str]:
        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            del self._store[key]
            del self._expiry[key]
            return None
        return self._store.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        self._store[key] = value
        if ex:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ex)
    
    async def delete(self, key: str):
        self._store.pop(key, None)
        self._expiry.pop(key, None)
    
    async def keys(self, pattern: str) -> List[str]:
        # Simple pattern matching (only supports * at end)
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            return [k for k in self._store.keys() if k.startswith(prefix)]
        return [k for k in self._store.keys() if k == pattern]
    
    async def exists(self, key: str) -> bool:
        return key in self._store


class MemoryManager:
    """
    Manages conversation memory with Redis backend
    
    Memory Types:
    - Short-term: Current conversation context (TTL-based)
    - Long-term: Scammer profiles and extracted intelligence (persistent)
    """
    
    # Key prefixes
    PREFIX_CONVERSATION = "conv:"
    PREFIX_SCAMMER = "scammer:"
    PREFIX_INTEL = "intel:"
    PREFIX_SESSION = "session:"
    
    def __init__(self):
        self._redis: Optional[Any] = None
        self._fallback = InMemoryStore()
        self._connected = False
        
        logger.info("Memory manager initialized")
    
    async def connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Using in-memory fallback for memory storage")
            return
        
        try:
            self._redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Redis", url=settings.redis_url)
        except Exception as e:
            logger.warning("Redis connection failed, using fallback", error=str(e))
            self._redis = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._connected = False
    
    @property
    def store(self):
        """Get the active store (Redis or fallback)"""
        return self._redis if self._redis else self._fallback
    
    # ==================== Short-term Memory ====================
    
    async def save_conversation(
        self,
        conversation_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Save conversation context to short-term memory
        
        Args:
            conversation_id: Unique conversation identifier
            data: Conversation data to store
            ttl: Time-to-live in seconds (default from settings)
        """
        ttl = ttl or settings.short_term_memory_ttl
        key = f"{self.PREFIX_CONVERSATION}{conversation_id}"
        
        await self.store.set(key, json.dumps(data, default=str), ex=ttl)
        logger.debug("Saved conversation to memory", conversation_id=conversation_id)
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context from memory"""
        key = f"{self.PREFIX_CONVERSATION}{conversation_id}"
        data = await self.store.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def update_conversation(
        self,
        conversation_id: str,
        updates: Dict[str, Any]
    ):
        """Update specific fields in conversation memory"""
        existing = await self.get_conversation(conversation_id)
        if existing:
            existing.update(updates)
            await self.save_conversation(conversation_id, existing)
    
    async def delete_conversation(self, conversation_id: str):
        """Delete conversation from memory"""
        key = f"{self.PREFIX_CONVERSATION}{conversation_id}"
        await self.store.delete(key)
    
    # ==================== Long-term Memory ====================
    
    async def save_scammer_profile(
        self,
        scammer_id: str,
        profile: Dict[str, Any]
    ):
        """
        Save scammer profile to long-term memory
        No TTL - persists until explicitly deleted
        """
        key = f"{self.PREFIX_SCAMMER}{scammer_id}"
        profile['updated_at'] = datetime.utcnow().isoformat()
        
        await self.store.set(key, json.dumps(profile, default=str))
        logger.info("Saved scammer profile", scammer_id=scammer_id)
    
    async def get_scammer_profile(self, scammer_id: str) -> Optional[Dict[str, Any]]:
        """Get scammer profile from memory"""
        key = f"{self.PREFIX_SCAMMER}{scammer_id}"
        data = await self.store.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def update_scammer_profile(
        self,
        scammer_id: str,
        updates: Dict[str, Any]
    ):
        """Update scammer profile"""
        existing = await self.get_scammer_profile(scammer_id)
        if existing:
            existing.update(updates)
            await self.save_scammer_profile(scammer_id, existing)
        else:
            await self.save_scammer_profile(scammer_id, updates)
    
    async def find_scammer_by_identifier(
        self,
        identifier: str,
        identifier_type: str = "phone"
    ) -> Optional[Dict[str, Any]]:
        """
        Find scammer profile by identifier (phone, UPI, email)
        
        This is a simple implementation - in production, use a proper index
        """
        # Get all scammer keys
        keys = await self.store.keys(f"{self.PREFIX_SCAMMER}*")
        
        for key in keys:
            data = await self.store.get(key)
            if data:
                profile = json.loads(data)
                identifiers = profile.get('identifiers', {})
                if identifier in identifiers.get(identifier_type, []):
                    return profile
        
        return None
    
    # ==================== Intelligence Storage ====================
    
    async def save_intelligence(
        self,
        conversation_id: str,
        intel: Dict[str, Any]
    ):
        """Save extracted intelligence"""
        key = f"{self.PREFIX_INTEL}{conversation_id}"
        intel['extracted_at'] = datetime.utcnow().isoformat()
        
        await self.store.set(key, json.dumps(intel, default=str))
    
    async def get_intelligence(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get extracted intelligence for a conversation"""
        key = f"{self.PREFIX_INTEL}{conversation_id}"
        data = await self.store.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def append_intelligence(
        self,
        conversation_id: str,
        entity_type: str,
        value: str
    ):
        """Append a new entity to existing intelligence"""
        intel = await self.get_intelligence(conversation_id) or {'entities': {}}
        
        if entity_type not in intel['entities']:
            intel['entities'][entity_type] = []
        
        if value not in intel['entities'][entity_type]:
            intel['entities'][entity_type].append(value)
            await self.save_intelligence(conversation_id, intel)
            return True
        
        return False
    
    # ==================== Cross-session Linking ====================
    
    async def link_conversations(
        self,
        scammer_id: str,
        conversation_id: str
    ):
        """Link a conversation to a scammer profile"""
        profile = await self.get_scammer_profile(scammer_id)
        
        if not profile:
            profile = {
                'scammer_id': scammer_id,
                'conversations': [],
                'created_at': datetime.utcnow().isoformat()
            }
        
        if conversation_id not in profile.get('conversations', []):
            profile.setdefault('conversations', []).append(conversation_id)
            await self.save_scammer_profile(scammer_id, profile)
    
    async def get_linked_conversations(
        self,
        scammer_id: str
    ) -> List[str]:
        """Get all conversations linked to a scammer"""
        profile = await self.get_scammer_profile(scammer_id)
        return profile.get('conversations', []) if profile else []
    
    # ==================== Utility Methods ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        conv_keys = await self.store.keys(f"{self.PREFIX_CONVERSATION}*")
        scammer_keys = await self.store.keys(f"{self.PREFIX_SCAMMER}*")
        intel_keys = await self.store.keys(f"{self.PREFIX_INTEL}*")
        
        return {
            'conversations': len(conv_keys),
            'scammer_profiles': len(scammer_keys),
            'intelligence_records': len(intel_keys),
            'redis_connected': self._connected
        }
    
    async def clear_expired(self):
        """Clear expired entries (for in-memory fallback)"""
        if isinstance(self.store, InMemoryStore):
            # Trigger cleanup by accessing keys
            for key in list(self._fallback._store.keys()):
                await self._fallback.get(key)


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


async def get_memory_manager() -> MemoryManager:
    """Get or create the memory manager singleton"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
        await _memory_manager.connect()
    return _memory_manager
