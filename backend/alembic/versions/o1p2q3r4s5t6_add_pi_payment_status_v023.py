"""Add pi_number and payment_status to production_request v0.23.0

Revision ID: o1p2q3r4s5t6
Revises: n1o2p3q4r5s6
Create Date: 2026-02-03

v0.23.0: 생산 요청서 PI/입금현황 필드 추가
- pi_number: PI 번호 (Proforma Invoice)
- payment_status: 입금현황 (UNPAID/PARTIAL/PAID)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'o1p2q3r4s5t6'
down_revision = 'n1o2p3q4r5s6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('production_request', sa.Column('pi_number', sa.String(50), nullable=True, comment='PI 번호 (Proforma Invoice)'))
    op.add_column('production_request', sa.Column('payment_status', sa.String(20), nullable=True, server_default='UNPAID', comment='입금현황'))


def downgrade():
    op.drop_column('production_request', 'payment_status')
    op.drop_column('production_request', 'pi_number')
