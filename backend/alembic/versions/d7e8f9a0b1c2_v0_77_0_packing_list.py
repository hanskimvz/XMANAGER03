"""v0.77.0 출고 packing list

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-07-29

- production_request.packing_list (생산 출고 시 박스별 포장 명세)
- sales_document.packing_list (CI가 생산 packing list를 승계)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d7e8f9a0b1c2"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request", sa.Column("packing_list", sa.JSON(), nullable=True))
    op.add_column("sales_document", sa.Column("packing_list", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_document", "packing_list")
    op.drop_column("production_request", "packing_list")
