"""
Scam Network Analyzer - Detect connected scammer networks
"""

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from app.memory.memory_manager import get_memory_manager

logger = structlog.get_logger()


@dataclass
class NetworkNode:
    """A node in the scammer network"""
    scammer_id: str
    identifiers: Dict[str, List[str]] = field(default_factory=dict)
    connections: Set[str] = field(default_factory=set)
    conversation_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


@dataclass
class NetworkCluster:
    """A cluster of connected scammers"""
    cluster_id: str
    members: List[str] = field(default_factory=list)
    shared_identifiers: Dict[str, List[str]] = field(default_factory=dict)
    total_conversations: int = 0
    risk_score: float = 0.0
    scam_types: List[str] = field(default_factory=list)


class NetworkAnalyzer:
    """
    Analyzes scammer networks to find:
    - Reused UPI IDs across conversations
    - Shared phone numbers
    - Similar URL patterns
    - Persona reuse correlation
    """
    
    def __init__(self):
        self._memory = None
        
        # In-memory graph (for quick lookups)
        self._identifier_to_scammers: Dict[str, Set[str]] = defaultdict(set)
        self._scammer_nodes: Dict[str, NetworkNode] = {}
        
        logger.info("Network analyzer initialized")
    
    async def _get_memory(self):
        """Get memory manager (lazy init)"""
        if self._memory is None:
            self._memory = await get_memory_manager()
        return self._memory
    
    def add_scammer(
        self,
        scammer_id: str,
        identifiers: Dict[str, List[str]],
        conversation_id: Optional[str] = None
    ):
        """
        Add or update a scammer in the network graph
        
        Args:
            scammer_id: Unique scammer ID
            identifiers: Dict of identifiers by type
            conversation_id: Optional conversation to link
        """
        # Get or create node
        if scammer_id not in self._scammer_nodes:
            self._scammer_nodes[scammer_id] = NetworkNode(
                scammer_id=scammer_id,
                first_seen=datetime.utcnow()
            )
        
        node = self._scammer_nodes[scammer_id]
        node.last_seen = datetime.utcnow()
        
        if conversation_id:
            node.conversation_count += 1
        
        # Add identifiers and track connections
        for id_type, values in identifiers.items():
            if id_type not in node.identifiers:
                node.identifiers[id_type] = []
            
            for value in values:
                normalized = self._normalize_identifier(id_type, value)
                
                if normalized not in node.identifiers[id_type]:
                    node.identifiers[id_type].append(normalized)
                
                # Track which scammers use this identifier
                id_key = f"{id_type}:{normalized}"
                existing_users = self._identifier_to_scammers[id_key]
                
                # Connect to other scammers using same identifier
                for other_id in existing_users:
                    if other_id != scammer_id:
                        node.connections.add(other_id)
                        if other_id in self._scammer_nodes:
                            self._scammer_nodes[other_id].connections.add(scammer_id)
                
                existing_users.add(scammer_id)
    
    def _normalize_identifier(self, id_type: str, value: str) -> str:
        """Normalize an identifier for comparison"""
        if id_type == 'phone_number':
            # Extract just digits
            import re
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 10:
                return digits[-10:]  # Last 10 digits
            return digits
        
        if id_type == 'upi_id':
            return value.lower().strip()
        
        if id_type == 'email':
            return value.lower().strip()
        
        if id_type == 'url':
            # Extract domain
            import re
            match = re.search(r'https?://([^/]+)', value)
            if match:
                return match.group(1).lower()
            return value.lower()
        
        return value.strip()
    
    def find_connected_scammers(
        self,
        scammer_id: str,
        max_depth: int = 2
    ) -> List[str]:
        """
        Find all scammers connected to a given scammer
        
        Uses BFS to find connections up to max_depth
        """
        if scammer_id not in self._scammer_nodes:
            return []
        
        visited = set()
        queue = [(scammer_id, 0)]
        connected = []
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            if current_id != scammer_id:
                connected.append(current_id)
            
            if depth < max_depth:
                node = self._scammer_nodes.get(current_id)
                if node:
                    for connection in node.connections:
                        if connection not in visited:
                            queue.append((connection, depth + 1))
        
        return connected
    
    def detect_clusters(self, min_cluster_size: int = 2) -> List[NetworkCluster]:
        """
        Detect clusters of connected scammers
        
        Uses Union-Find to identify connected components
        """
        # Union-Find structure
        parent = {sid: sid for sid in self._scammer_nodes}
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        # Build clusters
        for scammer_id, node in self._scammer_nodes.items():
            for connection in node.connections:
                if connection in parent:
                    union(scammer_id, connection)
        
        # Group by cluster
        clusters_dict = defaultdict(list)
        for scammer_id in self._scammer_nodes:
            root = find(scammer_id)
            clusters_dict[root].append(scammer_id)
        
        # Build cluster objects
        clusters = []
        for root, members in clusters_dict.items():
            if len(members) >= min_cluster_size:
                cluster = self._build_cluster(root, members)
                clusters.append(cluster)
        
        # Sort by size
        clusters.sort(key=lambda c: len(c.members), reverse=True)
        
        return clusters
    
    def _build_cluster(self, cluster_id: str, members: List[str]) -> NetworkCluster:
        """Build a cluster object with aggregated data"""
        cluster = NetworkCluster(
            cluster_id=f"cluster_{hashlib.md5(cluster_id.encode()).hexdigest()[:8]}",
            members=members
        )
        
        # Aggregate data
        seen_identifiers = defaultdict(set)
        
        for member_id in members:
            node = self._scammer_nodes.get(member_id)
            if node:
                cluster.total_conversations += node.conversation_count
                
                for id_type, values in node.identifiers.items():
                    for value in values:
                        seen_identifiers[id_type].add(value)
        
        # Find shared identifiers (used by multiple members)
        for id_type, values in seen_identifiers.items():
            shared = []
            for value in values:
                id_key = f"{id_type}:{value}"
                users = self._identifier_to_scammers.get(id_key, set())
                # Check if used by multiple members of this cluster
                cluster_users = users.intersection(set(members))
                if len(cluster_users) > 1:
                    shared.append(value)
            
            if shared:
                cluster.shared_identifiers[id_type] = shared
        
        # Calculate risk score
        cluster.risk_score = self._calculate_cluster_risk(cluster)
        
        return cluster
    
    def _calculate_cluster_risk(self, cluster: NetworkCluster) -> float:
        """Calculate risk score for a cluster"""
        score = 0.3  # Base score
        
        # More members = higher risk
        score += min(len(cluster.members) * 0.1, 0.3)
        
        # Shared identifiers = coordinated operation
        shared_count = sum(len(v) for v in cluster.shared_identifiers.values())
        score += min(shared_count * 0.1, 0.2)
        
        # More conversations = active threat
        if cluster.total_conversations > 10:
            score += 0.1
        if cluster.total_conversations > 50:
            score += 0.1
        
        return min(score, 1.0)
    
    def find_reused_upi(self) -> List[Tuple[str, List[str]]]:
        """Find UPI IDs used by multiple scammers"""
        reused = []
        
        for id_key, scammers in self._identifier_to_scammers.items():
            if id_key.startswith('upi_id:') and len(scammers) > 1:
                upi_id = id_key.split(':', 1)[1]
                reused.append((upi_id, list(scammers)))
        
        return sorted(reused, key=lambda x: len(x[1]), reverse=True)
    
    def find_reused_phones(self) -> List[Tuple[str, List[str]]]:
        """Find phone numbers used by multiple scammers"""
        reused = []
        
        for id_key, scammers in self._identifier_to_scammers.items():
            if id_key.startswith('phone_number:') and len(scammers) > 1:
                phone = id_key.split(':', 1)[1]
                reused.append((phone, list(scammers)))
        
        return sorted(reused, key=lambda x: len(x[1]), reverse=True)
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        clusters = self.detect_clusters()
        
        return {
            'total_scammers': len(self._scammer_nodes),
            'total_identifiers': len(self._identifier_to_scammers),
            'total_clusters': len(clusters),
            'largest_cluster_size': len(clusters[0].members) if clusters else 0,
            'reused_upi_count': len(self.find_reused_upi()),
            'reused_phone_count': len(self.find_reused_phones()),
            'average_connections': sum(
                len(n.connections) for n in self._scammer_nodes.values()
            ) / max(len(self._scammer_nodes), 1)
        }
    
    def get_cluster_report(self) -> List[Dict[str, Any]]:
        """Generate a report of all clusters"""
        clusters = self.detect_clusters()
        
        return [
            {
                'cluster_id': c.cluster_id,
                'size': len(c.members),
                'members': c.members,
                'shared_identifiers': c.shared_identifiers,
                'total_conversations': c.total_conversations,
                'risk_score': c.risk_score
            }
            for c in clusters
        ]


# Singleton instance
_analyzer: Optional[NetworkAnalyzer] = None


def get_network_analyzer() -> NetworkAnalyzer:
    """Get or create network analyzer singleton"""
    global _analyzer
    if _analyzer is None:
        _analyzer = NetworkAnalyzer()
    return _analyzer
