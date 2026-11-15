"""v0.64.0 결재 시행자/시행전후 + 구매 구분

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-14

approval_documents:
- purchase_category: 구매 구분(일반/과제/개발) — 과제 구매 탭 필터용
- executor_id: 시행자(집행자) user id
- execution_status: 시행 상태(NULL/PENDING=시행전/DONE=시행후)
- executed_at: 시행 완료 일시
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("approval_documents", sa.Column("purchase_category", sa.String(length=10), nullable=True))
    op.add_column("approval_documents", sa.Column("executor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("approval_documents", sa.Column("execution_status", sa.String(length=10), nullable=True))
    op.add_column("approval_documents", sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_approval_documents_executor_id", "approval_documents", ["executor_id"])
    op.create_index("ix_approval_documents_purchase_category", "approval_documents", ["purchase_category"])


def downgrade() -> None:
    op.drop_index("ix_approval_documents_purchase_category", table_name="approval_documents")
    op.drop_index("ix_approval_documents_executor_id", table_name="approval_documents")
    op.drop_column("approval_documents", "executed_at")
    op.drop_column("approval_documents", "execution_status")
    op.drop_column("approval_documents", "executor_id")
    op.drop_column("approval_documents", "purchase_category")
