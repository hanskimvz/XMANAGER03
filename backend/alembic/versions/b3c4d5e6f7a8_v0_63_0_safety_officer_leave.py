"""v0.63.0 산업안전요원(입사일 기준 연차) 플래그

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-14

users.is_safety_officer: 산업안전요원 여부. True면 연차 자동발생을 회계연도가 아닌
'입사일 기준(근로기준법)'으로 산정.
"""
from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_safety_officer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "is_safety_officer")
