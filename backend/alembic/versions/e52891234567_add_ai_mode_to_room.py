"""Add ai_mode to room

Revision ID: e52891234567
Revises: c437303aa424
Create Date: 2026-01-08 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "e52891234567"
down_revision: Union[str, None] = "c437303aa424"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ai_mode column with a default value for existing rows
    # We use valid default 'teacher_only' which is consistent with the model
    op.add_column(
        "room",
        sa.Column(
            "ai_mode",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default=sa.text("'teacher_only'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("room", "ai_mode")
