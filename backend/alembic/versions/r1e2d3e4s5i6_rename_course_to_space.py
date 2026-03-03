"""rename course to space and add new columns

Revision ID: r1e2d3e4s5i6
Revises: a1f3g7h9k2m4
Create Date: 2026-03-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "r1e2d3e4s5i6"
down_revision = "a1f3g7h9k2m4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Step 1: Rename tables ---
    op.rename_table("course", "space")
    op.rename_table("user_course_link", "user_space_link")

    # --- Step 2: Rename FK columns ---
    # user_space_link: course_id → space_id
    op.alter_column("user_space_link", "course_id", new_column_name="space_id")

    # room: course_id → space_id
    op.alter_column("room", "course_id", new_column_name="space_id")

    # announcement: course_id → space_id
    op.alter_column("announcement", "course_id", new_column_name="space_id")

    # analytics_report: course_id → space_id
    op.alter_column("analytics_report", "course_id", new_column_name="space_id")

    # --- Step 3: Add new columns to space ---
    op.add_column(
        "space",
        sa.Column("preset", sa.String(), nullable=True, server_default="custom"),
    )

    # --- Step 4: Add enabled_tabs to room ---
    op.add_column(
        "room",
        sa.Column(
            "enabled_tabs",
            postgresql.JSONB(),
            nullable=True,
            server_default='{"chat": true, "board": false, "docs": true, "process": true, "graph": false}',
        ),
    )


def downgrade() -> None:
    # Remove new columns
    op.drop_column("room", "enabled_tabs")
    op.drop_column("space", "preset")

    # Rename FK columns back
    op.alter_column("analytics_report", "space_id", new_column_name="course_id")
    op.alter_column("announcement", "space_id", new_column_name="course_id")
    op.alter_column("room", "space_id", new_column_name="course_id")
    op.alter_column("user_space_link", "space_id", new_column_name="course_id")

    # Rename tables back
    op.rename_table("user_space_link", "user_course_link")
    op.rename_table("space", "course")
