"""v0.93.0 공급업체 구분 코드 테이블

Revision ID: xm_v0930_supplier_type
Revises: xm_v0920_doc_show_customer_tax
Create Date: 2026-08-28

supplier_type: 공급업체를 분류하기 위한 관리 데이터(코드관리).
다른 코드 마스터 테이블(procurement_type 등)과 동일한 스키마.
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0930_supplier_type"
down_revision = "xm_v0920_doc_show_customer_tax"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_type",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name_ko", sa.String(length=50), nullable=False),
        sa.Column("name_en", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_supplier_type_id", "supplier_type", ["id"])
    op.create_index("ix_supplier_type_code", "supplier_type", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_supplier_type_code", table_name="supplier_type")
    op.drop_index("ix_supplier_type_id", table_name="supplier_type")
    op.drop_table("supplier_type")
