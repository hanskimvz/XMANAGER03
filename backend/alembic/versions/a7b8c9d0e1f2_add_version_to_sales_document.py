"""add version fields to sales_document

Revision ID: a7b8c9d0e1f2
Revises: z6a7b8c9d0e1
Create Date: 2026-04-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'z6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sales_document', sa.Column('version', sa.Integer(), nullable=False, server_default='1', comment='버전 번호'))
    op.add_column('sales_document', sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='true', comment='최신 버전 여부'))
    op.add_column('sales_document', sa.Column('version_group', sa.String(50), nullable=True, comment='버전 그룹'))
    op.create_index('ix_sales_document_is_latest', 'sales_document', ['is_latest'])
    op.create_index('ix_sales_document_version_group', 'sales_document', ['version_group'])
    # 기존 문서의 version_group을 document_number로 초기화
    op.execute("UPDATE sales_document SET version_group = document_number")


def downgrade() -> None:
    op.drop_index('ix_sales_document_version_group')
    op.drop_index('ix_sales_document_is_latest')
    op.drop_column('sales_document', 'version_group')
    op.drop_column('sales_document', 'is_latest')
    op.drop_column('sales_document', 'version')
