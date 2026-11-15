"""add_price_management_v018

Revision ID: g1h2i3j4k5l6
Revises: f3g4h5i6j7k8
Create Date: 2026-01-16 12:00:00.000000

원가관리 기능 (v0.18.0)
- Parts 테이블에 가격 필드 추가
- PriceHistory 테이블 생성
- ExchangeRate 테이블 생성
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'f3g4h5i6j7k8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Parts 테이블에 가격 필드 추가
    op.add_column('parts', sa.Column('standard_price', sa.Numeric(15, 4), nullable=True, server_default='0', comment='기준단가 (수동 입력)'))
    op.add_column('parts', sa.Column('standard_price_currency', sa.String(10), nullable=True, server_default='KRW', comment='기준단가 통화'))
    op.add_column('parts', sa.Column('inventory_avg_price', sa.Numeric(15, 4), nullable=True, server_default='0', comment='재고단가 (이동평균)'))
    op.add_column('parts', sa.Column('inventory_avg_price_currency', sa.String(10), nullable=True, server_default='KRW', comment='재고단가 통화'))
    op.add_column('parts', sa.Column('latest_price', sa.Numeric(15, 4), nullable=True, server_default='0', comment='최근단가 (최종 입고가)'))
    op.add_column('parts', sa.Column('latest_price_currency', sa.String(10), nullable=True, server_default='KRW', comment='최근단가 통화'))
    op.add_column('parts', sa.Column('latest_price_date', sa.DateTime(timezone=True), nullable=True, comment='최근단가 갱신일'))
    op.add_column('parts', sa.Column('latest_price_supplier_id', sa.Integer(), sa.ForeignKey('supplier.id'), nullable=True, comment='최근단가 공급업체 ID'))
    op.add_column('parts', sa.Column('avg_price_30d', sa.Numeric(15, 4), nullable=True, server_default='0', comment='평균단가 (최근 30일)'))
    op.add_column('parts', sa.Column('avg_price_90d', sa.Numeric(15, 4), nullable=True, server_default='0', comment='평균단가 (최근 90일)'))
    op.add_column('parts', sa.Column('avg_price_last5', sa.Numeric(15, 4), nullable=True, server_default='0', comment='평균단가 (최근 5건)'))
    op.add_column('parts', sa.Column('avg_price_last10', sa.Numeric(15, 4), nullable=True, server_default='0', comment='평균단가 (최근 10건)'))

    # PriceHistory 테이블 생성
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('part_id', sa.Integer(), sa.ForeignKey('parts.id', ondelete='CASCADE'), nullable=False, index=True, comment='부품 ID'),
        sa.Column('price_type', sa.String(20), nullable=False, server_default='PURCHASE', index=True, comment='가격유형 (PURCHASE/STANDARD/MANUAL/QUOTE)'),
        sa.Column('unit_price', sa.Numeric(15, 4), nullable=False, comment='단가'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='KRW', comment='통화'),
        sa.Column('exchange_rate', sa.Numeric(12, 4), nullable=True, server_default='1', comment='환율 (원화 기준)'),
        sa.Column('unit_price_krw', sa.Numeric(15, 4), nullable=True, comment='원화 환산 단가'),
        sa.Column('quantity', sa.Numeric(15, 3), nullable=True, comment='수량'),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('supplier.id', ondelete='SET NULL'), nullable=True, index=True, comment='공급업체 ID'),
        sa.Column('reference_type', sa.String(30), nullable=True, comment='참조유형 (PO/RECEIVING/QUOTATION/MANUAL)'),
        sa.Column('reference_id', sa.String(50), nullable=True, index=True, comment='참조문서번호'),
        sa.Column('reference_date', sa.DateTime(timezone=True), nullable=True, comment='참조일자 (발주일/입고일)'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='비고'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='생성자 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True, comment='생성일시'),
    )

    # PriceHistory 복합 인덱스
    op.create_index('ix_price_history_part_date', 'price_history', ['part_id', 'created_at'])
    op.create_index('ix_price_history_part_supplier', 'price_history', ['part_id', 'supplier_id'])
    op.create_index('ix_price_history_part_type', 'price_history', ['part_id', 'price_type'])

    # ExchangeRate 테이블 생성
    op.create_table(
        'exchange_rate',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('currency_code', sa.String(10), nullable=False, index=True, comment='통화코드 (USD, EUR, JPY 등)'),
        sa.Column('currency_name', sa.String(50), nullable=True, comment='통화명'),
        sa.Column('rate', sa.Numeric(12, 4), nullable=False, comment='환율 (1 외화 = ? KRW)'),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False, index=True, comment='적용일자'),
        sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True, comment='만료일자'),
        sa.Column('source', sa.String(20), nullable=True, server_default='MANUAL', comment='출처 (MANUAL/API/BANK)'),
        sa.Column('is_active', sa.String(1), nullable=True, server_default='Y', comment='사용여부 (Y/N)'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='생성자 ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True, comment='생성일시'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='수정자 ID'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='수정일시'),
    )

    # ExchangeRate 복합 인덱스
    op.create_index('ix_exchange_rate_currency_date', 'exchange_rate', ['currency_code', 'effective_date'])


def downgrade() -> None:
    # ExchangeRate 테이블 삭제
    op.drop_index('ix_exchange_rate_currency_date', table_name='exchange_rate')
    op.drop_table('exchange_rate')

    # PriceHistory 테이블 삭제
    op.drop_index('ix_price_history_part_type', table_name='price_history')
    op.drop_index('ix_price_history_part_supplier', table_name='price_history')
    op.drop_index('ix_price_history_part_date', table_name='price_history')
    op.drop_table('price_history')

    # Parts 테이블에서 가격 필드 삭제
    op.drop_column('parts', 'avg_price_last10')
    op.drop_column('parts', 'avg_price_last5')
    op.drop_column('parts', 'avg_price_90d')
    op.drop_column('parts', 'avg_price_30d')
    op.drop_column('parts', 'latest_price_supplier_id')
    op.drop_column('parts', 'latest_price_date')
    op.drop_column('parts', 'latest_price_currency')
    op.drop_column('parts', 'latest_price')
    op.drop_column('parts', 'inventory_avg_price_currency')
    op.drop_column('parts', 'inventory_avg_price')
    op.drop_column('parts', 'standard_price_currency')
    op.drop_column('parts', 'standard_price')
