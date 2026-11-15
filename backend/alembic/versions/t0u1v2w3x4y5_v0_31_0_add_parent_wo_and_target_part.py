"""v0.31.0 add parent_wo_id and target_part_id to work_order

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-04-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 't0u1v2w3x4y5'
down_revision: str = 's9t0u1v2w3x4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'work_order',
        sa.Column('parent_wo_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'work_order',
        sa.Column('target_part_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'work_order_parent_wo_id_fkey',
        'work_order', 'work_order',
        ['parent_wo_id'], ['id'],
    )
    op.create_foreign_key(
        'work_order_target_part_id_fkey',
        'work_order', 'parts',
        ['target_part_id'], ['id'],
    )
    op.create_index(
        'ix_work_order_parent_wo_id',
        'work_order', ['parent_wo_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_work_order_parent_wo_id', table_name='work_order')
    op.drop_constraint('work_order_target_part_id_fkey', 'work_order', type_='foreignkey')
    op.drop_constraint('work_order_parent_wo_id_fkey', 'work_order', type_='foreignkey')
    op.drop_column('work_order', 'target_part_id')
    op.drop_column('work_order', 'parent_wo_id')
