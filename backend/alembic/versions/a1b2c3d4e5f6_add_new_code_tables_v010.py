"""add_new_code_tables_v010

품번 구조 변경을 위한 신규 코드 테이블 추가 (v0.10.0 → v1.1)
- ProductLine: 대분류/제품라인 (HB01, BI03, TF01 등) - 4자리
- PartGroup: 소분류/품목군 (DCP, PLP, OCP 등) - 3자리
- DevelopmentType: 개발구분 (D, S, M, R, C, P) - 분류속성
- PartType: 부품유형 (P, E, O, M, G, I, W, A, C, H, X, T) - 분류속성, 다중선택
- DrawingType: 도면여부 (D, S, N) - 분류속성
- part_part_type: 부품-부품유형 다대다 관계 테이블

Revision ID: a1b2c3d4e5f6
Revises: e920940b6757
Create Date: 2026-01-12 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e920940b6757'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ProductLine 테이블 생성 (대분류/제품라인)
    op.create_table('product_line',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(10), nullable=False, comment='코드 (3자리)'),
        sa.Column('name_ko', sa.String(50), nullable=False, comment='한글명'),
        sa.Column('name_en', sa.String(50), nullable=True, comment='영문명'),
        sa.Column('description', sa.Text(), nullable=True, comment='설명'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True, comment='사용여부'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='수정일시'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_product_line_id', 'product_line', ['id'])
    op.create_index('ix_product_line_code', 'product_line', ['code'], unique=True)

    # PartGroup 테이블 생성 (소분류/품목군)
    op.create_table('part_group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(10), nullable=False, comment='코드 (2~3자리)'),
        sa.Column('name_ko', sa.String(50), nullable=False, comment='한글명'),
        sa.Column('name_en', sa.String(50), nullable=True, comment='영문명'),
        sa.Column('description', sa.Text(), nullable=True, comment='설명'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True, comment='사용여부'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='수정일시'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_part_group_id', 'part_group', ['id'])
    op.create_index('ix_part_group_code', 'part_group', ['code'], unique=True)

    # DevelopmentType 테이블 생성 (개발구분)
    op.create_table('development_type',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(10), nullable=False, comment='코드 (1자리)'),
        sa.Column('name_ko', sa.String(50), nullable=False, comment='한글명'),
        sa.Column('name_en', sa.String(50), nullable=True, comment='영문명'),
        sa.Column('description', sa.Text(), nullable=True, comment='설명'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True, comment='사용여부'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='수정일시'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_development_type_id', 'development_type', ['id'])
    op.create_index('ix_development_type_code', 'development_type', ['code'], unique=True)

    # PartType 테이블 생성 (부품유형)
    op.create_table('part_type',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(10), nullable=False, comment='코드 (1자리)'),
        sa.Column('name_ko', sa.String(50), nullable=False, comment='한글명'),
        sa.Column('name_en', sa.String(50), nullable=True, comment='영문명'),
        sa.Column('description', sa.Text(), nullable=True, comment='설명'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True, comment='사용여부'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='수정일시'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_part_type_id', 'part_type', ['id'])
    op.create_index('ix_part_type_code', 'part_type', ['code'], unique=True)

    # DrawingType 테이블 생성 (도면여부)
    op.create_table('drawing_type',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(10), nullable=False, comment='코드 (1자리)'),
        sa.Column('name_ko', sa.String(50), nullable=False, comment='한글명'),
        sa.Column('name_en', sa.String(50), nullable=True, comment='영문명'),
        sa.Column('description', sa.Text(), nullable=True, comment='설명'),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0, comment='정렬순서'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True, comment='사용여부'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='수정일시'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_drawing_type_id', 'drawing_type', ['id'])
    op.create_index('ix_drawing_type_code', 'drawing_type', ['code'], unique=True)

    # part_part_type 다대다 관계 테이블 생성
    op.create_table('part_part_type',
        sa.Column('part_id', sa.Integer(), nullable=False),
        sa.Column('part_type_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['part_type_id'], ['part_type.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('part_id', 'part_type_id')
    )

    # 초기 데이터 삽입 - ProductLine (대분류/제품라인) - v1.1: 4자리 코드
    op.execute("""
        INSERT INTO product_line (code, name_ko, name_en, description, sort_order, is_active) VALUES
        ('HB01', 'HXB11', 'HXB11', 'Expanded Beam 11핀', 1, true),
        ('HB03', 'HXB13', 'HXB13', 'Expanded Beam 13핀', 2, true),
        ('HB05', 'HXB15', 'HXB15', 'Expanded Beam 15핀', 3, true),
        ('HB07', 'HXB17', 'HXB17', 'Expanded Beam 17핀', 4, true),
        ('HB00', 'HXB공용', 'HXB Common', 'HXB 시리즈 공용 부품', 5, true),
        ('BI01', 'XBI11', 'XBI11', '인서트 11핀', 6, true),
        ('BI03', 'XBI13', 'XBI13', '인서트 13핀', 7, true),
        ('BI05', 'XBI15', 'XBI15', '인서트 15핀', 8, true),
        ('BI07', 'XBI17', 'XBI17', '인서트 17핀', 9, true),
        ('BI00', 'XBI공용', 'XBI Common', 'XBI 시리즈 공용 부품', 10, true),
        ('IK05', 'XBI15K', 'XBI15 Kit', 'XBI15 키트', 11, true),
        ('TF01', 'TFOCA', 'TFOCA', 'TFOCA 커넥터', 12, true),
        ('COM0', '공용', 'Common', '공용/상용 부품', 13, true)
    """)

    # 초기 데이터 삽입 - PartGroup (소분류/품목군)
    op.execute("""
        INSERT INTO part_group (code, name_ko, name_en, description, sort_order, is_active) VALUES
        ('DCP', '더스트캡 부품', 'Dust Cap Parts', 'Dust Cap Parts', 1, true),
        ('BIP', '인서트용 부품', 'Insert Parts', 'Insert Parts', 2, true),
        ('CHP', '케이블홀더', 'Cable Holder Parts', 'Cable Holder Parts', 3, true),
        ('PLP', '플러그 부품', 'Plug Parts', 'Plug Parts', 4, true),
        ('RCP', '리셉터클 부품', 'Receptacle Parts', 'Receptacle Parts', 5, true),
        ('CMP', '화학소재', 'Chemical Materials', 'Chemical Materials', 6, true),
        ('MNP', '공정', 'Manufacturing Process', 'Manufacturing Process', 7, true),
        ('CSP', '하우징 파트', 'Casing Parts', 'Casing Parts', 8, true),
        ('ELP', '전자 부품', 'Electronic Parts', 'Electronic Parts', 9, true),
        ('OCP', '광학 부품', 'Optical Parts', 'Optical Parts', 10, true),
        ('JIG', '지그류', 'Jig & Fixture', 'Jig & Fixture', 11, true),
        ('O2', '광 2채널', 'Optical 2ch', 'Optical 2 channel', 12, true),
        ('O4', '광 4채널', 'Optical 4ch', 'Optical 4 channel', 13, true),
        ('O6', '광 6채널', 'Optical 6ch', 'Optical 6 channel', 14, true),
        ('O8', '광 8채널', 'Optical 8ch', 'Optical 8 channel', 15, true),
        ('H2', '광2/전2', 'Hybrid 2ch', 'Hybrid 광2/전2 (AWG16)', 16, true),
        ('H4', '광4/전2', 'Hybrid 4ch', 'Hybrid 광4/전2 (AWG16)', 17, true),
        ('CT', '커스텀', 'Custom', 'Custom', 18, true),
        ('BL', '볼렌즈', 'Ball Lens', 'Ball Lens', 19, true),
        ('CR', '크림프링', 'Crimp Ring', 'Crimp Ring', 20, true),
        ('BT', '볼트/너트', 'Bolt/Nut', 'Bolt/Nut', 21, true),
        ('SO', '규격오링', 'Standard O-Ring', 'Standard O-Ring', 22, true),
        ('NO', '비규격오링', 'Non-standard O-Ring', 'Non-standard O-Ring', 23, true),
        ('CB', '케이블부트', 'Cable Boot', 'Cable Boot', 24, true),
        ('WR', '와셔', 'Washer', 'Washer', 25, true)
    """)

    # 초기 데이터 삽입 - DevelopmentType (개발구분)
    op.execute("""
        INSERT INTO development_type (code, name_ko, name_en, description, sort_order, is_active) VALUES
        ('D', '개발품', 'Developed Part', '자체 설계/개발 부품', 1, true),
        ('S', '규격품', 'Standard Part', '표준 규격 부품', 2, true),
        ('M', '상용품', 'Market Part', '시중 구매 부품', 3, true),
        ('R', '원소재', 'Raw Material', '원자재', 4, true),
        ('C', '주문품', 'Custom Part', '고객 맞춤 부품', 5, true),
        ('P', '공정', 'Process', '제조 공정', 6, true)
    """)

    # 초기 데이터 삽입 - PartType (부품유형)
    op.execute("""
        INSERT INTO part_type (code, name_ko, name_en, description, sort_order, is_active) VALUES
        ('P', '가공품', 'Processed Part', '가공품', 1, true),
        ('E', '고무품', 'Elastomer Part', '고무품', 2, true),
        ('O', '광학품', 'Optical Part', '광학품', 3, true),
        ('M', '금형품', 'Mold Part', '금형품', 4, true),
        ('G', '일반기계부품', 'General Mechanic Part', '일반 기계 부품', 5, true),
        ('I', '사출품', 'Injection Part', '사출품', 6, true),
        ('W', '와이어류', 'Wire', '와이어류', 7, true),
        ('A', '조립품', 'Assembly', '조립품', 8, true),
        ('C', '케이블류', 'Cable', '케이블류', 9, true),
        ('H', '하드웨어', 'Hardware', '하드웨어', 10, true),
        ('X', '화학품', 'Chemical Part', '화학품', 11, true),
        ('T', '수축튜브', 'Tube', '수축튜브', 12, true)
    """)

    # 초기 데이터 삽입 - DrawingType (도면여부)
    op.execute("""
        INSERT INTO drawing_type (code, name_ko, name_en, description, sort_order, is_active) VALUES
        ('D', '도면', 'Drawing', '도면 있음', 1, true),
        ('S', '표준품번', 'Standard', '표준 규격품 (도면 불필요)', 2, true),
        ('N', '없음', 'None', '도면 없음', 3, true)
    """)


def downgrade() -> None:
    # 테이블 삭제 (역순)
    op.drop_table('part_part_type')
    op.drop_index('ix_drawing_type_code', table_name='drawing_type')
    op.drop_index('ix_drawing_type_id', table_name='drawing_type')
    op.drop_table('drawing_type')
    op.drop_index('ix_part_type_code', table_name='part_type')
    op.drop_index('ix_part_type_id', table_name='part_type')
    op.drop_table('part_type')
    op.drop_index('ix_development_type_code', table_name='development_type')
    op.drop_index('ix_development_type_id', table_name='development_type')
    op.drop_table('development_type')
    op.drop_index('ix_part_group_code', table_name='part_group')
    op.drop_index('ix_part_group_id', table_name='part_group')
    op.drop_table('part_group')
    op.drop_index('ix_product_line_code', table_name='product_line')
    op.drop_index('ix_product_line_id', table_name='product_line')
    op.drop_table('product_line')
