"""v0.78.0 영업활동 코멘트 첨부 + 거래처 기본 SHIPPING MARK/CONSIGNEE

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-07-29

- sales_activity_log.attachment_files (코멘트 스크린샷/사진 첨부)
- business_partner.default_shipping_mark / default_consignee (생산요청 자동 채움 기본값)
"""
from alembic import op
import sqlalchemy as sa

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_activity_log", sa.Column("attachment_files", sa.JSON(), nullable=True))
    op.add_column("business_partner", sa.Column("default_shipping_mark", sa.Text(), nullable=True))
    op.add_column("business_partner", sa.Column("default_consignee", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("business_partner", "default_consignee")
    op.drop_column("business_partner", "default_shipping_mark")
    op.drop_column("sales_activity_log", "attachment_files")
