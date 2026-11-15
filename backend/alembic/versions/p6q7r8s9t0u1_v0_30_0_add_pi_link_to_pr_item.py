"""v0.30.0 add pi_document_id and pi_item_id to production_request_item

Revision ID: p6q7r8s9t0u1
Revises: j0k1l2m3n4o5
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p6q7r8s9t0u1'
down_revision: str = 'j0k1l2m3n4o5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'production_request_item',
        sa.Column('pi_document_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'production_request_item',
        sa.Column('pi_item_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'production_request_item_pi_document_id_fkey',
        'production_request_item', 'sales_document',
        ['pi_document_id'], ['id'],
    )
    op.create_foreign_key(
        'production_request_item_pi_item_id_fkey',
        'production_request_item', 'sales_document_item',
        ['pi_item_id'], ['id'],
    )
    op.create_index(
        'ix_production_request_item_pi_document_id',
        'production_request_item', ['pi_document_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_production_request_item_pi_document_id', table_name='production_request_item')
    op.drop_constraint('production_request_item_pi_item_id_fkey', 'production_request_item', type_='foreignkey')
    op.drop_constraint('production_request_item_pi_document_id_fkey', 'production_request_item', type_='foreignkey')
    op.drop_column('production_request_item', 'pi_item_id')
    op.drop_column('production_request_item', 'pi_document_id')
