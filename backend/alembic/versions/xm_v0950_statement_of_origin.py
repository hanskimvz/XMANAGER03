"""v0.95.0 원산지 신고문(Statement of Origin) 표기 플래그

Revision ID: xm_v0950_statement_of_origin
Revises: xm_v0940_hs_code_widen
Create Date: 2026-08-31

CI에 원산지 신고문 블록을 고객사별로 선택 표기.
- sales_document.show_statement_of_origin: 해당 문서 표기 여부
- business_partner.show_statement_of_origin: 거래처 기본값(문서 생성 시 프리필)
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0950_statement_of_origin"
down_revision = "xm_v0940_hs_code_widen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_document", sa.Column(
        "show_statement_of_origin", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("business_partner", sa.Column(
        "show_statement_of_origin", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("business_partner", "show_statement_of_origin")
    op.drop_column("sales_document", "show_statement_of_origin")
