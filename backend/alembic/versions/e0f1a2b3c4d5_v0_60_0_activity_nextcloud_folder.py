"""v0.60.0 영업활동 Nextcloud 저장 폴더

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-07-09

영업 대응 현황에 Nextcloud 저장 폴더(상대경로) 컬럼 추가.
문서 PDF 를 이 폴더로 자동 저장(로컬 동기화 → Nextcloud).
"""
from alembic import op
import sqlalchemy as sa

revision = "e0f1a2b3c4d5"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_activity", sa.Column("nextcloud_folder", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_activity", "nextcloud_folder")
