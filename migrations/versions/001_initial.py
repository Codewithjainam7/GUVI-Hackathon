"""
Initial migration - Create all tables

Revision ID: 001_initial
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scammer_profiles table
    op.create_table(
        'scammer_profiles',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('risk_score', sa.Float(), default=0.5),
        sa.Column('risk_level', sa.String(20), default='medium'),
        sa.Column('identifiers', sa.JSON(), default=dict),
        sa.Column('conversation_count', sa.Integer(), default=0),
        sa.Column('total_messages', sa.Integer(), default=0),
        sa.Column('scam_types', sa.JSON(), default=list),
        sa.Column('behavior_patterns', sa.JSON(), default=list),
        sa.Column('first_seen', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_seen', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_scammer_profiles_risk_score', 'scammer_profiles', ['risk_score'])
    op.create_index('ix_scammer_profiles_last_seen', 'scammer_profiles', ['last_seen'])
    
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('scammer_id', sa.String(50), sa.ForeignKey('scammer_profiles.id'), nullable=True),
        sa.Column('state', sa.String(50), default='initial'),
        sa.Column('turn_count', sa.Integer(), default=0),
        sa.Column('scam_score', sa.Float(), default=0.0),
        sa.Column('persona_type', sa.String(50), nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_activity', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('is_terminated', sa.Boolean(), default=False),
        sa.Column('termination_reason', sa.String(100), nullable=True),
    )
    op.create_index('ix_conversations_scammer_id', 'conversations', ['scammer_id'])
    op.create_index('ix_conversations_state', 'conversations', ['state'])
    op.create_index('ix_conversations_started_at', 'conversations', ['started_at'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.String(50), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('scam_score', sa.Float(), nullable=True),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_timestamp', 'messages', ['timestamp'])
    
    # Create extracted_intelligence table
    op.create_table(
        'extracted_intelligence',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.String(50), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_value', sa.String(500), nullable=False),
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('extraction_method', sa.String(50)),
        sa.Column('source_message_id', sa.Integer(), sa.ForeignKey('messages.id'), nullable=True),
        sa.Column('is_validated', sa.Boolean(), default=False),
        sa.Column('is_fake', sa.Boolean(), default=False),
        sa.Column('extracted_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_extracted_intel_entity_type', 'extracted_intelligence', ['entity_type'])
    op.create_index('ix_extracted_intel_entity_value', 'extracted_intelligence', ['entity_value'])
    op.create_index('ix_extracted_intel_conversation_id', 'extracted_intelligence', ['conversation_id'])
    
    # Create agent_decisions table
    op.create_table(
        'agent_decisions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.String(50), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('decision_type', sa.String(50), nullable=False),
        sa.Column('decision_value', sa.String(500), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_agent_decisions_conversation_id', 'agent_decisions', ['conversation_id'])
    op.create_index('ix_agent_decisions_agent_type', 'agent_decisions', ['agent_type'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_description', sa.Text(), nullable=False),
        sa.Column('conversation_id', sa.String(50), nullable=True),
        sa.Column('user_id', sa.String(50), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('severity', sa.String(20), default='info'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_severity', 'audit_logs', ['severity'])
    
    # Create risk_scores table
    op.create_table(
        'risk_scores',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.String(50), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('rule_based_score', sa.Float(), nullable=True),
        sa.Column('llm_score', sa.Float(), nullable=True),
        sa.Column('signals', sa.JSON(), nullable=True),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_risk_scores_conversation_id', 'risk_scores', ['conversation_id'])
    op.create_index('ix_risk_scores_score', 'risk_scores', ['score'])


def downgrade() -> None:
    op.drop_table('risk_scores')
    op.drop_table('audit_logs')
    op.drop_table('agent_decisions')
    op.drop_table('extracted_intelligence')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('scammer_profiles')
