"""add graphrag room settings

Revision ID: a1f3g7h9k2m4
Revises: e8f2a9b7c3d1
Create Date: 2026-03-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1f3g7h9k2m4"
down_revision = "e8f2a9b7c3d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "room",
        sa.Column(
            "graphrag_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "room",
        sa.Column(
            "graphrag_extraction_model",
            sa.String(),
            nullable=False,
            server_default="gpt-4o-mini",
        ),
    )
    op.add_column(
        "room",
        sa.Column(
            "graphrag_summarization_model",
            sa.String(),
            nullable=False,
            server_default="gpt-4o-mini",
        ),
    )


def downgrade() -> None:
    op.drop_column("room", "graphrag_summarization_model")
    op.drop_column("room", "graphrag_extraction_model")
    op.drop_column("room", "graphrag_enabled")
