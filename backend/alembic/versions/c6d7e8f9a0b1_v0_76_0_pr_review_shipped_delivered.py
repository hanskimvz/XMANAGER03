"""v0.76.0 생산요청 검토사유/출고·발송 시각

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-07-29

- production_request.review_note (검토 필요 사유, 생산팀→영업 확인요청)
- production_request.shipped_at (생산 출고 SHIPPED 시각)
- production_request.delivered_at (발송 완료 DELIVERED 시각 — 영업 처리)
"""
from alembic import op
import sqlalchemy as sa

revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column("production_request", sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("production_request", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("production_request", "delivered_at")
    op.drop_column("production_request", "shipped_at")
    op.drop_column("production_request", "review_note")
