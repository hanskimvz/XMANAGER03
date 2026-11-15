"""add_inventory_lot_tables

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2026-01-15 16:00:00.000000

로트 추적 테이블 생성 (v0.7.0):
- inventory_lot: 입고분별 재고 로트
- work_order_item_issue: 작업지시서 항목별 로트 출고 기록
- inventory.fifo_enabled 필드 추가
- inventory_transaction.lot_id, lot_number 필드 추가
- 기존 재고에 대한 초기 로트 생성
"""
from typing import Sequence, Union
from datetime import datetime
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3g4h5i6j7'
down_revision: Union[str, None] = 'd1e2f3g4h5i6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. inventory_lot 테이블 생성
    op.create_table('inventory_lot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('part_id', sa.Integer(), nullable=False, comment='부품 ID'),
        sa.Column('lot_number', sa.String(50), nullable=False, comment='로트/배치 번호'),
        sa.Column('quantity_received', sa.Numeric(15, 3), nullable=False, comment='입고 수량'),
        sa.Column('quantity_on_hand', sa.Numeric(15, 3), nullable=False, default=0, comment='현재 잔량'),
        sa.Column('quantity_issued', sa.Numeric(15, 3), nullable=True, default=0, comment='출고된 수량'),
        sa.Column('received_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='입고일시'),
        sa.Column('purchase_order_id', sa.Integer(), nullable=True, comment='발주서 ID'),
        sa.Column('supplier_id', sa.Integer(), nullable=True, comment='공급업체 ID'),
        sa.Column('warehouse_location_id', sa.Integer(), nullable=True, comment='보관위치 ID'),
        sa.Column('expiry_date', sa.Date(), nullable=True, comment='유효기간'),
        sa.Column('supplier_lot_number', sa.String(50), nullable=True, comment='공급업체 로트번호'),
        sa.Column('unit_cost', sa.Numeric(15, 2), nullable=True, comment='입고 단가'),
        sa.Column('status', sa.String(20), nullable=True, default='ACTIVE', comment='상태'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='비고'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='수정일시'),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_order.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['business_partner.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['warehouse_location_id'], ['warehouse_location.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('part_id', 'lot_number', name='uq_inventory_lot_part_lot')
    )
    op.create_index(op.f('ix_inventory_lot_id'), 'inventory_lot', ['id'], unique=False)
    op.create_index(op.f('ix_inventory_lot_part_id'), 'inventory_lot', ['part_id'], unique=False)
    op.create_index('ix_inventory_lot_part_date', 'inventory_lot', ['part_id', 'received_date'], unique=False)
    op.create_index('ix_inventory_lot_status', 'inventory_lot', ['part_id', 'status'], unique=False)

    # 2. work_order_item_issue 테이블 생성
    op.create_table('work_order_item_issue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('work_order_item_id', sa.Integer(), nullable=False, comment='작업지시서 항목 ID'),
        sa.Column('lot_id', sa.Integer(), nullable=True, comment='로트 ID'),
        sa.Column('lot_number', sa.String(50), nullable=True, comment='로트번호'),
        sa.Column('quantity', sa.Numeric(15, 3), nullable=False, comment='출고 수량'),
        sa.Column('issue_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='출고일시'),
        sa.Column('returned_quantity', sa.Numeric(15, 3), nullable=True, default=0, comment='반납 수량'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='생성일시'),
        sa.ForeignKeyConstraint(['work_order_item_id'], ['work_order_item.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lot_id'], ['inventory_lot.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_order_item_issue_id'), 'work_order_item_issue', ['id'], unique=False)
    op.create_index('ix_wo_item_issue_item', 'work_order_item_issue', ['work_order_item_id'], unique=False)
    op.create_index('ix_wo_item_issue_lot', 'work_order_item_issue', ['lot_id'], unique=False)

    # 3. inventory 테이블에 fifo_enabled 컬럼 추가
    op.add_column('inventory', sa.Column('fifo_enabled', sa.Boolean(), nullable=True, default=True, comment='선입선출 적용 여부'))

    # 4. inventory_transaction 테이블에 lot 관련 컬럼 추가
    op.add_column('inventory_transaction', sa.Column('lot_id', sa.Integer(), nullable=True, comment='로트 ID'))
    op.add_column('inventory_transaction', sa.Column('lot_number', sa.String(50), nullable=True, comment='로트번호'))
    op.create_foreign_key('fk_inv_transaction_lot', 'inventory_transaction', 'inventory_lot', ['lot_id'], ['id'], ondelete='SET NULL')

    # 5. 기존 재고에 대한 초기 로트 생성 (데이터 마이그레이션)
    # SQLite와 PostgreSQL 모두 지원하도록 raw SQL 사용
    connection = op.get_bind()

    # 현재 재고가 있는 inventory 레코드 조회
    result = connection.execute(
        sa.text("""
            SELECT i.id, i.part_id, i.quantity_on_hand, i.unit_cost, i.created_at
            FROM inventory i
            WHERE i.quantity_on_hand > 0
        """)
    )

    # 각 재고에 대해 초기 로트 생성
    for row in result:
        inv_id, part_id, qty, unit_cost, created_at = row
        lot_number = f"INIT-{part_id:06d}"

        # 로트 생성
        connection.execute(
            sa.text("""
                INSERT INTO inventory_lot
                (part_id, lot_number, quantity_received, quantity_on_hand, quantity_issued,
                 received_date, unit_cost, status, remarks)
                VALUES
                (:part_id, :lot_number, :qty, :qty, 0,
                 :received_date, :unit_cost, 'ACTIVE', '초기 재고 로트 (자동생성)')
            """),
            {
                'part_id': part_id,
                'lot_number': lot_number,
                'qty': float(qty) if qty else 0,
                'received_date': created_at or datetime.now(),
                'unit_cost': float(unit_cost) if unit_cost else None
            }
        )


def downgrade() -> None:
    # 역순으로 삭제
    # 5. 초기 로트는 자동으로 삭제됨 (CASCADE)

    # 4. inventory_transaction에서 lot 관련 컬럼 삭제
    op.drop_constraint('fk_inv_transaction_lot', 'inventory_transaction', type_='foreignkey')
    op.drop_column('inventory_transaction', 'lot_number')
    op.drop_column('inventory_transaction', 'lot_id')

    # 3. inventory에서 fifo_enabled 컬럼 삭제
    op.drop_column('inventory', 'fifo_enabled')

    # 2. work_order_item_issue 삭제
    op.drop_index('ix_wo_item_issue_lot', table_name='work_order_item_issue')
    op.drop_index('ix_wo_item_issue_item', table_name='work_order_item_issue')
    op.drop_index(op.f('ix_work_order_item_issue_id'), table_name='work_order_item_issue')
    op.drop_table('work_order_item_issue')

    # 1. inventory_lot 삭제
    op.drop_index('ix_inventory_lot_status', table_name='inventory_lot')
    op.drop_index('ix_inventory_lot_part_date', table_name='inventory_lot')
    op.drop_index(op.f('ix_inventory_lot_part_id'), table_name='inventory_lot')
    op.drop_index(op.f('ix_inventory_lot_id'), table_name='inventory_lot')
    op.drop_table('inventory_lot')
