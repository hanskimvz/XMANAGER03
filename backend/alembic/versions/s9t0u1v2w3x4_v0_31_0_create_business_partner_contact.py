"""v0.31.0 create business_partner_contact table

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-04-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 's9t0u1v2w3x4'
down_revision: str = 'r8s9t0u1v2w3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'business_partner_contact',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('partner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment="담당자명"),
        sa.Column('position', sa.String(50), nullable=True, comment="직책"),
        sa.Column('role', sa.String(20), nullable=True, comment="역할 (PURCHASING/TECHNICAL/SALES/GENERAL)"),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('tel_office', sa.String(50), nullable=True, comment="사무실 전화"),
        sa.Column('tel_mobile', sa.String(50), nullable=True, comment="휴대폰"),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false', comment="기본 담당자 여부"),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['business_partner.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_business_partner_contact_partner_id', 'business_partner_contact', ['partner_id'])

    # 기존 manager_* 데이터를 contact 테이블로 이전 (이름이 있는 경우만)
    op.execute("""
        INSERT INTO business_partner_contact
            (partner_id, name, position, email, tel_office, tel_mobile, is_primary, sort_order, created_at)
        SELECT
            id, manager_name, manager_position, manager_email, manager_tel, manager_mobile,
            true, 0, COALESCE(created_at, NOW())
        FROM business_partner
        WHERE manager_name IS NOT NULL AND manager_name != ''
    """)


def downgrade() -> None:
    op.drop_index('ix_business_partner_contact_partner_id', table_name='business_partner_contact')
    op.drop_table('business_partner_contact')
