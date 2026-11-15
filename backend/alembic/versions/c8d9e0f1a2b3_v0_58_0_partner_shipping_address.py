"""v0.58.0 거래처 배송지(다중) + 문서 배송지 선택

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-06

- business_partner_shipping_address: 거래처별 저장 배송지(다중)
- sales_document.ship_to_address_id: 문서에서 선택한 저장 배송지 FK
  (NULL이면 직접입력 ship_to_* 또는 Same as Buyer)
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_partner_shipping_address",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("partner_id", sa.Integer(),
                  sa.ForeignKey("business_partner.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("contact", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_bp_shipping_partner", "business_partner_shipping_address", ["partner_id"])
    op.add_column("sales_document", sa.Column("ship_to_address_id", sa.Integer(),
                  sa.ForeignKey("business_partner_shipping_address.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_sales_document_ship_to_address", "sales_document", ["ship_to_address_id"])


def downgrade() -> None:
    op.drop_index("ix_sales_document_ship_to_address", table_name="sales_document")
    op.drop_column("sales_document", "ship_to_address_id")
    op.drop_index("ix_bp_shipping_partner", table_name="business_partner_shipping_address")
    op.drop_table("business_partner_shipping_address")
