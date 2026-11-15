"""v0.51.0 leave approver presets (휴가 전용 인원별 결재선/참조자)

Revision ID: z9a0b1c2d3e4
Revises: y8z9a0b1c2d3
Create Date: 2026-06-29

users 에 휴가(LEAVE) 기안 시 자동 채울 결재선/참조자 프리셋(JSONB 배열) 추가.
- leave_approver_ids: 순서대로의 결재자 user id 배열
- leave_reference_ids: 참조자 user id 배열
미설정(NULL)이면 기존 기본 결재자(approver_id/approver2_id)로 폴백.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "z9a0b1c2d3e4"
down_revision = "y8z9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("leave_approver_ids",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("users", sa.Column("leave_reference_ids",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "leave_reference_ids")
    op.drop_column("users", "leave_approver_ids")
