"""update_parts_model_v010

Parts 모델 수정 - 품번 구조 변경 (v0.10.0)
- 신규 컬럼 추가: product_line_id, part_group_id, item_code, development_type_id, drawing_type_id
- 기존 컬럼 nullable 변경: major_category_id, minor_category_id, item_code_id, level_id
- 품번 길이 변경: 20->25 (시스템용), 25->30 (표시용)

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-12 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 신규 컬럼 추가
    op.add_column('parts', sa.Column('product_line_id', sa.Integer(), nullable=True, comment='대분류/제품라인 ID'))
    op.add_column('parts', sa.Column('part_group_id', sa.Integer(), nullable=True, comment='소분류/품목군 ID'))
    op.add_column('parts', sa.Column('item_code', sa.String(5), nullable=True, comment='품목코드 (5자리)'))
    op.add_column('parts', sa.Column('development_type_id', sa.Integer(), nullable=True, comment='개발구분 ID'))
    op.add_column('parts', sa.Column('drawing_type_id', sa.Integer(), nullable=True, comment='도면여부 ID'))

    # 2. FK 제약조건 추가
    op.create_foreign_key('fk_parts_product_line', 'parts', 'product_line', ['product_line_id'], ['id'])
    op.create_foreign_key('fk_parts_part_group', 'parts', 'part_group', ['part_group_id'], ['id'])
    op.create_foreign_key('fk_parts_development_type', 'parts', 'development_type', ['development_type_id'], ['id'])
    op.create_foreign_key('fk_parts_drawing_type', 'parts', 'drawing_type', ['drawing_type_id'], ['id'])

    # 3. 기존 컬럼 nullable 변경 (PostgreSQL)
    op.alter_column('parts', 'major_category_id', nullable=True)
    op.alter_column('parts', 'minor_category_id', nullable=True)
    op.alter_column('parts', 'item_code_id', nullable=True)
    op.alter_column('parts', 'level_id', nullable=True)

    # 4. 품번 컬럼 길이 변경 (PostgreSQL)
    op.alter_column('parts', 'part_number',
                    existing_type=sa.String(20),
                    type_=sa.String(25))
    op.alter_column('parts', 'part_number_display',
                    existing_type=sa.String(25),
                    type_=sa.String(30))


def downgrade() -> None:
    # 4. 품번 컬럼 길이 원복
    op.alter_column('parts', 'part_number',
                    existing_type=sa.String(25),
                    type_=sa.String(20))
    op.alter_column('parts', 'part_number_display',
                    existing_type=sa.String(30),
                    type_=sa.String(25))

    # 3. 기존 컬럼 nullable 원복
    op.alter_column('parts', 'major_category_id', nullable=False)
    op.alter_column('parts', 'minor_category_id', nullable=False)
    op.alter_column('parts', 'item_code_id', nullable=False)
    op.alter_column('parts', 'level_id', nullable=False)

    # 2. FK 제약조건 삭제
    op.drop_constraint('fk_parts_drawing_type', 'parts', type_='foreignkey')
    op.drop_constraint('fk_parts_development_type', 'parts', type_='foreignkey')
    op.drop_constraint('fk_parts_part_group', 'parts', type_='foreignkey')
    op.drop_constraint('fk_parts_product_line', 'parts', type_='foreignkey')

    # 1. 신규 컬럼 삭제
    op.drop_column('parts', 'drawing_type_id')
    op.drop_column('parts', 'development_type_id')
    op.drop_column('parts', 'item_code')
    op.drop_column('parts', 'part_group_id')
    op.drop_column('parts', 'product_line_id')
