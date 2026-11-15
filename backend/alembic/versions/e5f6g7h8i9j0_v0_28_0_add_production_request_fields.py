"""v0.28.0 add production request additional fields

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6g7h8i9j0'
down_revision: str = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 생산요청서 헤더 필드 추가
    op.add_column('production_request', sa.Column('country', sa.String(100)))
    op.add_column('production_request', sa.Column('production_period', sa.String(50)))
    op.add_column('production_request', sa.Column('shipping_mark', sa.Text()))
    op.add_column('production_request', sa.Column('consignee', sa.Text()))
    op.add_column('production_request', sa.Column('prepared_by_name', sa.String(100)))

    # 품목별 고객 요구사항 필드 추가
    op.add_column('production_request_item', sa.Column('customer_requirements', sa.Text()))


def downgrade() -> None:
    op.drop_column('production_request_item', 'customer_requirements')
    op.drop_column('production_request', 'prepared_by_name')
    op.drop_column('production_request', 'consignee')
    op.drop_column('production_request', 'shipping_mark')
    op.drop_column('production_request', 'production_period')
    op.drop_column('production_request', 'country')
