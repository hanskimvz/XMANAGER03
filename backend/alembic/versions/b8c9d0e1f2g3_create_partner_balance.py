"""create partner_balance_transaction table

Revision ID: b8c9d0e1f2g3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b8c9d0e1f2g3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'partner_balance_transaction',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('partner_id', sa.Integer(), sa.ForeignKey('business_partner.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('transaction_type', sa.String(20), nullable=False, comment='DEPOSIT/DEDUCT'),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('currency', sa.String(10), server_default='USD'),
        sa.Column('balance_after', sa.Numeric(15, 2), nullable=False),
        sa.Column('reference_doc_number', sa.String(50), nullable=True),
        sa.Column('reference_doc_id', sa.Integer(), nullable=True),
        sa.Column('memo', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('partner_balance_transaction')
