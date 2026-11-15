"""v0.79.0 부품 전속(독점) 공급 계약 필드

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-07-29

parts에 전속계약(opt-in) 3필드 추가. 비보호 부품은 무영향(is_protected 기본 false).
- parts.is_protected (전속계약 여부)
- parts.protected_customer_id (전속 고객 FK)
- parts.protection_note (비고)
"""
from alembic import op
import sqlalchemy as sa

revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parts", sa.Column("is_protected", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("parts", sa.Column("protected_customer_id", sa.Integer(), nullable=True))
    op.add_column("parts", sa.Column("protection_note", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_parts_protected_customer", "parts", "business_partner",
        ["protected_customer_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_parts_protected_customer", "parts", type_="foreignkey")
    op.drop_column("parts", "protection_note")
    op.drop_column("parts", "protected_customer_id")
    op.drop_column("parts", "is_protected")
