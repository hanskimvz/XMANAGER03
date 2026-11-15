"""create partner_note table

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'x4y5z6a7b8c9'
down_revision: Union[str, None] = 'w3x4y5z6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'partner_note',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('partner_id', sa.Integer(), sa.ForeignKey('business_partner.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('note_type', sa.String(20), nullable=False, server_default='GENERAL', comment='메모 유형'),
        sa.Column('content', sa.Text(), nullable=False, comment='메모 내용'),
        sa.Column('is_pinned', sa.Boolean(), server_default='false', comment='상단 고정'),
        sa.Column('created_by', sa.String(100), nullable=True, comment='작성자'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('partner_note')
