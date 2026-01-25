"""
Database Models - SQLAlchemy models for persistent storage
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    Text, JSON, ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ConversationState(str, Enum):
    """Conversation state enum"""
    INITIAL = "initial"
    NORMAL_CHAT = "normal_chat"
    SCAM_SUSPECTED = "scam_suspected"
    HONEYPOT_ENGAGED = "honeypot_engaged"
    INTEL_EXTRACTION = "intel_extraction"
    SAFE_TERMINATION = "safe_termination"
    TERMINATED = "terminated"


class Conversation(Base):
    """Stores conversation metadata and state"""
    __tablename__ = "conversations"
    
    id = Column(String(50), primary_key=True)
    scammer_id = Column(String(50), ForeignKey("scammer_profiles.id"), nullable=True)
    
    # State
    state = Column(SQLEnum(ConversationState), default=ConversationState.INITIAL)
    turn_count = Column(Integer, default=0)
    scam_score = Column(Float, default=0.0)
    persona_type = Column(String(50), nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Status
    is_terminated = Column(Boolean, default=False)
    termination_reason = Column(String(100), nullable=True)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    extracted_intel = relationship("ExtractedIntelligence", back_populates="conversation", cascade="all, delete-orphan")
    agent_decisions = relationship("AgentDecision", back_populates="conversation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_conversations_scammer_id", "scammer_id"),
        Index("ix_conversations_state", "state"),
        Index("ix_conversations_started_at", "started_at"),
    )


class Message(Base):
    """Stores individual messages in a conversation"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id"), nullable=False)
    
    # Message content
    role = Column(String(20), nullable=False)  # 'scammer' or 'honeypot'
    content = Column(Text, nullable=False)
    turn_number = Column(Integer, nullable=False)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, nullable=True)
    
    # Analysis
    scam_score = Column(Float, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_timestamp", "timestamp"),
    )


class ScammerProfile(Base):
    """Stores scammer profiles with risk evolution"""
    __tablename__ = "scammer_profiles"
    
    id = Column(String(50), primary_key=True)
    
    # Risk assessment
    risk_score = Column(Float, default=0.5)
    risk_level = Column(String(20), default="medium")
    
    # Identifiers (stored as JSON for flexibility)
    identifiers = Column(JSON, default=dict)
    # Example: {"phone": ["+91-xxx"], "upi": ["xxx@upi"], "email": []}
    
    # Statistics
    conversation_count = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    
    # Behavior analysis
    scam_types = Column(JSON, default=list)  # ["lottery", "tech_support"]
    behavior_patterns = Column(JSON, default=list)
    
    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", backref="scammer_profile")
    
    __table_args__ = (
        Index("ix_scammer_profiles_risk_score", "risk_score"),
        Index("ix_scammer_profiles_last_seen", "last_seen"),
    )


class ExtractedIntelligence(Base):
    """Stores extracted entities and intelligence"""
    __tablename__ = "extracted_intelligence"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id"), nullable=False)
    
    # Entity information
    entity_type = Column(String(50), nullable=False)  # 'upi_id', 'phone', 'bank_account', etc.
    entity_value = Column(String(500), nullable=False)
    
    # Extraction metadata
    confidence = Column(Float, default=0.0)
    extraction_method = Column(String(50))  # 'regex', 'llm', 'hybrid'
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    
    # Validation
    is_validated = Column(Boolean, default=False)
    is_fake = Column(Boolean, default=False)
    
    # Timestamps
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="extracted_intel")
    
    __table_args__ = (
        Index("ix_extracted_intel_entity_type", "entity_type"),
        Index("ix_extracted_intel_entity_value", "entity_value"),
        Index("ix_extracted_intel_conversation_id", "conversation_id"),
    )


class AgentDecision(Base):
    """Stores agent decisions for audit trail"""
    __tablename__ = "agent_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id"), nullable=False)
    
    # Decision details
    agent_type = Column(String(50), nullable=False)  # 'planner', 'conversation', 'extraction', 'evaluator'
    decision_type = Column(String(50), nullable=False)  # 'state_transition', 'persona_switch', 'termination'
    decision_value = Column(String(500), nullable=False)
    
    # Context
    reasoning = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    
    # Model info
    model_used = Column(String(50), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    # Timestamps
    decided_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="agent_decisions")
    
    __table_args__ = (
        Index("ix_agent_decisions_conversation_id", "conversation_id"),
        Index("ix_agent_decisions_agent_type", "agent_type"),
    )


class AuditLog(Base):
    """Stores system audit logs"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event info
    event_type = Column(String(50), nullable=False)
    event_description = Column(Text, nullable=False)
    
    # Context
    conversation_id = Column(String(50), nullable=True)
    user_id = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    # Details
    details = Column(JSON, nullable=True)
    severity = Column(String(20), default="info")  # 'debug', 'info', 'warning', 'error', 'critical'
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_severity", "severity"),
    )


class RiskScore(Base):
    """Stores risk score history for analysis"""
    __tablename__ = "risk_scores"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id"), nullable=False)
    
    # Score details
    score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    
    # Components
    rule_based_score = Column(Float, nullable=True)
    llm_score = Column(Float, nullable=True)
    
    # Signals
    signals = Column(JSON, nullable=True)
    reasons = Column(JSON, nullable=True)
    
    # Timestamp
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_risk_scores_conversation_id", "conversation_id"),
        Index("ix_risk_scores_score", "score"),
    )
