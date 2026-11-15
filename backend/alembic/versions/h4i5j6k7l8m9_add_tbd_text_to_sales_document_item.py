"""add quantity_text / unit_price_text / amount_text to sales_document_item

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-05-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'h4i5j6k7l8m9'
down_revision: Union[str, None] = 'g3h4i5j6k7l8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sales_document_item',
        sa.Column('quantity_text', sa.String(length=40), nullable=True))
    op.add_column('sales_document_item',
        sa.Column('unit_price_text', sa.String(length=40), nullable=True))
    op.add_column('sales_document_item',
        sa.Column('amount_text', sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column('sales_document_item', 'amount_text')
    op.drop_column('sales_document_item', 'unit_price_text')
    op.drop_column('sales_document_item', 'quantity_text')
