"""add show_comparison to reports

Revision ID: 003_add_show_comparison
Revises: 002_add_is_test_and_unique
Create Date: 2026-10-04 15:30:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '003_add_show_comparison'
down_revision: str | None = '002_add_is_test_and_unique'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'reports',
        sa.Column('show_comparison', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )


def downgrade() -> None:
    op.drop_column('reports', 'show_comparison')
