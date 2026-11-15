"""v0.26.0 add trade_type to business_partner

Revision ID: a1b2c3d4e5f7
Revises: 753de169ebaa
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: str = '753de169ebaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('business_partner', sa.Column(
        'trade_type', sa.String(10), server_default='EXPORT',
        comment='거래유형 (DOMESTIC: 국내, EXPORT: 해외)'
    ))


def downgrade() -> None:
    op.drop_column('business_partner', 'trade_type')
