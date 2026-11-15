"""v0.29.0 add work_order_task table

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g7h8i9j0k1l2'
down_revision: str = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'work_order_task',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('work_order_id', sa.Integer(), sa.ForeignKey('work_order.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_name', sa.String(100), nullable=False),
        sa.Column('assigned_team', sa.String(100)),
        sa.Column('status', sa.String(20), server_default='PENDING'),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('remarks', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_work_order_task_wo_id', 'work_order_task', ['work_order_id'])


def downgrade() -> None:
    op.drop_table('work_order_task')
