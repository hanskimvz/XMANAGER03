"""Add ProductionRequestItem table for multi-product support v0.22.0

Revision ID: m1n2o3p4q5r6
Revises: l1m2n3o4p5q6
Create Date: 2026-01-26

v0.22.0: 생산 요청서 다중 제품 지원
- production_request_item 테이블 추가
- production_request.product_part_id nullable 변경
- production_request.requested_quantity nullable 변경
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'm1n2o3p4q5r6'
down_revision = 'l1m2n3o4p5q6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. production_request_item 테이블 생성
    op.create_table(
        'production_request_item',
        sa.Column('id', sa.Integer(), nullable=False, comment='ID'),
        sa.Column('production_request_id', sa.Integer(), nullable=False, comment='생산 요청서 ID'),
        sa.Column('product_part_id', sa.Integer(), nullable=False, comment='제품 부품 ID'),
        sa.Column('requested_quantity', sa.Numeric(precision=15, scale=3), nullable=False, comment='요청 수량'),
        sa.Column('line_remarks', sa.Text(), nullable=True, comment='항목 비고'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['production_request_id'], ['production_request.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_part_id'], ['parts.id']),
    )
    op.create_index('ix_production_request_item_id', 'production_request_item', ['id'])
    op.create_index('ix_production_request_item_production_request_id', 'production_request_item', ['production_request_id'])
    op.create_index('ix_production_request_item_product_part_id', 'production_request_item', ['product_part_id'])

    # 2. production_request 테이블의 product_part_id, requested_quantity를 nullable로 변경
    # SQLite에서는 ALTER COLUMN이 지원되지 않아 우회 방법 사용 (새 컬럼 추가 불필요, 이미 있는 데이터는 유지)
    # MySQL/PostgreSQL의 경우 아래 코드 사용
    try:
        op.alter_column('production_request', 'product_part_id',
                        existing_type=sa.Integer(),
                        nullable=True)
        op.alter_column('production_request', 'requested_quantity',
                        existing_type=sa.Numeric(precision=15, scale=3),
                        nullable=True)
    except Exception:
        # SQLite 등에서 ALTER COLUMN이 지원되지 않는 경우 무시
        pass

    # 3. 기존 데이터 마이그레이션: 기존 단일 제품 데이터를 items 테이블로 복사
    # (이 작업은 production_request에 데이터가 있는 경우에만 실행)
    op.execute("""
        INSERT INTO production_request_item (production_request_id, product_part_id, requested_quantity, sort_order)
        SELECT id, product_part_id, requested_quantity, 0
        FROM production_request
        WHERE product_part_id IS NOT NULL AND requested_quantity IS NOT NULL
    """)


def downgrade():
    # production_request_item 테이블 삭제
    op.drop_index('ix_production_request_item_product_part_id', table_name='production_request_item')
    op.drop_index('ix_production_request_item_production_request_id', table_name='production_request_item')
    op.drop_index('ix_production_request_item_id', table_name='production_request_item')
    op.drop_table('production_request_item')

    # production_request 테이블의 컬럼을 다시 NOT NULL로 변경 (선택적)
    try:
        op.alter_column('production_request', 'product_part_id',
                        existing_type=sa.Integer(),
                        nullable=False)
        op.alter_column('production_request', 'requested_quantity',
                        existing_type=sa.Numeric(precision=15, scale=3),
                        nullable=False)
    except Exception:
        pass
