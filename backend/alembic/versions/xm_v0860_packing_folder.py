"""v0.86.0 생산요청 포장사진 폴더 경로

Revision ID: xm_v0860_packing_folder
Revises: xm_v0840_insert_na
Create Date: 2026-08-11

출고 포장사진이 저장되는 폴더(납품 트리 기준 상대경로)를 생산요청에 저장.
번호 prefix 매칭/생성 결과를 최초 업로드 시 기록해 링크 안정화.
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0860_packing_folder"
down_revision = "xm_v0840_insert_na"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request", sa.Column("packing_folder", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("production_request", "packing_folder")
