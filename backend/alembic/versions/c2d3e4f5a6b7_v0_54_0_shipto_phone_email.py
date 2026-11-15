"""v0.54.0 Ship-To(수령자) 연락처 분리 — phone/email 컬럼 추가

Revision ID: c2d3e4f5a6b7
Revises: d3e4f5a6b7c8
Create Date: 2026-07-01

구매자(Buyer=고객사)와 제품 수령자(Consignee/Ship-To)가 다른 경우를 지원하기 위해
Ship-To 연락처를 담당자/전화/이메일로 분리한다.
기존 ship_to_name / ship_to_address / ship_to_contact(담당자명)에 더해
ship_to_phone / ship_to_email 를 추가. 모두 nullable(미입력 시 'Same as Buyer').
"""
from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a6b7"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_document", sa.Column("ship_to_phone", sa.String(length=50), nullable=True))
    op.add_column("sales_document", sa.Column("ship_to_email", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_document", "ship_to_email")
    op.drop_column("sales_document", "ship_to_phone")
