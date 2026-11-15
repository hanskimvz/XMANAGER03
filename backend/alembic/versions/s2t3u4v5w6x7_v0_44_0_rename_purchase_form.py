"""v0.44.0 구매 신청서 → 구매기안서 이름 변경

approval_forms.name 만 변경(code=PURCHASE 불변). 기존 문서/번호 영향 없음.

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa


revision = "s2t3u4v5w6x7"
down_revision = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE approval_forms SET name = '구매기안서' WHERE code = 'PURCHASE'")


def downgrade() -> None:
    op.execute("UPDATE approval_forms SET name = '구매 신청서' WHERE code = 'PURCHASE'")
