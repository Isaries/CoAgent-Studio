"""add graphrag_last_synced_at to room

Revision ID: g1r2a3p4h5s6
Revises: k1b2a3s4e5n6
Create Date: 2026-03-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "g1r2a3p4h5s6"
down_revision = "k1b2a3s4e5n6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "room",
        sa.Column("graphrag_last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("room", "graphrag_last_synced_at")
