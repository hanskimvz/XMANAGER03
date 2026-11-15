"""일정 등록 (schedules)

경영관리 > 일정등록에서 직접 등록하는 일정(행사/휴가/외근/출장).
게시판 > 일정 캘린더가 발주서·작업지시서·전자결재와 함께 읽어 표시한다.

Revision ID: xm_v1030_schedules
Revises: xm_v1020_free_board
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v1030_schedules"
down_revision = "xm_v1020_free_board"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("schedule_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("target_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("memo", sa.Text, nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="MANUAL"),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "schedule_type IN ('EVENT', 'LEAVE', 'FIELDWORK', 'TRIP')",
            name="ck_schedules_type",
        ),
        sa.CheckConstraint("end_date >= start_date", name="ck_schedules_date_range"),
    )
    op.create_index("ix_schedules_id", "schedules", ["id"])
    op.create_index("ix_schedules_schedule_type", "schedules", ["schedule_type"])
    op.create_index("ix_schedules_target_user_id", "schedules", ["target_user_id"])
    op.create_index("ix_schedules_created_by", "schedules", ["created_by"])
    op.create_index("ix_schedules_active_dates", "schedules",
                    ["is_active", "start_date", "end_date"])


def downgrade() -> None:
    op.drop_table("schedules")
