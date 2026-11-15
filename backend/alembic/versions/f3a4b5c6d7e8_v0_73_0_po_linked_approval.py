"""v0.73.0 발주서→구매기안서 역방향 링크 컬럼

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-27

발주서 기준으로 구매기안서(전자결재)를 자동 생성할 때, 중복 생성을 막고
역방향 추적을 위해 purchase_order.linked_approval_id 를 둔다.
"""
from alembic import op
import sqlalchemy as sa

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_order", sa.Column("linked_approval_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_order", "linked_approval_id")
