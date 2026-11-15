"""v0.72.0 영업문서 할인 사유(discount_reason) 컬럼 추가

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-27

할인 적용 시 사유를 견적서에 기록 → 추후 무분별한 할인 요청 근거 대응용.
"""
from alembic import op
import sqlalchemy as sa

revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_document", sa.Column("discount_reason", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_document", "discount_reason")
