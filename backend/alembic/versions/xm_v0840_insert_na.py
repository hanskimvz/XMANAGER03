"""v0.84.0 인서트 해당없음(N/A) 플래그

Revision ID: xm_v0840_insert_na
Revises: xm_v0830_pr_custom_item
Create Date: 2026-08-10

인서트 공정이 없는 생산요청을 구분하기 위한 insert_not_applicable 플래그 추가.
(미출고 / 출고됨 / 인서트 없음 3상태화)
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0840_insert_na"
down_revision = "xm_v0830_pr_custom_item"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_request",
        sa.Column("insert_not_applicable", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("production_request", "insert_not_applicable")
