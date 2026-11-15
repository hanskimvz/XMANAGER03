"""v0.88.0 생산요청 품목 누적 CI 발행수량(분할선적)

Revision ID: xm_v0880_pr_item_ci_qty
Revises: xm_v0870_pr_is_draft
Create Date: 2026-08-13

분할선적: 출고건 전량을 여러 CI(배송)로 나눠 발행. 각 품목의 누적 발행수량을
추적해 잔여(= 요청수량 - ci_quantity)를 계산. 기존 데이터는 0(백필 없음).
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0880_pr_item_ci_qty"
down_revision = "xm_v0870_pr_is_draft"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_request_item",
        sa.Column("ci_quantity", sa.Numeric(15, 3), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("production_request_item", "ci_quantity")
