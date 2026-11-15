"""add is_stub to parts

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-04-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'y5z6a7b8c9d0'
down_revision: Union[str, None] = 'x4y5z6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('parts', sa.Column('is_stub', sa.Boolean(), nullable=False, server_default='false', comment='자동 생성된 임시 부품 여부'))


def downgrade() -> None:
    op.drop_column('parts', 'is_stub')
