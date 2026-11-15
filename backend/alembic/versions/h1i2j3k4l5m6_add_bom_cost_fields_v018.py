"""add_bom_cost_fields_v018

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-01-16 14:00:00.000000

BOM 기반 원가 계산 필드 추가 (v0.18.0)
- Parts 테이블에 BOM 원가 계산 필드 추가
  - cost_type: 원가유형 (MANUAL/BOM/PROCESS)
  - material_cost: 재료비
  - labor_cost: 가공비/노무비
  - overhead_cost: 경비
  - calculated_cost: 계산된 원가 (캐시)
  - cost_calculated_at: 원가 계산일시
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Parts 테이블에 BOM 원가 계산 필드 추가

    # 원가 유형
    op.add_column('parts', sa.Column('cost_type', sa.String(20), nullable=True, server_default='MANUAL', comment='원가유형 (MANUAL/BOM/PROCESS)'))

    # 재료비 (Material Cost)
    op.add_column('parts', sa.Column('material_cost', sa.Numeric(15, 4), nullable=True, server_default='0', comment='재료비'))
    op.add_column('parts', sa.Column('material_cost_currency', sa.String(10), nullable=True, server_default='KRW', comment='재료비 통화'))

    # 가공비/노무비 (Labor Cost)
    op.add_column('parts', sa.Column('labor_cost', sa.Numeric(15, 4), nullable=True, server_default='0', comment='가공비/노무비'))
    op.add_column('parts', sa.Column('labor_cost_currency', sa.String(10), nullable=True, server_default='KRW', comment='가공비 통화'))

    # 경비 (Overhead Cost)
    op.add_column('parts', sa.Column('overhead_cost', sa.Numeric(15, 4), nullable=True, server_default='0', comment='경비'))
    op.add_column('parts', sa.Column('overhead_cost_currency', sa.String(10), nullable=True, server_default='KRW', comment='경비 통화'))

    # 계산된 원가 (Calculated Cost) - BOM 합산 결과 캐시
    op.add_column('parts', sa.Column('calculated_cost', sa.Numeric(15, 4), nullable=True, server_default='0', comment='계산된 원가 (캐시)'))
    op.add_column('parts', sa.Column('calculated_cost_currency', sa.String(10), nullable=True, server_default='KRW', comment='계산된 원가 통화'))
    op.add_column('parts', sa.Column('cost_calculated_at', sa.DateTime(timezone=True), nullable=True, comment='원가 계산일시'))


def downgrade() -> None:
    # Parts 테이블에서 BOM 원가 계산 필드 삭제
    op.drop_column('parts', 'cost_calculated_at')
    op.drop_column('parts', 'calculated_cost_currency')
    op.drop_column('parts', 'calculated_cost')
    op.drop_column('parts', 'overhead_cost_currency')
    op.drop_column('parts', 'overhead_cost')
    op.drop_column('parts', 'labor_cost_currency')
    op.drop_column('parts', 'labor_cost')
    op.drop_column('parts', 'material_cost_currency')
    op.drop_column('parts', 'material_cost')
    op.drop_column('parts', 'cost_type')
