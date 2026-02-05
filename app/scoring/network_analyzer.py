"""
Network Analyzer - advanced connectivity graphing
visualizes connections between scammers, phones, UPIs, and banks
"""

from typing import Dict, List, Any
import networkx as nx
import structlog
import json

logger = structlog.get_logger()

class ScammerNetworkGraph:
    def __init__(self):
        self.graph = nx.MultiGraph()
    
    def add_engagement(self, engagement_data: Dict[str, Any]):
        """Add intel from an engagement to the graph"""
        conversation_id = engagement_data.get('conversation_id')
        scammer_id = engagement_data.get('scammer_identifier')
        
        if not scammer_id:
            return
            
        # Add scammer node
        self.graph.add_node(scammer_id, type='scammer')
        
        # Add extracted entities
        intel = engagement_data.get('extracted_intel', {})
        
        for entity_type, values in intel.items():
            for value in values:
                # Add entity node
                self.graph.add_node(value, type=entity_type)
                # Add edge
                self.graph.add_edge(scammer_id, value, relation='uses', source=conversation_id)
                
    def get_network_stats(self) -> Dict[str, Any]:
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "components": nx.number_connected_components(self.graph),
            "most_connected": sorted(self.graph.degree, key=lambda x: x[1], reverse=True)[:5]
        }
        
    def export_graph_json(self) -> str:
        """Export graph for D3.js or other visualizers"""
        return json.dumps(nx.node_link_data(self.graph))

_network_graph = ScammerNetworkGraph()

def get_network_graph() -> ScammerNetworkGraph:
    return _network_graph
