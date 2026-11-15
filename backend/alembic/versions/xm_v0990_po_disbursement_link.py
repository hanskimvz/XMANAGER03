"""v0.99.0 발주서 대금지급을 지출결의(집행)에 연동 — disbursement_id

Revision ID: xm_v0990_po_disb
Revises: xm_v0980_po_source_sent
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0990_po_disb"
down_revision = "xm_v0980_po_source_sent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_order", sa.Column("disbursement_id", sa.Integer(), nullable=True))
    op.create_index("ix_purchase_order_disbursement", "purchase_order", ["disbursement_id"])


def downgrade() -> None:
    op.drop_index("ix_purchase_order_disbursement", table_name="purchase_order")
    op.drop_column("purchase_order", "disbursement_id")
