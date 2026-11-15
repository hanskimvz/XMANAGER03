"""v0.27.0 add sales_activity and sales_activity_log tables

Revision ID: c3d4e5f6g7h9
Revises: b2c3d4e5f6g8
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6g7h9'
down_revision: str = 'b2c3d4e5f6g8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sales_activity',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('business_partner.id'), nullable=True),
        sa.Column('customer_name', sa.String(200)),
        sa.Column('country', sa.String(100)),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('assigned_to', sa.String(100)),
        sa.Column('status', sa.String(20), server_default='IN_PROGRESS'),
        sa.Column('next_step', sa.Text()),
        sa.Column('pending_reason', sa.Text()),
        sa.Column('expected_amount', sa.Numeric(15, 2)),
        sa.Column('expected_currency', sa.String(3), server_default='KRW'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'sales_activity_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('activity_id', sa.Integer(), sa.ForeignKey('sales_activity.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('logged_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_sales_activity_status', 'sales_activity', ['status'])
    op.create_index('ix_sales_activity_assigned_to', 'sales_activity', ['assigned_to'])
    op.create_index('ix_sales_activity_log_activity_id', 'sales_activity_log', ['activity_id'])


def downgrade() -> None:
    op.drop_table('sales_activity_log')
    op.drop_table('sales_activity')
