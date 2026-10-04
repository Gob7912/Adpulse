"""add telegram_message_id and raw_meta_snapshot to run_histories
 
Revision ID: 005_add_tg_msg_id_snapshot
Revises: 004_sending_unique
Create Date: 2026-10-04 20:00:00
 
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '005_add_tg_msg_id_snapshot'
down_revision: str | None = '004_sending_unique'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('run_histories', sa.Column('telegram_message_id', sa.Integer(), nullable=True))
    op.add_column('run_histories', sa.Column('raw_meta_snapshot', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('run_histories', 'raw_meta_snapshot')
    op.drop_column('run_histories', 'telegram_message_id')
