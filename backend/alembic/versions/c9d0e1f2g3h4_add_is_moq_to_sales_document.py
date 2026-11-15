"""add is_moq to sales_document

Revision ID: c9d0e1f2g3h4
Revises: b8c9d0e1f2g3
Create Date: 2026-04-22
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c9d0e1f2g3h4'
down_revision: Union[str, None] = 'b8c9d0e1f2g3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sales_document', sa.Column('is_moq', sa.Boolean(), nullable=False, server_default='false', comment='MOQ 가격표 견적 여부'))


def downgrade() -> None:
    op.drop_column('sales_document', 'is_moq')
