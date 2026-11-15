"""v0.30.0 add inquiry_type to sales_activity

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i9j0k1l2m3n4'
down_revision: str = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sales_activity',
        sa.Column('inquiry_type', sa.String(20), server_default='GENERAL', nullable=True),
    )


def downgrade() -> None:
    op.drop_column('sales_activity', 'inquiry_type')
