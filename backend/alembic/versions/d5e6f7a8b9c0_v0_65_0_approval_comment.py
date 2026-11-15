"""v0.65.0 결재 의견(댓글) 테이블

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-15

approval_comment: 결재 문서 열람자가 남기는 논의용 댓글.
- document_id: 결재 문서(FK, CASCADE)
- user_id: 작성자
- content: 내용
- created_at: 작성 일시
"""
from alembic import op
import sqlalchemy as sa

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_comment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("approval_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_comment_document_id", "approval_comment", ["document_id"])
    op.create_index("ix_approval_comment_user_id", "approval_comment", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_approval_comment_user_id", table_name="approval_comment")
    op.drop_index("ix_approval_comment_document_id", table_name="approval_comment")
    op.drop_table("approval_comment")
