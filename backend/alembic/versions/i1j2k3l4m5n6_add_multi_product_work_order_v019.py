"""add_multi_product_work_order_v019

Revision ID: i1j2k3l4m5n6
Revises: h1i2j3k4l5m6
Create Date: 2026-01-16 18:00:00.000000

작업지시서 다중 제품 지원 (v0.19.0)
- WorkOrderProduct 테이블 생성
- WorkOrderItem에 work_order_product_id 컬럼 추가
- WorkOrder의 product_part_id, order_quantity nullable로 변경
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i1j2k3l4m5n6'
down_revision: Union[str, None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. WorkOrderProduct 테이블 생성
    op.create_table(
        'work_order_product',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('work_order_id', sa.Integer(), sa.ForeignKey('work_order.id', ondelete='CASCADE'), nullable=False, index=True, comment='작업지시서 ID'),
        sa.Column('product_part_id', sa.Integer(), sa.ForeignKey('parts.id'), nullable=False, index=True, comment='제품 부품 ID'),
        sa.Column('order_quantity', sa.Numeric(15, 3), nullable=False, comment='지시 수량'),
        sa.Column('completed_quantity', sa.Numeric(15, 3), default=0, comment='완료 수량'),
        sa.Column('defective_quantity', sa.Numeric(15, 3), default=0, comment='불량 수량'),
        sa.Column('sort_order', sa.Integer(), default=0, comment='정렬순서'),
        sa.Column('line_remarks', sa.Text(), nullable=True, comment='항목 비고'),
    )

    # 2. WorkOrderItem에 work_order_product_id 컬럼 추가
    op.add_column('work_order_item', sa.Column('work_order_product_id', sa.Integer(), sa.ForeignKey('work_order_product.id', ondelete='CASCADE'), nullable=True, comment='작업지시서 제품 ID'))
    op.create_index('ix_work_order_item_work_order_product_id', 'work_order_item', ['work_order_product_id'])

    # 3. WorkOrder의 product_part_id, order_quantity nullable로 변경
    # SQLite에서는 ALTER COLUMN을 지원하지 않으므로, 다른 DB에서만 실행
    # op.alter_column('work_order', 'product_part_id', existing_type=sa.Integer(), nullable=True)
    # op.alter_column('work_order', 'order_quantity', existing_type=sa.Numeric(15, 3), nullable=True)

    # 4. 기존 데이터 마이그레이션: 기존 work_order의 product_part_id를 work_order_product로 복사
    # 이 작업은 데이터가 있는 경우 수동으로 실행해야 합니다.
    # INSERT INTO work_order_product (work_order_id, product_part_id, order_quantity, completed_quantity, defective_quantity, sort_order)
    # SELECT id, product_part_id, order_quantity, completed_quantity, defective_quantity, 0
    # FROM work_order WHERE product_part_id IS NOT NULL


def downgrade() -> None:
    # 1. WorkOrderItem에서 work_order_product_id 컬럼 삭제
    op.drop_index('ix_work_order_item_work_order_product_id', table_name='work_order_item')
    op.drop_column('work_order_item', 'work_order_product_id')

    # 2. WorkOrderProduct 테이블 삭제
    op.drop_table('work_order_product')

    # 3. WorkOrder의 product_part_id, order_quantity nullable=False로 복원
    # op.alter_column('work_order', 'product_part_id', existing_type=sa.Integer(), nullable=False)
    # op.alter_column('work_order', 'order_quantity', existing_type=sa.Numeric(15, 3), nullable=False)
