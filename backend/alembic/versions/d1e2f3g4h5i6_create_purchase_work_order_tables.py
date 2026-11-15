"""create_purchase_work_order_tables

Revision ID: d1e2f3g4h5i6
Revises: c3d4e5f6g7h8
Create Date: 2026-01-15 14:00:00.000000

입출고 관리 테이블 생성 (v0.6.0):
- purchase_order: 발주서
- purchase_order_item: 발주서 항목
- work_order: 작업지시서
- work_order_item: 작업지시서 항목
- inventory_transaction.document_files 추가
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3g4h5i6'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 발주서 테이블 생성
    op.create_table('purchase_order',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('po_number', sa.String(20), nullable=False, comment='발주서번호'),
        sa.Column('supplier_id', sa.Integer(), nullable=False, comment='공급업체 ID'),
        sa.Column('order_date', sa.Date(), nullable=False, comment='발주일'),
        sa.Column('expected_delivery_date', sa.Date(), nullable=True, comment='예상 납기일'),
        sa.Column('actual_delivery_date', sa.Date(), nullable=True, comment='실제 입고일'),
        sa.Column('total_amount', sa.Numeric(15, 2), nullable=True, default=0, comment='총 금액'),
        sa.Column('currency', sa.String(10), nullable=True, default='KRW', comment='통화'),
        sa.Column('tax_amount', sa.Numeric(15, 2), nullable=True, default=0, comment='세금'),
        sa.Column('discount_amount', sa.Numeric(15, 2), nullable=True, default=0, comment='할인금액'),
        sa.Column('status', sa.String(20), nullable=True, default='DRAFT', comment='상태'),
        sa.Column('payment_terms', sa.String(200), nullable=True, comment='결제 조건'),
        sa.Column('delivery_terms', sa.String(200), nullable=True, comment='납품 조건'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='비고'),
        sa.Column('document_files', sa.JSON(), nullable=True, comment='첨부파일'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='생성자 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='생성일시'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='수정자 ID'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='수정일시'),
        sa.ForeignKeyConstraint(['supplier_id'], ['business_partner.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_order_id'), 'purchase_order', ['id'], unique=False)
    op.create_index(op.f('ix_purchase_order_po_number'), 'purchase_order', ['po_number'], unique=True)
    op.create_index(op.f('ix_purchase_order_supplier_id'), 'purchase_order', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_purchase_order_status'), 'purchase_order', ['status'], unique=False)
    op.create_index(op.f('ix_purchase_order_order_date'), 'purchase_order', ['order_date'], unique=False)

    # 2. 발주서 항목 테이블 생성
    op.create_table('purchase_order_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purchase_order_id', sa.Integer(), nullable=False, comment='발주서 ID'),
        sa.Column('part_id', sa.Integer(), nullable=False, comment='부품 ID'),
        sa.Column('ordered_quantity', sa.Numeric(15, 3), nullable=False, comment='발주 수량'),
        sa.Column('received_quantity', sa.Numeric(15, 3), nullable=True, default=0, comment='입고 수량'),
        sa.Column('defective_quantity', sa.Numeric(15, 3), nullable=True, default=0, comment='불량 수량'),
        sa.Column('unit_price', sa.Numeric(15, 2), nullable=False, comment='단가'),
        sa.Column('line_total', sa.Numeric(15, 2), nullable=True, comment='항목 금액'),
        sa.Column('unit_id', sa.Integer(), nullable=True, comment='단위 ID'),
        sa.Column('line_remarks', sa.Text(), nullable=True, comment='항목 비고'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_order.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id']),
        sa.ForeignKeyConstraint(['unit_id'], ['unit.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_order_item_id'), 'purchase_order_item', ['id'], unique=False)
    op.create_index(op.f('ix_purchase_order_item_po_id'), 'purchase_order_item', ['purchase_order_id'], unique=False)
    op.create_index(op.f('ix_purchase_order_item_part_id'), 'purchase_order_item', ['part_id'], unique=False)

    # 3. 작업지시서 테이블 생성
    op.create_table('work_order',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wo_number', sa.String(20), nullable=False, comment='작업지시서번호'),
        sa.Column('product_part_id', sa.Integer(), nullable=False, comment='완제품 부품 ID'),
        sa.Column('customer_id', sa.Integer(), nullable=True, comment='고객사 ID'),
        sa.Column('customer_order_no', sa.String(50), nullable=True, comment='고객 주문번호'),
        sa.Column('order_quantity', sa.Numeric(15, 3), nullable=False, comment='지시 수량'),
        sa.Column('completed_quantity', sa.Numeric(15, 3), nullable=True, default=0, comment='완료 수량'),
        sa.Column('defective_quantity', sa.Numeric(15, 3), nullable=True, default=0, comment='불량 수량'),
        sa.Column('status', sa.String(20), nullable=True, default='RECEIVED', comment='상태'),
        # 단계별 일시
        sa.Column('received_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='접수일시'),
        sa.Column('approved_date', sa.DateTime(timezone=True), nullable=True, comment='승인일시'),
        sa.Column('approved_by', sa.Integer(), nullable=True, comment='승인자 ID'),
        sa.Column('issue_scheduled_date', sa.Date(), nullable=True, comment='부품출고 예정일'),
        sa.Column('issue_completed_date', sa.DateTime(timezone=True), nullable=True, comment='부품출고 완료일시'),
        sa.Column('production_scheduled_date', sa.Date(), nullable=True, comment='작업 예정일'),
        sa.Column('production_start_date', sa.DateTime(timezone=True), nullable=True, comment='작업 시작일시'),
        sa.Column('production_end_date', sa.DateTime(timezone=True), nullable=True, comment='작업 완료일시'),
        sa.Column('inspection_scheduled_date', sa.Date(), nullable=True, comment='검사 예정일'),
        sa.Column('inspection_completed_date', sa.DateTime(timezone=True), nullable=True, comment='검사 완료일시'),
        sa.Column('packing_scheduled_date', sa.Date(), nullable=True, comment='포장 예정일'),
        sa.Column('packing_completed_date', sa.DateTime(timezone=True), nullable=True, comment='포장 완료일시'),
        sa.Column('shipping_scheduled_date', sa.Date(), nullable=True, comment='출하 예정일'),
        sa.Column('shipping_completed_date', sa.DateTime(timezone=True), nullable=True, comment='출하 완료일시'),
        sa.Column('priority', sa.Integer(), nullable=True, default=0, comment='우선순위'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='비고'),
        sa.Column('document_files', sa.JSON(), nullable=True, comment='첨부파일'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='생성자 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='생성일시'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='수정자 ID'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='수정일시'),
        sa.ForeignKeyConstraint(['product_part_id'], ['parts.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['business_partner.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_order_id'), 'work_order', ['id'], unique=False)
    op.create_index(op.f('ix_work_order_wo_number'), 'work_order', ['wo_number'], unique=True)
    op.create_index(op.f('ix_work_order_product_part_id'), 'work_order', ['product_part_id'], unique=False)
    op.create_index(op.f('ix_work_order_customer_id'), 'work_order', ['customer_id'], unique=False)
    op.create_index(op.f('ix_work_order_status'), 'work_order', ['status'], unique=False)

    # 4. 작업지시서 항목 테이블 생성
    op.create_table('work_order_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('work_order_id', sa.Integer(), nullable=False, comment='작업지시서 ID'),
        sa.Column('part_id', sa.Integer(), nullable=False, comment='부품 ID'),
        sa.Column('bom_id', sa.Integer(), nullable=True, comment='BOM ID'),
        sa.Column('required_quantity', sa.Numeric(15, 3), nullable=False, comment='필요 수량'),
        sa.Column('issued_quantity', sa.Numeric(15, 3), nullable=True, default=0, comment='출고 수량'),
        sa.Column('additional_quantity', sa.Numeric(15, 3), nullable=True, default=0, comment='추가 출고'),
        sa.Column('returned_quantity', sa.Numeric(15, 3), nullable=True, default=0, comment='반납 수량'),
        sa.Column('unit_id', sa.Integer(), nullable=True, comment='단위 ID'),
        sa.Column('bom_level', sa.Integer(), nullable=True, default=1, comment='BOM 레벨'),
        sa.Column('line_remarks', sa.Text(), nullable=True, comment='항목 비고'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_order.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id']),
        sa.ForeignKeyConstraint(['bom_id'], ['bom.id']),
        sa.ForeignKeyConstraint(['unit_id'], ['unit.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_order_item_id'), 'work_order_item', ['id'], unique=False)
    op.create_index(op.f('ix_work_order_item_wo_id'), 'work_order_item', ['work_order_id'], unique=False)
    op.create_index(op.f('ix_work_order_item_part_id'), 'work_order_item', ['part_id'], unique=False)

    # 5. inventory_transaction에 document_files 컬럼 추가
    op.add_column('inventory_transaction', sa.Column('document_files', sa.JSON(), nullable=True, comment='첨부파일'))


def downgrade() -> None:
    # 역순으로 삭제
    # 5. inventory_transaction에서 document_files 컬럼 삭제
    op.drop_column('inventory_transaction', 'document_files')

    # 4. work_order_item 삭제
    op.drop_index(op.f('ix_work_order_item_part_id'), table_name='work_order_item')
    op.drop_index(op.f('ix_work_order_item_wo_id'), table_name='work_order_item')
    op.drop_index(op.f('ix_work_order_item_id'), table_name='work_order_item')
    op.drop_table('work_order_item')

    # 3. work_order 삭제
    op.drop_index(op.f('ix_work_order_status'), table_name='work_order')
    op.drop_index(op.f('ix_work_order_customer_id'), table_name='work_order')
    op.drop_index(op.f('ix_work_order_product_part_id'), table_name='work_order')
    op.drop_index(op.f('ix_work_order_wo_number'), table_name='work_order')
    op.drop_index(op.f('ix_work_order_id'), table_name='work_order')
    op.drop_table('work_order')

    # 2. purchase_order_item 삭제
    op.drop_index(op.f('ix_purchase_order_item_part_id'), table_name='purchase_order_item')
    op.drop_index(op.f('ix_purchase_order_item_po_id'), table_name='purchase_order_item')
    op.drop_index(op.f('ix_purchase_order_item_id'), table_name='purchase_order_item')
    op.drop_table('purchase_order_item')

    # 1. purchase_order 삭제
    op.drop_index(op.f('ix_purchase_order_order_date'), table_name='purchase_order')
    op.drop_index(op.f('ix_purchase_order_status'), table_name='purchase_order')
    op.drop_index(op.f('ix_purchase_order_supplier_id'), table_name='purchase_order')
    op.drop_index(op.f('ix_purchase_order_po_number'), table_name='purchase_order')
    op.drop_index(op.f('ix_purchase_order_id'), table_name='purchase_order')
    op.drop_table('purchase_order')
