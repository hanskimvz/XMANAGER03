"""add position to users

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'w3x4y5z6a7b8'
down_revision: Union[str, None] = 'v2w3x4y5z6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('position', sa.String(50), nullable=True, comment='직급'))
    # 직급 데이터 입력
    op.execute("UPDATE users SET position = 'CTO' WHERE username = 'admin'")
    op.execute("UPDATE users SET position = '과장' WHERE username = 'lsj'")
    op.execute("UPDATE users SET position = '사원' WHERE username = 'yhsung42'")
    op.execute("UPDATE users SET position = '사원' WHERE username = 'suc'")


def downgrade() -> None:
    op.drop_column('users', 'position')
