"""Add My Agent fields to AgentConfig

Revision ID: f3a8b5c2d1e0
Revises: cc5f67b71291
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a8b5c2d1e0'
down_revision = 'cc5f67b71291'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add parent_config_id column with self-referential FK
    op.add_column('agentconfig', sa.Column('parent_config_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_agentconfig_parent_config_id'), 'agentconfig', ['parent_config_id'], unique=False)
    op.create_foreign_key(
        'fk_agentconfig_parent_config_id',
        'agentconfig',
        'agentconfig',
        ['parent_config_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Add is_template column
    op.add_column('agentconfig', sa.Column('is_template', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_constraint('fk_agentconfig_parent_config_id', 'agentconfig', type_='foreignkey')
    op.drop_index(op.f('ix_agentconfig_parent_config_id'), table_name='agentconfig')
    op.drop_column('agentconfig', 'parent_config_id')
    op.drop_column('agentconfig', 'is_template')
