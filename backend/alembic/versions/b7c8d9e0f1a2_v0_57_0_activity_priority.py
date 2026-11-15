"""v0.57.0 영업활동 우선순위(긴급/중요) 2축 플래그

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-06

영업 대응 현황에서 진행중 건들의 긴급/중요를 한눈에 보기 위해 상태/문의유형과
독립된 우선순위 2축(is_urgent=시급성, is_important=전략가치)을 추가한다.
상태값에 DROPPED(무산)도 함께 사용(값만 추가, 스키마 변경 없음).
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_activity", sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("sales_activity", sa.Column("is_important", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("sales_activity", "is_important")
    op.drop_column("sales_activity", "is_urgent")
