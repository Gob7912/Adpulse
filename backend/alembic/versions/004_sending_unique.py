"""update unique constraint to include sending status in run_histories

Revision ID: 004_update_run_histories_unique_sending
Revises: 003_add_show_comparison
Create Date: 2026-10-04 16:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '004_sending_unique'
down_revision: str | None = '003_add_show_comparison'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop previous partial index
    op.drop_index('uq_run_histories_report_period_success', table_name='run_histories')
    # Re-create partial index covering 'success', 'no_data', and 'sending'
    op.create_index(
        'uq_run_histories_report_period_success',
        'run_histories',
        ['report_id', 'period_start', 'period_end'],
        unique=True,
        postgresql_where=sa.text("is_test = false AND status IN ('success', 'no_data', 'sending')")
    )


def downgrade() -> None:
    op.drop_index('uq_run_histories_report_period_success', table_name='run_histories')
    op.create_index(
        'uq_run_histories_report_period_success',
        'run_histories',
        ['report_id', 'period_start', 'period_end'],
        unique=True,
        postgresql_where=sa.text("is_test = false AND status IN ('success', 'no_data')")
    )
