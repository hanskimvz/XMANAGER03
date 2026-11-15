"""조직도 필드 (departments 확장)

경영관리 > 조직관리의 조직도를 위해 departments 에 컬럼 추가:
- parent_id(상위 조직, 자기참조) / org_type(조직 유형) / manager_user_id(책임자)
- name_en(영문명) / description(설명)

기존 행은 모두 최상위(parent_id NULL) · 유형 '팀'(TEAM)으로 남는다.

Revision ID: xm_v1040_department_org
Revises: xm_v1030_schedules
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v1040_department_org"
down_revision = "xm_v1030_schedules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("departments", sa.Column("name_en", sa.String(length=100), nullable=True))
    op.add_column("departments", sa.Column(
        "org_type", sa.String(length=20), nullable=False, server_default="TEAM"))
    op.add_column("departments", sa.Column("parent_id", sa.Integer, nullable=True))
    op.add_column("departments", sa.Column("manager_user_id", sa.Integer, nullable=True))
    op.add_column("departments", sa.Column("description", sa.Text, nullable=True))
    op.create_foreign_key("fk_departments_parent_id", "departments", "departments",
                          ["parent_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_departments_manager_user_id", "departments", "users",
                          ["manager_user_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"])
    op.create_check_constraint(
        "ck_departments_org_type", "departments",
        "org_type IN ('EXECUTIVE', 'DIVISION', 'DEPARTMENT', 'TEAM')")


def downgrade() -> None:
    op.drop_constraint("ck_departments_org_type", "departments", type_="check")
    op.drop_index("ix_departments_parent_id", table_name="departments")
    op.drop_constraint("fk_departments_manager_user_id", "departments", type_="foreignkey")
    op.drop_constraint("fk_departments_parent_id", "departments", type_="foreignkey")
    op.drop_column("departments", "description")
    op.drop_column("departments", "manager_user_id")
    op.drop_column("departments", "parent_id")
    op.drop_column("departments", "org_type")
    op.drop_column("departments", "name_en")
