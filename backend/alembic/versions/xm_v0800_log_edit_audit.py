"""v0.80.0 영업활동 코멘트 수정 기록

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-07-29

sales_activity_log에 수정 기록(edited_by / edited_at) 추가 — 코멘트 수정 감사용.
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0800_log_edit_audit"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_activity_log", sa.Column("edited_by", sa.String(length=100), nullable=True))
    op.add_column("sales_activity_log", sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_activity_log", "edited_at")
    op.drop_column("sales_activity_log", "edited_by")
