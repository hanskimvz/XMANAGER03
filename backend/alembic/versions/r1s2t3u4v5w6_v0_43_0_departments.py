"""v0.43.0 부서 마스터 테이블(departments)

- departments: id, code(unique), name, is_active, sort_order, created_at
- 기존 users.department(코드 문자열)이 참조. 시드(영업팀/생산팀/경영지원팀)는 부팅 시 ensure_default_departments.

Revision ID: r1s2t3u4v5w6
Revises: q0r1s2t3u4v5
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa


revision = "r1s2t3u4v5w6"
down_revision = "q0r1s2t3u4v5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_departments_id", "departments", ["id"])
    op.create_unique_constraint("uq_departments_code", "departments", ["code"])
    op.create_index("ix_departments_code", "departments", ["code"])


def downgrade() -> None:
    op.drop_index("ix_departments_code", table_name="departments")
    op.drop_constraint("uq_departments_code", "departments", type_="unique")
    op.drop_index("ix_departments_id", table_name="departments")
    op.drop_table("departments")
