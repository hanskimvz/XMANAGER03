"""v0.52.0 sales document customer contact (영업문서 담당자 선택)

Revision ID: a0b1c2d3e4f5
Revises: z9a0b1c2d3e4
Create Date: 2026-06-29

sales_document 에 customer_contact_id(FK business_partner_contact) 추가.
문서별로 고객사 담당자를 지정. NULL이면 거래처 기본 담당자(manager_name)로 폴백.
"""
from alembic import op
import sqlalchemy as sa

revision = "a0b1c2d3e4f5"
down_revision = "z9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_document",
                  sa.Column("customer_contact_id", sa.Integer(), nullable=True))
    op.create_index("ix_sales_document_customer_contact_id", "sales_document",
                    ["customer_contact_id"])
    op.create_foreign_key(
        "fk_sales_document_customer_contact", "sales_document",
        "business_partner_contact", ["customer_contact_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_sales_document_customer_contact", "sales_document", type_="foreignkey")
    op.drop_index("ix_sales_document_customer_contact_id", table_name="sales_document")
    op.drop_column("sales_document", "customer_contact_id")
