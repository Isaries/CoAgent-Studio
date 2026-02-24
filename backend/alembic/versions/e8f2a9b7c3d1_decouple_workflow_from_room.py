"""
Decouple Workflow from Room – Architecture Migration

Revision ID: e8f2a9b7c3d1
Revises: f3a8b5c2d1e0
Create Date: 2026-02-24

This migration:
1. Creates the new ``workflow`` table (decoupled from Room).
2. Creates the ``trigger_policy`` table.
3. Migrates data from the old ``room_workflow`` table to ``workflow``.
4. Adds ``attached_workflow_id`` to the ``room`` table.
5. Links each Room to its migrated Workflow.
6. Updates ``workflow_run`` to use ``session_id`` instead of ``room_id``.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from uuid import uuid4


# revision identifiers
revision = "e8f2a9b7c3d1"
down_revision = "817324835f6c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Create new `workflow` table ────────────────────────────────
    op.create_table(
        "workflow",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, server_default="Default Workflow"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("graph_data", JSONB, nullable=False, server_default='{"nodes": [], "edges": []}'),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True),
    )

    # ── 2. Create `trigger_policy` table ──────────────────────────────
    op.create_table(
        "trigger_policy",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, server_default="Untitled Trigger"),
        sa.Column("event_type", sa.String(), nullable=False, server_default="user_message"),
        sa.Column("conditions", JSONB, nullable=False, server_default="{}"),
        sa.Column("target_workflow_id", sa.Uuid(), sa.ForeignKey("workflow.id"), nullable=False),
        sa.Column("scope_session_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("user.id"), nullable=True),
    )
    op.create_index("ix_trigger_policy_target_workflow_id", "trigger_policy", ["target_workflow_id"])
    op.create_index("ix_trigger_policy_scope_session_id", "trigger_policy", ["scope_session_id"])

    # ── 3. Add `attached_workflow_id` to `room` ──────────────────────
    op.add_column(
        "room",
        sa.Column(
            "attached_workflow_id",
            sa.Uuid(),
            sa.ForeignKey("workflow.id"),
            nullable=True,
        ),
    )

    # ── 4. Migrate data from `room_workflow` → `workflow` ─────────────
    # Copy each row from old table to new table, then link Room.
    conn = op.get_bind()
    old_rows = conn.execute(
        sa.text("SELECT id, room_id, name, is_active, graph_data, created_at, updated_at FROM room_workflow")
    ).fetchall()

    for row in old_rows:
        wf_id = row[0]  # Keep the same UUID
        room_id = row[1]
        name = row[2]
        is_active = row[3]
        graph_data = row[4]
        created_at = row[5]
        updated_at = row[6]

        # Insert into new workflow table
        conn.execute(
            sa.text(
                """
                INSERT INTO workflow (id, name, is_active, graph_data, created_at, updated_at)
                VALUES (:id, :name, :is_active, :graph_data, :created_at, :updated_at)
                """
            ),
            {
                "id": str(wf_id),
                "name": name or "Default Workflow",
                "is_active": is_active,
                "graph_data": graph_data if isinstance(graph_data, str) else str(graph_data),
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )

        # Link the Room to the new Workflow
        conn.execute(
            sa.text("UPDATE room SET attached_workflow_id = :wf_id WHERE id = :room_id"),
            {"wf_id": str(wf_id), "room_id": str(room_id)},
        )

    # ── 5. Update `workflow_run` table ────────────────────────────────
    # Add `session_id` and `trigger_payload`, then copy `room_id` values to `session_id`
    op.add_column("workflow_run", sa.Column("session_id", sa.String(), nullable=True))
    op.add_column("workflow_run", sa.Column("trigger_payload", JSONB, nullable=True, server_default="{}"))

    # Copy room_id to session_id (as string)
    conn.execute(
        sa.text("UPDATE workflow_run SET session_id = CAST(room_id AS TEXT)")
    )

    # Make session_id NOT NULL now
    op.alter_column("workflow_run", "session_id", nullable=False)
    op.create_index("ix_workflow_run_session_id", "workflow_run", ["session_id"])

    # Update foreign key: workflow_run.workflow_id → workflow.id (instead of room_workflow.id)
    # First drop old FK constraint if it exists, then add new one
    try:
        op.drop_constraint("workflow_run_workflow_id_fkey", "workflow_run", type_="foreignkey")
    except Exception:
        pass  # Constraint might not exist by that name
    
    op.create_foreign_key(
        "workflow_run_workflow_id_fkey",
        "workflow_run", "workflow",
        ["workflow_id"], ["id"],
    )

    # Drop the old room_id column from workflow_run (data preserved in session_id)
    try:
        op.drop_column("workflow_run", "room_id")
    except Exception:
        pass

    # Drop the old trigger_message_id if it exists
    try:
        op.drop_column("workflow_run", "trigger_message_id")
    except Exception:
        pass


def downgrade() -> None:
    # Re-add room_id to workflow_run
    op.add_column("workflow_run", sa.Column("room_id", sa.Uuid(), nullable=True))

    # Drop new columns from workflow_run
    op.drop_column("workflow_run", "trigger_payload")
    op.drop_column("workflow_run", "session_id")

    # Drop attached_workflow_id from room
    op.drop_column("room", "attached_workflow_id")

    # Drop new tables
    op.drop_table("trigger_policy")
    op.drop_table("workflow")
