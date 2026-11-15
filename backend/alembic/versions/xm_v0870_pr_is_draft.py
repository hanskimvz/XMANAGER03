"""v0.87.0 생산요청 초안(is_draft) 플래그

Revision ID: xm_v0870_pr_is_draft
Revises: xm_v0860_packing_folder
Create Date: 2026-08-12

PI 자동생성 초안을 생산팀에 즉시 노출/알림하지 않도록 is_draft 플래그 추가.
영업이 특이사항 입력 후 '생산팀에 요청'하면 is_draft=false 로 전환하며 알림 발송.
기존 데이터는 전부 정식(False).
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0870_pr_is_draft"
down_revision = "xm_v0860_packing_folder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request", sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="false"))
    op.create_index("ix_production_request_is_draft", "production_request", ["is_draft"])


def downgrade() -> None:
    op.drop_index("ix_production_request_is_draft", table_name="production_request")
    op.drop_column("production_request", "is_draft")
