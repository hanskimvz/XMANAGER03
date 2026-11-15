"""v0.69.0 생산요청: 총괄자 메모 + 공정 확인표 컬럼 추가

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-07-27

생산 시작 단계에 필요한 자료:
- manager_memo: 생산팀 총괄자가 생산 시작 전 작성하는 메모
- process_checks: 공정 확인표(표준 5개 항목별 일자/확인자/특이사항/조치내용) JSON
"""
from alembic import op
import sqlalchemy as sa

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request", sa.Column("manager_memo", sa.Text(), nullable=True))
    op.add_column("production_request", sa.Column("process_checks", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("production_request", "process_checks")
    op.drop_column("production_request", "manager_memo")
