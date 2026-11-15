"""v0.70.0 생산요청 품목 단위(uom) 컬럼 추가

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-07-27

생산요청 품목이 단위를 갖지 않아 목록/출력에서 'EA'로 하드코딩되던 문제(⑨).
PI 품목(uom)에서 단위를 승계해 표시 정확도 확보.
"""
from alembic import op
import sqlalchemy as sa

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request_item", sa.Column("uom", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("production_request_item", "uom")
