"""v0.83.0 생산요청 커스텀(외주) 항목

Revision ID: xm_v0830_pr_custom_item
Revises: xm_v0820_default_dest
Create Date: 2026-08-10

BOM에 없는 제품(외주 부품 등)도 생산요청 항목으로 등록 가능하게:
- production_request_item.product_part_id 를 nullable 로 변경
- custom_product_code / custom_product_name 컬럼 추가(직접 입력 품번/품명)
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0830_pr_custom_item"
down_revision = "xm_v0820_default_dest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request_item", sa.Column("custom_product_code", sa.String(length=100), nullable=True))
    op.add_column("production_request_item", sa.Column("custom_product_name", sa.String(length=200), nullable=True))
    op.alter_column("production_request_item", "product_part_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("production_request_item", "product_part_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("production_request_item", "custom_product_name")
    op.drop_column("production_request_item", "custom_product_code")
