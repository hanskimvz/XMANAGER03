"""add_production_request_v020

Revision ID: k1l2m3n4o5p6
Revises: j1k2l3m4n5o6
Create Date: 2026-01-23 10:00:00.000000

생산 요청서 기능 추가 (v0.20.0)
- ProductionRequest 테이블 생성
- WorkOrder에 production_request_id, order_type 컬럼 추가
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j1k2l3m4n5o6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ProductionRequest 테이블 생성
    op.create_table(
        'production_request',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('request_number', sa.String(20), unique=True, nullable=False, index=True, comment='요청서번호'),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('business_partner.id'), nullable=True, comment='고객사 ID'),
        sa.Column('customer_order_no', sa.String(50), nullable=True, comment='고객 주문번호'),
        sa.Column('product_part_id', sa.Integer(), sa.ForeignKey('parts.id'), nullable=False, index=True, comment='제품 부품 ID'),
        sa.Column('requested_quantity', sa.Numeric(15, 3), nullable=False, comment='요청 수량'),
        sa.Column('due_date', sa.Date(), nullable=True, comment='희망 납기일'),
        sa.Column('status', sa.String(20), default='REQUESTED', index=True, comment='상태'),
        sa.Column('requested_by', sa.Integer(), nullable=True, comment='요청자 ID'),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='요청일시'),
        sa.Column('approved_by', sa.Integer(), nullable=True, comment='승인자 ID'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True, comment='승인일시'),
        sa.Column('rejection_reason', sa.Text(), nullable=True, comment='반려 사유'),
        sa.Column('priority', sa.Integer(), default=0, comment='우선순위'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='비고'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='생성자 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='수정자 ID'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), comment='수정일시'),
    )

    # 2. WorkOrder에 production_request_id 컬럼 추가
    op.add_column('work_order', sa.Column('production_request_id', sa.Integer(), sa.ForeignKey('production_request.id'), nullable=True, comment='생산 요청서 ID'))
    op.create_index('ix_work_order_production_request_id', 'work_order', ['production_request_id'])

    # 3. WorkOrder에 order_type 컬럼 추가
    op.add_column('work_order', sa.Column('order_type', sa.String(20), default='CUSTOMER_ORDER', comment='작업 유형'))


def downgrade() -> None:
    # 1. WorkOrder에서 order_type 컬럼 삭제
    op.drop_column('work_order', 'order_type')

    # 2. WorkOrder에서 production_request_id 컬럼 삭제
    op.drop_index('ix_work_order_production_request_id', table_name='work_order')
    op.drop_column('work_order', 'production_request_id')

    # 3. ProductionRequest 테이블 삭제
    op.drop_table('production_request')
