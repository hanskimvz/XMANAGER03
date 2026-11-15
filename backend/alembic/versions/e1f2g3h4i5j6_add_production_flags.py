"""add insert_shipped / production_shipped / needs_review to production_request

Revision ID: e1f2g3h4i5j6
Revises: d0e1f2g3h4i5
Create Date: 2026-05-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, None] = 'd0e1f2g3h4i5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('production_request',
        sa.Column('insert_shipped', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('production_request',
        sa.Column('production_shipped', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('production_request',
        sa.Column('needs_review', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('production_request', 'needs_review')
    op.drop_column('production_request', 'production_shipped')
    op.drop_column('production_request', 'insert_shipped')
