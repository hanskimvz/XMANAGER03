"""v0.91.0 발주서 BOM 미등록(자유입력) 품목 지원

Revision ID: xm_v0910_po_custom_item
Revises: xm_v0900_pr_box_plan
Create Date: 2026-08-18

발주서 품목이 반드시 부품(parts)이어야 하던 제약을 완화:
part_id를 nullable로 바꾸고, BOM 미등록 품목용 custom_product_code/name 추가.
(생산요청서 품목의 커스텀 품목 패턴과 동일)
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0910_po_custom_item"
down_revision = "xm_v0900_pr_box_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_order_item", sa.Column("custom_product_code", sa.String(length=100), nullable=True))
    op.add_column("purchase_order_item", sa.Column("custom_product_name", sa.String(length=200), nullable=True))
    op.alter_column("purchase_order_item", "part_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("purchase_order_item", "part_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("purchase_order_item", "custom_product_name")
    op.drop_column("purchase_order_item", "custom_product_code")
