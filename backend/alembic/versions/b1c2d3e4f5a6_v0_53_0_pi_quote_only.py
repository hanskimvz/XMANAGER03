"""v0.53.0 PI 견적 대용 플래그 (매출/미수 집계 제외)

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-06-30

sales_document.is_quote_only 추가. PI를 견적서 대용으로 발행한 경우 True →
미실현 매출·미입금(수금) 집계에서 제외하여 허수를 막는다. 기본 False(=실주문).
"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_document",
                  sa.Column("is_quote_only", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("sales_document", "is_quote_only")
