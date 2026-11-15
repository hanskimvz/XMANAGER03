"""create_inventory_tables

Revision ID: c3d4e5f6g7h8
Revises: a1b2c3d4e5f6
Create Date: 2026-01-15 10:00:00.000000

재고관리 테이블 생성:
- warehouse_location: 보관위치
- inventory: 재고 현황
- inventory_transaction: 재고 거래 기록
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 보관위치 테이블 생성
    op.create_table('warehouse_location',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, comment='위치코드'),
        sa.Column('name', sa.String(100), nullable=False, comment='위치명'),
        sa.Column('warehouse_name', sa.String(100), nullable=True, comment='창고명'),
        sa.Column('zone', sa.String(50), nullable=True, comment='구역'),
        sa.Column('description', sa.Text(), nullable=True, comment='설명'),
        sa.Column('capacity', sa.Numeric(15, 2), nullable=True, comment='용량'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True, comment='사용여부'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='수정일시'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_warehouse_location_id'), 'warehouse_location', ['id'], unique=False)
    op.create_index(op.f('ix_warehouse_location_code'), 'warehouse_location', ['code'], unique=True)

    # 2. 재고 현황 테이블 생성
    op.create_table('inventory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('part_id', sa.Integer(), nullable=False, comment='부품 ID'),
        sa.Column('quantity_on_hand', sa.Numeric(15, 3), nullable=False, default=0, comment='현재고'),
        sa.Column('quantity_reserved', sa.Numeric(15, 3), nullable=True, default=0, comment='예약수량'),
        sa.Column('quantity_available', sa.Numeric(15, 3), nullable=True, default=0, comment='가용수량'),
        sa.Column('reorder_point', sa.Numeric(15, 3), nullable=True, comment='재주문점'),
        sa.Column('reorder_qty', sa.Numeric(15, 3), nullable=True, comment='재주문량'),
        sa.Column('warehouse_location_id', sa.Integer(), nullable=True, comment='보관위치 ID'),
        sa.Column('unit_cost', sa.Numeric(15, 2), nullable=True, comment='단가'),
        sa.Column('status', sa.String(20), nullable=True, default='OUT_OF_STOCK', comment='상태'),
        sa.Column('last_count_date', sa.DateTime(timezone=True), nullable=True, comment='마지막 실사일'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='비고'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True, comment='사용여부'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='생성자 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='생성일시'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='수정자 ID'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='수정일시'),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['warehouse_location_id'], ['warehouse_location.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_id'), 'inventory', ['id'], unique=False)
    op.create_index(op.f('ix_inventory_part_id'), 'inventory', ['part_id'], unique=False)
    op.create_index(op.f('ix_inventory_status'), 'inventory', ['status'], unique=False)
    op.create_index('ix_inventory_part_location', 'inventory', ['part_id', 'warehouse_location_id'], unique=True)

    # 3. 재고 거래 기록 테이블 생성
    op.create_table('inventory_transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inventory_id', sa.Integer(), nullable=True, comment='재고 ID'),
        sa.Column('part_id', sa.Integer(), nullable=False, comment='부품 ID'),
        sa.Column('transaction_type', sa.String(20), nullable=False, comment='거래유형'),
        sa.Column('quantity', sa.Numeric(15, 3), nullable=False, comment='변동수량'),
        sa.Column('quantity_before', sa.Numeric(15, 3), nullable=True, comment='변동전 수량'),
        sa.Column('quantity_after', sa.Numeric(15, 3), nullable=True, comment='변동후 수량'),
        sa.Column('reference_type', sa.String(50), nullable=True, comment='참조유형'),
        sa.Column('reference_id', sa.String(50), nullable=True, comment='참조문서번호'),
        sa.Column('reason', sa.Text(), nullable=True, comment='사유'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='비고'),
        sa.Column('transaction_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='거래일시'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='생성자 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='생성일시'),
        sa.ForeignKeyConstraint(['inventory_id'], ['inventory.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_transaction_id'), 'inventory_transaction', ['id'], unique=False)
    op.create_index(op.f('ix_inventory_transaction_part_id'), 'inventory_transaction', ['part_id'], unique=False)
    op.create_index(op.f('ix_inventory_transaction_type'), 'inventory_transaction', ['transaction_type'], unique=False)
    op.create_index(op.f('ix_inventory_transaction_date'), 'inventory_transaction', ['transaction_date'], unique=False)


def downgrade() -> None:
    # 역순으로 삭제
    op.drop_index(op.f('ix_inventory_transaction_date'), table_name='inventory_transaction')
    op.drop_index(op.f('ix_inventory_transaction_type'), table_name='inventory_transaction')
    op.drop_index(op.f('ix_inventory_transaction_part_id'), table_name='inventory_transaction')
    op.drop_index(op.f('ix_inventory_transaction_id'), table_name='inventory_transaction')
    op.drop_table('inventory_transaction')

    op.drop_index('ix_inventory_part_location', table_name='inventory')
    op.drop_index(op.f('ix_inventory_status'), table_name='inventory')
    op.drop_index(op.f('ix_inventory_part_id'), table_name='inventory')
    op.drop_index(op.f('ix_inventory_id'), table_name='inventory')
    op.drop_table('inventory')

    op.drop_index(op.f('ix_warehouse_location_code'), table_name='warehouse_location')
    op.drop_index(op.f('ix_warehouse_location_id'), table_name='warehouse_location')
    op.drop_table('warehouse_location')
