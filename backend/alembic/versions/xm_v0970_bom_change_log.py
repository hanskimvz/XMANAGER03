"""v0.97.0 BOM 개편 P2 — 변경 감사 로그(bom_change_log)

Revision ID: xm_v0970_bom_changelog
Revises: xm_v0960_bom_p1
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0970_bom_changelog"
down_revision = "xm_v0960_bom_p1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bom_change_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("parent_part_id", sa.Integer(), nullable=True),
        sa.Column("child_part_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bom_change_log_parent", "bom_change_log", ["parent_part_id"])
    op.create_index("ix_bom_change_log_child", "bom_change_log", ["child_part_id"])
    op.create_index("ix_bom_change_log_created", "bom_change_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("bom_change_log")
