"""v0.71.0 영업문서 할인/배송비 컬럼 추가

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-07-27

견적서/PI 등에 품목과 별개로 할인(discount)·배송비(shipping)를 입력해 총액에 반영.
NULL = 미적용(체크 해제), 값 있으면 총액 = 소계 - 할인 + 배송비.
"""
from alembic import op
import sqlalchemy as sa

revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_document", sa.Column("discount_amount", sa.Numeric(15, 2), nullable=True))
    op.add_column("sales_document", sa.Column("shipping_fee", sa.Numeric(15, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_document", "shipping_fee")
    op.drop_column("sales_document", "discount_amount")
