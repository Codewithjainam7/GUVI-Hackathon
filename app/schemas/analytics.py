from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class AnalyticsOverview(BaseModel):
    active_threats: int
    total_blocked: int
    scams_prevented: int
    risk_distribution: Dict[str, int]
    system_status: str

class TrafficPoint(BaseModel):
    timestamp: str
    count: int

class ThreatLandscape(BaseModel):
    time_series: List[TrafficPoint]
    geo_distribution: Optional[List[Dict[str, Any]]] = None

class NetworkNode(BaseModel):
    id: str
    label: str
    type: str # 'scammer', 'phone', 'upi', 'email'
    risk_score: float

class NetworkLink(BaseModel):
    source: str
    target: str
    type: str # 'used_identifier', 'same_persona'

class NetworkGraph(BaseModel):
    nodes: List[NetworkNode]
    links: List[NetworkLink]

class ActivityItem(BaseModel):
    id: str
    type: str # 'message', 'alert'
    content: str
    timestamp: datetime
    severity: str

class RecentActivity(BaseModel):
    activities: List[ActivityItem]
