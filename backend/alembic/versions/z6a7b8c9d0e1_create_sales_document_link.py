"""create sales_document_link table for N:M

Revision ID: z6a7b8c9d0e1
Revises: y5z6a7b8c9d0
Create Date: 2026-04-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'z6a7b8c9d0e1'
down_revision: Union[str, None] = 'y5z6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sales_document_link',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('sales_document.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_id', sa.Integer(), sa.ForeignKey('sales_document.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # 기존 source_document_id 데이터를 link 테이블로 이관
    op.execute("""
        INSERT INTO sales_document_link (source_id, target_id)
        SELECT source_document_id, id
        FROM sales_document
        WHERE source_document_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_table('sales_document_link')
