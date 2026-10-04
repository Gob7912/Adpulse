"""add is_test and unique constraint to run_histories

Revision ID: 002_add_is_test_and_unique
Revises: 001_initial_schema
Create Date: 2026-10-04 15:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '002_add_is_test_and_unique'
down_revision: str | None = '001_initial_schema'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'run_histories',
        sa.Column('is_test', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    op.create_index(
        'uq_run_histories_report_period_success',
        'run_histories',
        ['report_id', 'period_start', 'period_end'],
        unique=True,
        postgresql_where=sa.text("is_test = false AND status IN ('success', 'no_data')")
    )


def downgrade() -> None:
    op.drop_index('uq_run_histories_report_period_success', table_name='run_histories')
    op.drop_column('run_histories', 'is_test')
