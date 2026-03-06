"""add knowledge_base table and FK references

Revision ID: k1b2a3s4e5n6
Revises: r1e2d3e4s5i6
Create Date: 2026-03-04 00:01:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "k1b2a3s4e5n6"
down_revision = "r1e2d3e4s5i6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Step 1: Create knowledge_base table ---
    op.create_table(
        "knowledge_base",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "space_id",
            postgresql.UUID(),
            sa.ForeignKey("space.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "room_id",
            postgresql.UUID(),
            sa.ForeignKey("room.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "source_type",
            sa.String(),
            server_default="conversation",
            nullable=False,
        ),
        sa.Column("build_status", sa.String(), server_default="idle", nullable=False),
        sa.Column("extraction_model", sa.String(), nullable=True),
        sa.Column("summarization_model", sa.String(), nullable=True),
        sa.Column("node_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("edge_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_built_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # --- Step 2: Add KB FK references ---
    op.add_column(
        "room",
        sa.Column(
            "room_kb_id",
            postgresql.UUID(),
            sa.ForeignKey("knowledge_base.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("room", "room_kb_id")
    op.drop_table("knowledge_base")
