"""Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-29 16:30:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # meta_connections
    op.create_table(
        'meta_connections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False),
        sa.Column('meta_user_id', sa.String(length=100), nullable=True),
        sa.Column('meta_user_name', sa.String(length=255), nullable=True),
        sa.Column('meta_avatar_url', sa.Text(), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_meta_connections_user_id'), 'meta_connections', ['user_id'], unique=True)

    # reports
    op.create_table(
        'reports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('meta_account_id', sa.String(length=100), nullable=False),
        sa.Column('meta_account_name', sa.String(length=255), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('account_timezone', sa.String(length=100), nullable=False, server_default='UTC'),
        sa.Column('campaign_scope_type', sa.String(length=20), nullable=False, server_default='all'),
        sa.Column('campaign_filter_goals', sa.JSON(), nullable=True),
        sa.Column('campaign_filter_name', sa.String(length=255), nullable=True),
        sa.Column('specific_campaign_ids', sa.JSON(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('smart_metric_detection', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('metric_labels', sa.JSON(), nullable=True),
        sa.Column('metric_lang', sa.String(length=10), nullable=False, server_default='ru'),
        sa.Column('periodicity', sa.String(length=20), nullable=False, server_default='daily'),
        sa.Column('schedule_time', sa.String(length=10), nullable=False, server_default='08:00'),
        sa.Column('schedule_weekday', sa.Integer(), nullable=True),
        sa.Column('schedule_monthday', sa.Integer(), nullable=True),
        sa.Column('send_timezone', sa.String(length=100), nullable=False, server_default='Asia/Tashkent'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_status', sa.String(length=20), nullable=True),
        sa.Column('last_run_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_user_id'), 'reports', ['user_id'])
    op.create_index(op.f('ix_reports_next_run_at'), 'reports', ['next_run_at'])

    # destinations
    op.create_table(
        'destinations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=36), nullable=False),
        sa.Column('destination_type', sa.String(length=20), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('telegram_target_type', sa.String(length=20), nullable=True),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=True),
        sa.Column('telegram_thread_id', sa.Integer(), nullable=True),
        sa.Column('telegram_chat_title', sa.String(length=255), nullable=True),
        sa.Column('one_time_code', sa.String(length=64), nullable=True),
        sa.Column('is_connected', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sheets_url', sa.Text(), nullable=True),
        sa.Column('sheets_spreadsheet_id', sa.String(length=100), nullable=True),
        sa.Column('sheets_tab_name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_destinations_report_id'), 'destinations', ['report_id'])
    op.create_index(op.f('ix_destinations_one_time_code'), 'destinations', ['one_time_code'])

    # run_histories
    op.create_table(
        'run_histories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('period_start', sa.String(length=30), nullable=False),
        sa.Column('period_end', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0'),
        sa.Column('metrics_data', sa.JSON(), nullable=True),
        sa.Column('telegram_delivered', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('telegram_error', sa.Text(), nullable=True),
        sa.Column('sheets_delivered', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sheets_error', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_histories_report_id'), 'run_histories', ['report_id'])
    op.create_index(op.f('ix_run_histories_user_id'), 'run_histories', ['user_id'])

def downgrade() -> None:
    op.drop_table('run_histories')
    op.drop_table('destinations')
    op.drop_table('reports')
    op.drop_table('meta_connections')
    op.drop_table('users')
