"""v0.50.0 announcements (회사 공지사항: 공지/첨부/읽음영수)

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-06-26

3개 테이블:
- announcements: 공지 1건(제목/본문HTML/핀/대상부서 JSONB/소프트삭제).
- announcement_attachments: 첨부(다중, FK CASCADE).
- announcement_reads: 읽음 영수((공지,사용자) UNIQUE, FK CASCADE).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "y8z9a0b1c2d3"
down_revision = "x7y8z9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("target_departments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_announcements_is_pinned", "announcements", ["is_pinned"])
    op.create_index("ix_announcements_published_at", "announcements", ["published_at"])
    op.create_index("ix_announcements_is_active", "announcements", ["is_active"])
    op.create_index("ix_announcements_active_pinned_pub", "announcements",
                    ["is_active", "is_pinned", "published_at"])
    op.create_index("ix_announcements_target_gin", "announcements",
                    ["target_departments"], postgresql_using="gin")

    op.create_table(
        "announcement_attachments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("announcement_id", sa.Integer,
                  sa.ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(length=300), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(length=150), nullable=True),
        sa.Column("uploaded_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_announcement_attachments_announcement_id",
                    "announcement_attachments", ["announcement_id"])

    op.create_table(
        "announcement_reads",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("announcement_id", sa.Integer,
                  sa.ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_read_user"),
    )
    op.create_index("ix_announcement_reads_announcement_id",
                    "announcement_reads", ["announcement_id"])
    op.create_index("ix_announcement_reads_user_id", "announcement_reads", ["user_id"])


def downgrade() -> None:
    op.drop_table("announcement_reads")
    op.drop_table("announcement_attachments")
    op.drop_index("ix_announcements_target_gin", table_name="announcements")
    op.drop_index("ix_announcements_active_pinned_pub", table_name="announcements")
    op.drop_index("ix_announcements_is_active", table_name="announcements")
    op.drop_index("ix_announcements_published_at", table_name="announcements")
    op.drop_index("ix_announcements_is_pinned", table_name="announcements")
    op.drop_table("announcements")
