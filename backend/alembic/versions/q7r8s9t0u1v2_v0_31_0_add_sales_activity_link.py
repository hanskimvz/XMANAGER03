"""v0.31.0 add sales_activity_id to sales_document

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-04-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'q7r8s9t0u1v2'
down_revision: str = 'p6q7r8s9t0u1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sales_document',
        sa.Column('sales_activity_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'sales_document_sales_activity_id_fkey',
        'sales_document', 'sales_activity',
        ['sales_activity_id'], ['id'],
    )
    op.create_index(
        'ix_sales_document_sales_activity_id',
        'sales_document', ['sales_activity_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_sales_document_sales_activity_id', table_name='sales_document')
    op.drop_constraint('sales_document_sales_activity_id_fkey', 'sales_document', type_='foreignkey')
    op.drop_column('sales_document', 'sales_activity_id')
