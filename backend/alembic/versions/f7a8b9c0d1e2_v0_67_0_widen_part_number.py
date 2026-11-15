"""v0.67.0 부품 품번 컬럼 길이 확대 (25/30 → 100)

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-27

자유형식 오더코드(영업품목 product_code = String(100))가 길어지면
PI→생산요청 초안 생성 시 stub 부품 INSERT 에서 part_number(25)/part_number_display(30)
길이를 초과해 StringDataRightTruncation 오류로 생산요청이 실패했다.
(예: 'HXB15AS-RJL-B-O4-S1-S09-LC-0.23' = 31자)
소스 컬럼(product_code, 100)에 맞춰 부품 품번 컬럼을 100자로 확대.
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "parts", "part_number",
        existing_type=sa.String(length=25),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
    op.alter_column(
        "parts", "part_number_display",
        existing_type=sa.String(length=30),
        type_=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    # 축소는 데이터 잘림 위험이 있어 되돌리지 않음 (no-op)
    pass
