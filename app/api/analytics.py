"""
Analytics API - Advanced insights and visualization data
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy import select, func, desc, and_

from app.config import get_settings
from app.utils.database import get_database
from app.schemas.responses import UnifiedResponse
from app.schemas.database_models import (
    Conversation, Message, ScammerProfile, 
    ExtractedIntelligence, RiskScore, AuditLog
)
from app.schemas.analytics import (
    AnalyticsOverview, ThreatLandscape, NetworkGraph, 
    RecentActivity, NetworkNode, NetworkLink, TrafficPoint, ActivityItem
)

router = APIRouter()
settings = get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or missing API key"}
        )
    return api_key

@router.get("/overview", response_model=UnifiedResponse[AnalyticsOverview])
async def get_analytics_overview(
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[AnalyticsOverview]:
    """Get high-level analytics overview"""
    db = await get_database()
    async with db.session() as session:
        # Active Threats (Active conversations)
        active_count = (await session.execute(
            select(func.count(Conversation.id)).where(Conversation.is_terminated == False)
        )).scalar() or 0
        
        # Total Blocked (High risk profiles)
        total_blocked = (await session.execute(
            select(func.count(ScammerProfile.id)).where(ScammerProfile.risk_level == 'high')
        )).scalar() or 0
        
        # Scams Prevented (Total terminated conversations)
        scams_prevented = (await session.execute(
            select(func.count(Conversation.id)).where(Conversation.is_terminated == True)
        )).scalar() or 0
        
        # Risk Distribution
        # Group by risk_level
        risk_dist_query = select(ScammerProfile.risk_level, func.count(ScammerProfile.id)).group_by(ScammerProfile.risk_level)
        risk_dist_result = (await session.execute(risk_dist_query)).all()
        risk_distribution = {row[0]: row[1] for row in risk_dist_result}
        
        return UnifiedResponse(
            success=True,
            data=AnalyticsOverview(
                active_threats=active_count,
                total_blocked=total_blocked,
                scams_prevented=scams_prevented,
                risk_distribution=risk_distribution,
                system_status="ONLINE"
            ),
            error=None
        )

@router.get("/threat-landscape", response_model=UnifiedResponse[ThreatLandscape])
async def get_threat_landscape(
    days: int = 7,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[ThreatLandscape]:
    """Get threat landscape time-series data"""
    db = await get_database()
    async with db.session() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Messages per day
        traffic_query = select(
            func.date_trunc('day', Message.timestamp).label('day'),
            func.count(Message.id)
        ).where(Message.timestamp >= cutoff).group_by(func.date_trunc('day', Message.timestamp)).order_by('day')
        
        # Note: SQLite doesn't support date_trunc, falling back to python processing if needed
        # For Postgres (production), date_trunc is fine. 
        # Assuming Postgres for Enterprise Upgrade as per Plan.
        
        try:
            results = (await session.execute(traffic_query)).all()
            time_series = [
                TrafficPoint(timestamp=row[0].isoformat(), count=row[1]) 
                for row in results
            ]
        except Exception:
            # Fallback for SQLite/Other
            msgs = (await session.execute(
                select(Message.timestamp).where(Message.timestamp >= cutoff)
            )).scalars().all()
            
            buckets = {}
            for ts in msgs:
                day = ts.date().isoformat()
                buckets[day] = buckets.get(day, 0) + 1
            
            time_series = [
                TrafficPoint(timestamp=k, count=v) for k, v in sorted(buckets.items())
            ]
            
        return UnifiedResponse(
            success=True,
            data=ThreatLandscape(time_series=time_series),
            error=None
        )

@router.get("/network-graph", response_model=UnifiedResponse[NetworkGraph])
async def get_network_graph(
    limit: int = 50,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[NetworkGraph]:
    """Get network graph of scammers and extracted intelligence"""
    db = await get_database()
    async with db.session() as session:
        # Get recent high risk scammers
        scammers = (await session.execute(
            select(ScammerProfile).order_by(desc(ScammerProfile.last_seen)).limit(limit)
        )).scalars().all()
        
        nodes = []
        links = []
        scammer_ids = set()
        
        for scammer in scammers:
            scammer_node_id = f"scammer_{scammer.id}"
            nodes.append(NetworkNode(
                id=scammer_node_id,
                label=f"Scammer {scammer.id[:6]}",
                type="scammer",
                risk_score=scammer.risk_score
            ))
            scammer_ids.add(scammer.id)
            
            # Get associated conversations
            convs = (await session.execute(
                select(Conversation).where(Conversation.scammer_id == scammer.id)
            )).scalars().all()
            
            for conv in convs:
                # Get extracted intel for this conversation
                intel = (await session.execute(
                    select(ExtractedIntelligence).where(ExtractedIntelligence.conversation_id == conv.id)
                )).scalars().all()
                
                for item in intel:
                    # Create node for intel
                    intel_node_id = f"intel_{item.entity_value}"
                    # Check if node exists (simple dedupe for response)
                    if not any(n.id == intel_node_id for n in nodes):
                        nodes.append(NetworkNode(
                            id=intel_node_id,
                            label=item.entity_value,
                            type=item.entity_type,
                            risk_score=scammer.risk_score # Inherit risk? Or 0
                        ))
                    
                    # Link scammer to intel
                    links.append(NetworkLink(
                        source=scammer_node_id,
                        target=intel_node_id,
                        type="used_identifier"
                    ))
        
        return UnifiedResponse(
            success=True,
            data=NetworkGraph(nodes=nodes, links=links),
            error=None
        )

@router.get("/recent-activity", response_model=UnifiedResponse[RecentActivity])
async def get_recent_activity(
    limit: int = 10,
    api_key: str = Depends(verify_api_key)
) -> UnifiedResponse[RecentActivity]:
    """Get real-time recent activity feed"""
    db = await get_database()
    async with db.session() as session:
        # Get latest messages
        messages = (await session.execute(
            select(Message).order_by(desc(Message.timestamp)).limit(limit)
        )).scalars().all()
        
        activities = []
        for msg in messages:
            activities.append(ActivityItem(
                id=str(msg.id),
                type="message",
                content=f"Message from {msg.role}: {msg.content[:50]}...",
                timestamp=msg.timestamp,
                severity="info" if msg.role == "honeypot" else "warning"
            ))
            
        return UnifiedResponse(
            success=True,
            data=RecentActivity(activities=activities),
            error=None
        )
