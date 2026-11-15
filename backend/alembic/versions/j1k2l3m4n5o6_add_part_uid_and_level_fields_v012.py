"""add part_uid and level fields v0.12

Revision ID: j1k2l3m4n5o6
Revises: i1j2k3l4m5n6
Create Date: 2026-01-19

v0.12.0 변경사항:
1. parts 테이블에 part_uid 컬럼 추가 (바코드/QR용 고유 ID)
2. level 테이블에 is_assembly, cost_calculation 컬럼 추가 (레벨별 관리 구분)
3. 기존 데이터에 part_uid 자동 생성
4. 기존 level 데이터에 is_assembly, cost_calculation 값 설정
"""
from alembic import op
import sqlalchemy as sa
import hashlib
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'j1k2l3m4n5o6'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def generate_part_uid(part_number: str, created_at) -> str:
    """품번 + 생성시간 기반 고유 ID 생성"""
    if created_at is None:
        created_at = datetime.now()
    if hasattr(created_at, 'isoformat'):
        timestamp_str = created_at.isoformat()
    else:
        timestamp_str = str(created_at)
    seed = f"{part_number}:{timestamp_str}"
    hash_value = hashlib.sha256(seed.encode('utf-8')).hexdigest()[:8].upper()
    return f"PT-{hash_value}"


def upgrade() -> None:
    # 1. parts 테이블에 part_uid 컬럼 추가
    op.add_column('parts', sa.Column('part_uid', sa.String(12), nullable=True, comment='고유 ID (PT-XXXXXXXX, 바코드용, 변경불가)'))

    # 2. level 테이블에 is_assembly, cost_calculation 컬럼 추가
    op.add_column('level', sa.Column('is_assembly', sa.Boolean(), nullable=True, server_default='false', comment='조립품 여부 (True: BOM관리, False: 부품관리)'))
    op.add_column('level', sa.Column('cost_calculation', sa.String(10), nullable=True, server_default='MANUAL', comment='단가계산방식 (MANUAL: 직접입력, BOM: 하위합산)'))

    # 3. 기존 parts 데이터에 part_uid 생성
    connection = op.get_bind()
    parts = connection.execute(sa.text("SELECT id, part_number, created_at FROM parts WHERE part_uid IS NULL"))
    for part in parts:
        part_uid = generate_part_uid(part.part_number, part.created_at)
        connection.execute(
            sa.text("UPDATE parts SET part_uid = :uid WHERE id = :id"),
            {"uid": part_uid, "id": part.id}
        )

    # 4. part_uid에 unique 인덱스 추가
    op.create_index('ix_parts_part_uid', 'parts', ['part_uid'], unique=True)

    # 5. 기존 level 데이터에 is_assembly, cost_calculation 값 설정
    # 단품 레벨: M, O, R → is_assembly=False, cost_calculation=MANUAL
    # 조립품 레벨: C, S, P, K, F → is_assembly=True, cost_calculation=BOM
    connection.execute(sa.text("""
        UPDATE level SET is_assembly = false, cost_calculation = 'MANUAL'
        WHERE code IN ('M', 'O', 'R')
    """))
    connection.execute(sa.text("""
        UPDATE level SET is_assembly = true, cost_calculation = 'BOM'
        WHERE code IN ('C', 'S', 'P', 'K', 'F')
    """))

    # 6. 아직 설정되지 않은 level은 기본값 적용
    connection.execute(sa.text("""
        UPDATE level SET is_assembly = false, cost_calculation = 'MANUAL'
        WHERE is_assembly IS NULL
    """))


def downgrade() -> None:
    # 인덱스 제거
    op.drop_index('ix_parts_part_uid', table_name='parts')

    # 컬럼 제거
    op.drop_column('parts', 'part_uid')
    op.drop_column('level', 'is_assembly')
    op.drop_column('level', 'cost_calculation')
