"""v0.74.0 생산요청 인서트/생산 출고 완료 시각 컬럼

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-29

인서트출고/생산출고 체크박스에 완료 시각을 기록해 영업 현황 표시 + 출고일 조회에 활용.
"""
from alembic import op
import sqlalchemy as sa

revision = "a4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request", sa.Column("insert_shipped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("production_request", sa.Column("production_shipped_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("production_request", "production_shipped_at")
    op.drop_column("production_request", "insert_shipped_at")
