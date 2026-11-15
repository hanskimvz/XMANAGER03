"""v0.62.0 연차 부여 방식(자동/수동) 직원별 설정

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-10

users.leave_grant_mode: 'AUTO'(회계연도 자동 발생, 기본) | 'MANUAL'(수동 조정으로만 부여).
MANUAL 이면 ensure_grants 가 자동 GRANT 를 만들지 않고 기존 자동발생분은 제거.
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("leave_grant_mode", sa.String(length=10), nullable=False, server_default="AUTO"),
    )


def downgrade() -> None:
    op.drop_column("users", "leave_grant_mode")
