"""create sales_document_pdf table for PDF storage history

Revision ID: d0e1f2g3h4i5
Revises: c9d0e1f2g3h4
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'd0e1f2g3h4i5'
down_revision: Union[str, None] = 'c9d0e1f2g3h4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sales_document_pdf',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('sales_document.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('document_type', sa.String(length=20), nullable=False),
        sa.Column('document_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('first_generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_downloaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_generated_by', sa.String(length=100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            'document_id', 'document_version', 'language',
            name='uq_sales_document_pdf_doc_version_lang',
        ),
    )


def downgrade() -> None:
    op.drop_table('sales_document_pdf')
