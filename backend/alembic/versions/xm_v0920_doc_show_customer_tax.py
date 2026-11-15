"""v0.92.0 문서에 거래처 VAT/TAX ID(사업자등록번호) 표기 옵션

Revision ID: xm_v0920_doc_show_customer_tax
Revises: xm_v0910_po_custom_item
Create Date: 2026-08-19

해외 업체가 자사 VAT/TAX ID(NIP 등)를 PI 등 문서에 기재해 달라고 요청할 때,
체크 시 거래처 정보의 사업자등록번호(business_number)를 문서에 표기한다.
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0920_doc_show_customer_tax"
down_revision = "xm_v0910_po_custom_item"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_document", sa.Column(
        "show_customer_tax_id", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("sales_document", "show_customer_tax_id")
