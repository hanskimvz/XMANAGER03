"""Add attachment_files column to production_request table

Revision ID: n1o2p3q4r5s6
Revises: m1n2o3p4q5r6
Create Date: 2026-01-29

v0.22.0: 생산 요청서 첨부파일 지원
- production_request.attachment_files (JSON) 컬럼 추가
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = 'n1o2p3q4r5s6'
down_revision = 'm1n2o3p4q5r6'
branch_labels = None
depends_on = None


def upgrade():
    # production_request 테이블에 attachment_files JSON 컬럼 추가
    op.add_column('production_request',
                  sa.Column('attachment_files', JSON, nullable=True, comment='첨부파일 목록 (JSON)'))


def downgrade():
    op.drop_column('production_request', 'attachment_files')
