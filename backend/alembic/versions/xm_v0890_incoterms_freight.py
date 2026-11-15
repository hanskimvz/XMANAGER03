"""v0.89.0 인코텀즈 + 박스당 운임(분할선적)

Revision ID: xm_v0890_incoterms_freight
Revises: xm_v0880_pr_item_ci_qty
Create Date: 2026-08-14

CPT 등 운임부담 인코텀즈에서 박스당 운임을 잡고, 박스별 CI 발행 시 배송비로 가산.
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0890_incoterms_freight"
down_revision = "xm_v0880_pr_item_ci_qty"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_document", sa.Column("incoterms", sa.String(length=10), nullable=True))
    op.add_column("sales_document", sa.Column("freight_per_box", sa.Numeric(15, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_document", "freight_per_box")
    op.drop_column("sales_document", "incoterms")
