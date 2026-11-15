"""v0.29.0 add work_order_id to production_request_item

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6g7h8i9j0k1'
down_revision: str = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('production_request_item', sa.Column(
        'work_order_id', sa.Integer(),
        sa.ForeignKey('work_order.id'),
        nullable=True,
        comment='연결된 작업지시서 ID'
    ))


def downgrade() -> None:
    op.drop_column('production_request_item', 'work_order_id')
