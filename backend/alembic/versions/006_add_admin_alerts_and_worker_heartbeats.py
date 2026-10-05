"""add admin_alerts and worker_heartbeats tables

Revision ID: 006_add_admin_alerts_and_heartbeats
Revises: 005_add_tg_msg_id_snapshot
Create Date: 2026-10-05 15:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '006_admin_alerts_heartbeats'
down_revision: str | None = '005_add_tg_msg_id_snapshot'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. admin_alerts table for persistent deduplication
    op.create_table(
        'admin_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_key', sa.String(length=255), nullable=False),
        sa.Column('alert_type', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_alerts_alert_key', 'admin_alerts', ['alert_key'], unique=True)

    # 2. worker_heartbeats table
    op.create_table(
        'worker_heartbeats',
        sa.Column('worker_name', sa.String(length=100), nullable=False),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('worker_name')
    )


def downgrade() -> None:
    op.drop_table('worker_heartbeats')
    op.drop_index('ix_admin_alerts_alert_key', table_name='admin_alerts')
    op.drop_table('admin_alerts')
