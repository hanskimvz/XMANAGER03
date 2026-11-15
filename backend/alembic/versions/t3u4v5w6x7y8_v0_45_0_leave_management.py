"""v0.45.0 연차 관리 — users.hire_date/resign_date + leave_ledger

- users: hire_date(DATE null), resign_date(DATE null) 추가 (가산적·nullable → 기존 영향 0)
- leave_ledger: 연차 거래 원장(발생/사용/수당지급/조정)

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa


revision = "t3u4v5w6x7y8"
down_revision = "s2t3u4v5w6x7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("hire_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("resign_date", sa.Date(), nullable=True))

    op.create_table(
        "leave_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="MANUAL"),
        sa.Column("source_doc_id", sa.Integer(), sa.ForeignKey("approval_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memo", sa.String(length=300), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_leave_ledger_id", "leave_ledger", ["id"])
    op.create_index("ix_leave_ledger_user_id", "leave_ledger", ["user_id"])
    op.create_index("ix_leave_ledger_fiscal_year", "leave_ledger", ["fiscal_year"])
    op.create_index("ix_leave_ledger_user_fy", "leave_ledger", ["user_id", "fiscal_year"])
    op.create_index("ix_leave_ledger_user_type", "leave_ledger", ["user_id", "entry_type"])


def downgrade() -> None:
    op.drop_index("ix_leave_ledger_user_type", table_name="leave_ledger")
    op.drop_index("ix_leave_ledger_user_fy", table_name="leave_ledger")
    op.drop_index("ix_leave_ledger_fiscal_year", table_name="leave_ledger")
    op.drop_index("ix_leave_ledger_user_id", table_name="leave_ledger")
    op.drop_index("ix_leave_ledger_id", table_name="leave_ledger")
    op.drop_table("leave_ledger")
    op.drop_column("users", "resign_date")
    op.drop_column("users", "hire_date")
