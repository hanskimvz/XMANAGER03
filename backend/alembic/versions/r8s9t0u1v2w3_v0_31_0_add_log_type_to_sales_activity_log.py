"""v0.31.0 add log_type to sales_activity_log

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-04-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'r8s9t0u1v2w3'
down_revision: str = 'q7r8s9t0u1v2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sales_activity_log',
        sa.Column('log_type', sa.String(20), nullable=False, server_default='COMMENT'),
    )


def downgrade() -> None:
    op.drop_column('sales_activity_log', 'log_type')
