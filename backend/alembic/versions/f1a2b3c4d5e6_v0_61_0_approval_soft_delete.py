"""v0.61.0 결재 소프트 삭제

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-07-09

전자결재 문서 소프트 삭제(관리자 전용). 목록/상세/휴가집계 제외, 감사용 보존.
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("approval_documents", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("approval_documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("approval_documents", sa.Column("deleted_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("ix_approval_documents_is_deleted", "approval_documents", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_approval_documents_is_deleted", table_name="approval_documents")
    op.drop_column("approval_documents", "deleted_by")
    op.drop_column("approval_documents", "deleted_at")
    op.drop_column("approval_documents", "is_deleted")
