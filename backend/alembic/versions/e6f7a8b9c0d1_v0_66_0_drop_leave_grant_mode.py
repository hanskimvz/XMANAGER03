"""v0.66.0 연차 부여방식(AUTO/MANUAL) 기능 제거 — leave_grant_mode 컬럼 드롭

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-15

산업기능요원(입사일 기준) 체크로 특수 케이스를 처리하므로 자동/수동 부여방식 토글이
불필요 → users.leave_grant_mode 컬럼 삭제.
"""
from alembic import op
import sqlalchemy as sa

revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "leave_grant_mode")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("leave_grant_mode", sa.String(length=10), nullable=False, server_default="AUTO"),
    )
