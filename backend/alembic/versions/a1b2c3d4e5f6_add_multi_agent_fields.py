"""Add multi-agent and external integration fields

Revision ID: a1b2c3d4e5f6
Revises: f3a8b5c2d1e0
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f3a8b5c2d1e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === AgentConfig table extensions ===
    
    # Add category column with default 'instructor'
    op.add_column('agentconfig', sa.Column('category', sa.String(20), nullable=False, server_default='instructor'))
    op.create_index(op.f('ix_agentconfig_category'), 'agentconfig', ['category'], unique=False)
    
    # Add is_external flag
    op.add_column('agentconfig', sa.Column('is_external', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add external_config JSONB column for webhook/OAuth configuration
    op.add_column('agentconfig', sa.Column('external_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add capabilities JSONB column
    op.add_column('agentconfig', sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    
    # === Create AgentTypeMetadata table ===
    op.create_table(
        'agenttypemetadata',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('type_name', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False, server_default=''),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(20), nullable=False, server_default='instructor'),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('default_system_prompt', sa.Text(), nullable=True),
        sa.Column('default_model_provider', sa.String(20), nullable=False, server_default='gemini'),
        sa.Column('default_model', sa.String(50), nullable=True),
        sa.Column('default_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('default_capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_agenttypemetadata_type_name'), 'agenttypemetadata', ['type_name'], unique=True)
    op.create_index(op.f('ix_agenttypemetadata_category'), 'agenttypemetadata', ['category'], unique=False)
    
    # === Seed system agent types ===
    op.execute("""
        INSERT INTO agenttypemetadata (id, type_name, display_name, category, is_system, description)
        VALUES 
            (gen_random_uuid(), 'teacher', 'Teacher', 'instructor', true, 'Guides and supervises discussions'),
            (gen_random_uuid(), 'student', 'Student', 'participant', true, 'Participates in discussions'),
            (gen_random_uuid(), 'design', 'Design', 'utility', true, 'Design and creative tasks'),
            (gen_random_uuid(), 'analytics', 'Analytics', 'utility', true, 'Analytics and reporting')
    """)


def downgrade() -> None:
    # Drop AgentTypeMetadata table
    op.drop_index(op.f('ix_agenttypemetadata_category'), table_name='agenttypemetadata')
    op.drop_index(op.f('ix_agenttypemetadata_type_name'), table_name='agenttypemetadata')
    op.drop_table('agenttypemetadata')
    
    # Remove columns from agentconfig
    op.drop_column('agentconfig', 'capabilities')
    op.drop_column('agentconfig', 'external_config')
    op.drop_column('agentconfig', 'is_external')
    op.drop_index(op.f('ix_agentconfig_category'), table_name='agentconfig')
    op.drop_column('agentconfig', 'category')
