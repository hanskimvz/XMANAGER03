"""add purchase order payment fields

Revision ID: f3g4h5i6j7k8
Revises: e2f3g4h5i6j7
Create Date: 2026-01-16

발주서에 결제 관련 필드 추가:
- is_paid: 결제 완료 여부
- paid_date: 결제일
- paid_amount: 결제 금액
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3g4h5i6j7k8'
down_revision = 'e2f3g4h5i6j7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 발주서에 결제 관련 필드 추가
    op.add_column('purchase_order', sa.Column('is_paid', sa.Boolean(), nullable=True, server_default='false', comment='결제 완료 여부'))
    op.add_column('purchase_order', sa.Column('paid_date', sa.Date(), nullable=True, comment='결제일'))
    op.add_column('purchase_order', sa.Column('paid_amount', sa.Numeric(precision=15, scale=2), nullable=True, comment='결제 금액'))


def downgrade() -> None:
    op.drop_column('purchase_order', 'paid_amount')
    op.drop_column('purchase_order', 'paid_date')
    op.drop_column('purchase_order', 'is_paid')
