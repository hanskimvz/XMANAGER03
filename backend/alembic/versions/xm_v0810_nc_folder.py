"""v0.81.0 파일 허브 — Nextcloud 폴더 경로 저장

Revision ID: xm_v0810_nc_folder
Revises: xm_v0800_log_edit_audit
Create Date: 2026-08-03

거래처/주문의 Nextcloud 폴더 상대경로를 최초 생성 시 저장(이후 불변) —
거래처명/PI번호가 바뀌어도 파일 링크가 유지되도록 함.
- business_partner.nextcloud_folder : 거래처 루트
- sales_document.nextcloud_folder   : 주문(영업문서) 폴더
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0810_nc_folder"
down_revision = "xm_v0800_log_edit_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("business_partner", sa.Column("nextcloud_folder", sa.String(length=500), nullable=True))
    op.add_column("sales_document", sa.Column("nextcloud_folder", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_document", "nextcloud_folder")
    op.drop_column("business_partner", "nextcloud_folder")
