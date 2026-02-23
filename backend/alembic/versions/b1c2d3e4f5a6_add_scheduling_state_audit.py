"""add_scheduling_state_audit

Revision ID: b1c2d3e4f5a6
Revises: 67a4c87e67e1
Create Date: 2026-02-23

Adds:
- user_api_key: is_active, schedule_config
- roomagentlink: is_active, schedule_config, trigger_config, timestamps
- agent_room_state table (new)
- audit_log table (new)
- Data migration for old schedule_config format
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers
revision = 'b1c2d3e4f5a6'
down_revision = '49388994d55d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 1. user_api_key ---
    op.add_column('user_api_key', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('user_api_key', sa.Column('schedule_config', JSONB, nullable=True))

    # --- 2. roomagentlink ---
    op.add_column('roomagentlink', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('roomagentlink', sa.Column('schedule_config', JSONB, nullable=True))
    op.add_column('roomagentlink', sa.Column('trigger_config', JSONB, nullable=True))
    op.add_column('roomagentlink', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))
    op.add_column('roomagentlink', sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))
    op.add_column('roomagentlink', sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=True))

    # --- 3. agent_room_state (new table) ---
    op.create_table(
        'agent_room_state',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('room_id', UUID(as_uuid=True), sa.ForeignKey('room.id'), nullable=False, index=True),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agentconfig.id'), nullable=False, index=True),
        sa.Column('is_sleeping', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('message_count_since_last_reply', sa.Integer(), server_default='0', nullable=False),
        sa.Column('monologue_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_agent_message_at', sa.DateTime(), nullable=True),
        sa.Column('last_user_message_at', sa.DateTime(), nullable=True),
        sa.Column('active_overrides', JSONB, nullable=True),
        sa.Column('overrides_expires_at', sa.DateTime(), nullable=True),
        sa.Column('version', sa.Integer(), server_default='0', nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint('room_id', 'agent_id', name='uq_room_agent'),
    )

    # --- 4. audit_log (new table) ---
    op.create_table(
        'audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_type', sa.String(), nullable=False, index=True),
        sa.Column('entity_id', sa.String(), nullable=False, index=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('actor_id', UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('actor_type', sa.String(), server_default='user', nullable=False),
        sa.Column('old_value', JSONB, nullable=True),
        sa.Column('new_value', JSONB, nullable=True),
        sa.Column('extra_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True, index=True),
    )

    # --- 5. Data migration: convert old schedule_config format ---
    _migrate_schedule_configs()


def _migrate_schedule_configs():
    """Convert old { specific, general } format to new { mode, rules } format."""
    import json

    conn = op.get_bind()

    # Migrate agentconfig.schedule_config
    rows = conn.execute(
        sa.text("SELECT id, schedule_config FROM agentconfig WHERE schedule_config IS NOT NULL")
    ).fetchall()

    for row in rows:
        old = row[1]
        if isinstance(old, str):
            old = json.loads(old)
        if not isinstance(old, dict):
            continue

        # Skip if already in new format
        if "mode" in old and "rules" in old:
            continue

        new_config = _convert_old_to_new(old)
        if new_config:
            conn.execute(
                sa.text("UPDATE agentconfig SET schedule_config = :config WHERE id = :id"),
                {"config": json.dumps(new_config), "id": row[0]}
            )


def _convert_old_to_new(old: dict) -> dict:
    """Convert { specific: [...], general: {...} } → { mode: "whitelist", rules: [...] }"""
    rules = []

    # Specific dates → specific_date rules
    for s in old.get("specific", []):
        rules.append({
            "type": "specific_date",
            "date": s.get("date"),
            "time_range": [s.get("start", "00:00"), s.get("end", "23:59")]
        })

    # General rules
    general = old.get("general", {})
    for r in general.get("rules", []):
        mode = general.get("mode", "none")
        if mode == "range_weekly":
            rules.append({
                "type": "day_of_week",
                "days": r.get("days", []),
                "time_range": [r.get("start_time", "00:00"), r.get("end_time", "23:59")]
            })
        elif mode in ["range_daily", "none"]:
            rules.append({
                "type": "everyday",
                "time_range": [r.get("start_time", "00:00"), r.get("end_time", "23:59")]
            })

    return {"mode": "whitelist", "rules": rules} if rules else None


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('agent_room_state')

    op.drop_column('roomagentlink', 'updated_by')
    op.drop_column('roomagentlink', 'updated_at')
    op.drop_column('roomagentlink', 'created_at')
    op.drop_column('roomagentlink', 'trigger_config')
    op.drop_column('roomagentlink', 'schedule_config')
    op.drop_column('roomagentlink', 'is_active')

    op.drop_column('user_api_key', 'schedule_config')
    op.drop_column('user_api_key', 'is_active')
