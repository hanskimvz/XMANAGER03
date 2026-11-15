"""v0.42.0 디폴트 결재자 2번째(approver2_id) 추가

- users.approver2_id (self FK, nullable) — 기안 시 2차로 자동 채울 디폴트 결재자
- 기존 approver_id(1차)는 그대로. 둘 다 nullable → 데이터 영향 없음.

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa


revision = "q0r1s2t3u4v5"
down_revision = "p9q0r1s2t3u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "approver2_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
            comment="디폴트 결재자 2차(기안 시 2번째로 자동 채움)",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "approver2_id")
