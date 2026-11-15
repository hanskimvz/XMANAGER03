"""v0.98.0 발주서 — 기안 파생 표시(source_approval_id) + 발송(sent_at/sent_by)

Revision ID: xm_v0980_po_source_sent
Revises: xm_v0970_bom_changelog
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0980_po_source_sent"
down_revision = "xm_v0970_bom_changelog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_order", sa.Column("source_approval_id", sa.Integer(), nullable=True))
    op.add_column("purchase_order", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("purchase_order", sa.Column("sent_by", sa.Integer(), nullable=True))
    op.create_index("ix_purchase_order_source_approval", "purchase_order", ["source_approval_id"])


def downgrade() -> None:
    op.drop_index("ix_purchase_order_source_approval", table_name="purchase_order")
    op.drop_column("purchase_order", "sent_by")
    op.drop_column("purchase_order", "sent_at")
    op.drop_column("purchase_order", "source_approval_id")
