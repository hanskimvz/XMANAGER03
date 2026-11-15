"""add source_request_modified to work_order v021

Revision ID: l1m2n3o4p5q6
Revises: k1l2m3n4o5p6
Create Date: 2026-01-26

v0.21.0: 연결된 생산 요청서 수정 알림 플래그 추가
- work_order.source_request_modified: 생산 요청서가 수정되면 True로 설정
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'l1m2n3o4p5q6'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade():
    # work_order 테이블에 source_request_modified 컬럼 추가
    op.add_column('work_order', sa.Column('source_request_modified', sa.Boolean(), nullable=True, default=False, comment='원본 요청서 수정됨'))

    # 기존 데이터는 False로 설정
    op.execute("UPDATE work_order SET source_request_modified = FALSE WHERE source_request_modified IS NULL")


def downgrade():
    op.drop_column('work_order', 'source_request_modified')
