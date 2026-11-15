"""v0.26.0 add description_ko to product_description_code

Revision ID: b2c3d4e5f6g8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g8'
down_revision: str = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('product_description_code', sa.Column(
        'description_ko', sa.Text(), nullable=True,
        comment='한글 설명 (국내 고객용)'
    ))


def downgrade() -> None:
    op.drop_column('product_description_code', 'description_ko')
