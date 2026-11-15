"""v0.94.0 HS Code 컬럼 확장 (복수 코드 허용)

Revision ID: xm_v0940_hs_code_widen
Revises: xm_v0930_supplier_type
Create Date: 2026-08-31

CI 등에 커넥터+조립체처럼 서로 다른 HS Code가 함께 들어갈 수 있도록
sales_document.hs_code / business_partner.hs_code 를 String(20) → String(100) 확장.
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0940_hs_code_widen"
down_revision = "xm_v0930_supplier_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("sales_document", "hs_code",
                    existing_type=sa.String(length=20), type_=sa.String(length=100),
                    existing_nullable=True)
    op.alter_column("business_partner", "hs_code",
                    existing_type=sa.String(length=20), type_=sa.String(length=100),
                    existing_nullable=True)


def downgrade() -> None:
    op.alter_column("business_partner", "hs_code",
                    existing_type=sa.String(length=100), type_=sa.String(length=20),
                    existing_nullable=True)
    op.alter_column("sales_document", "hs_code",
                    existing_type=sa.String(length=100), type_=sa.String(length=20),
                    existing_nullable=True)
