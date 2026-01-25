"""
Scammer Profiling - Build and analyze scammer profiles
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import structlog

from app.memory.memory_manager import get_memory_manager

logger = structlog.get_logger()


@dataclass
class ScammerProfile:
    """Complete scammer profile"""
    scammer_id: str
    
    # Risk
    risk_score: float = 0.5
    risk_level: str = "medium"
    
    # Identifiers
    identifiers: Dict[str, List[str]] = field(default_factory=lambda: {
        "phone": [],
        "upi": [],
        "email": [],
        "bank_account": [],
        "url": []
    })
    
    # Activity
    conversations: List[str] = field(default_factory=list)
    total_messages: int = 0
    
    # Behavior
    scam_types: List[str] = field(default_factory=list)
    behavior_patterns: List[str] = field(default_factory=list)
    
    # Timestamps
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    
    # Network
    linked_profiles: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scammer_id": self.scammer_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "identifiers": self.identifiers,
            "conversations": self.conversations,
            "total_messages": self.total_messages,
            "scam_types": self.scam_types,
            "behavior_patterns": self.behavior_patterns,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "linked_profiles": self.linked_profiles
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScammerProfile":
        return cls(
            scammer_id=data.get("scammer_id", ""),
            risk_score=data.get("risk_score", 0.5),
            risk_level=data.get("risk_level", "medium"),
            identifiers=data.get("identifiers", {}),
            conversations=data.get("conversations", []),
            total_messages=data.get("total_messages", 0),
            scam_types=data.get("scam_types", []),
            behavior_patterns=data.get("behavior_patterns", []),
            first_seen=data.get("first_seen"),
            last_seen=data.get("last_seen"),
            linked_profiles=data.get("linked_profiles", [])
        )


class ScammerProfiler:
    """
    Builds and manages scammer profiles
    Tracks risk evolution and behavior patterns
    """
    
    def __init__(self):
        self._memory = None
        logger.info("Scammer profiler initialized")
    
    async def _get_memory(self):
        """Get memory manager (lazy init)"""
        if self._memory is None:
            self._memory = await get_memory_manager()
        return self._memory
    
    def generate_scammer_id(self, identifier: str) -> str:
        """
        Generate a unique scammer ID from an identifier
        
        Args:
            identifier: Phone number, UPI, or email
            
        Returns:
            Unique scammer ID
        """
        # Hash the identifier for privacy
        hash_input = identifier.lower().strip()
        return f"scammer_{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"
    
    async def get_or_create_profile(
        self,
        identifier: str,
        identifier_type: str = "phone"
    ) -> ScammerProfile:
        """
        Get existing profile or create a new one
        
        Args:
            identifier: The scammer's identifier
            identifier_type: Type of identifier (phone, upi, email)
            
        Returns:
            ScammerProfile
        """
        memory = await self._get_memory()
        
        # Check if profile exists
        existing = await memory.find_scammer_by_identifier(identifier, identifier_type)
        
        if existing:
            return ScammerProfile.from_dict(existing)
        
        # Create new profile
        scammer_id = self.generate_scammer_id(identifier)
        now = datetime.utcnow().isoformat()
        
        profile = ScammerProfile(
            scammer_id=scammer_id,
            first_seen=now,
            last_seen=now
        )
        profile.identifiers[identifier_type].append(identifier)
        
        await memory.save_scammer_profile(scammer_id, profile.to_dict())
        
        logger.info(
            "Created new scammer profile",
            scammer_id=scammer_id,
            identifier_type=identifier_type
        )
        
        return profile
    
    async def update_profile(
        self,
        scammer_id: str,
        conversation_id: Optional[str] = None,
        new_identifiers: Optional[Dict[str, List[str]]] = None,
        scam_type: Optional[str] = None,
        messages_count: int = 0
    ) -> ScammerProfile:
        """
        Update a scammer profile with new information
        
        Args:
            scammer_id: The scammer's ID
            conversation_id: New conversation to link
            new_identifiers: New identifiers found
            scam_type: Type of scam detected
            messages_count: Number of new messages
            
        Returns:
            Updated ScammerProfile
        """
        memory = await self._get_memory()
        data = await memory.get_scammer_profile(scammer_id)
        
        if not data:
            raise ValueError(f"Scammer profile not found: {scammer_id}")
        
        profile = ScammerProfile.from_dict(data)
        
        # Add conversation
        if conversation_id and conversation_id not in profile.conversations:
            profile.conversations.append(conversation_id)
        
        # Add identifiers
        if new_identifiers:
            for id_type, values in new_identifiers.items():
                if id_type not in profile.identifiers:
                    profile.identifiers[id_type] = []
                for value in values:
                    if value not in profile.identifiers[id_type]:
                        profile.identifiers[id_type].append(value)
        
        # Add scam type
        if scam_type and scam_type not in profile.scam_types:
            profile.scam_types.append(scam_type)
        
        # Update counters
        profile.total_messages += messages_count
        profile.last_seen = datetime.utcnow().isoformat()
        
        # Recalculate risk
        profile.risk_score = self._calculate_risk_score(profile)
        profile.risk_level = self._get_risk_level(profile.risk_score)
        
        await memory.save_scammer_profile(scammer_id, profile.to_dict())
        
        return profile
    
    def _calculate_risk_score(self, profile: ScammerProfile) -> float:
        """
        Calculate risk score based on profile data
        
        Factors:
        - Number of conversations
        - Number of identifiers
        - Scam types detected
        - Message volume
        """
        score = 0.3  # Base score
        
        # More conversations = higher risk
        conv_factor = min(len(profile.conversations) * 0.1, 0.3)
        score += conv_factor
        
        # More identifiers = more sophisticated
        total_ids = sum(len(v) for v in profile.identifiers.values())
        id_factor = min(total_ids * 0.05, 0.2)
        score += id_factor
        
        # Multiple scam types = professional
        if len(profile.scam_types) > 1:
            score += 0.1
        
        # High message volume
        if profile.total_messages > 50:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_risk_level(self, score: float) -> str:
        """Convert score to risk level"""
        if score >= 0.8:
            return "critical"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
    
    async def detect_network(
        self,
        scammer_id: str
    ) -> List[str]:
        """
        Detect other scammers in the same network
        based on shared identifiers
        """
        memory = await self._get_memory()
        data = await memory.get_scammer_profile(scammer_id)
        
        if not data:
            return []
        
        profile = ScammerProfile.from_dict(data)
        linked = set()
        
        # Check for shared identifiers
        for id_type, values in profile.identifiers.items():
            for value in values:
                # Find other profiles with this identifier
                other = await memory.find_scammer_by_identifier(value, id_type)
                if other and other.get('scammer_id') != scammer_id:
                    linked.add(other['scammer_id'])
        
        return list(linked)
    
    async def add_behavior_pattern(
        self,
        scammer_id: str,
        pattern: str
    ):
        """Add a detected behavior pattern"""
        memory = await self._get_memory()
        data = await memory.get_scammer_profile(scammer_id)
        
        if data:
            profile = ScammerProfile.from_dict(data)
            if pattern not in profile.behavior_patterns:
                profile.behavior_patterns.append(pattern)
                await memory.save_scammer_profile(scammer_id, profile.to_dict())


# Singleton instance
_profiler: Optional[ScammerProfiler] = None


async def get_scammer_profiler() -> ScammerProfiler:
    """Get or create the scammer profiler singleton"""
    global _profiler
    if _profiler is None:
        _profiler = ScammerProfiler()
    return _profiler
