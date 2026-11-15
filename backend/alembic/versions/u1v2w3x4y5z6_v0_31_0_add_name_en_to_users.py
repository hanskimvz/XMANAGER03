"""v0.31.0 add name_en to users

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-04-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'u1v2w3x4y5z6'
down_revision: str = 't0u1v2w3x4y5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('name_en', sa.String(100), nullable=True, comment='영문 이름'),
    )


def downgrade() -> None:
    op.drop_column('users', 'name_en')
