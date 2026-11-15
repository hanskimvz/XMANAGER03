"""v0.55.0 구매기안서(PURCHASE)에서 결제방법 필드 제거

Revision ID: e4f5a6b7c8d9
Revises: c2d3e4f5a6b7
Create Date: 2026-07-06

구매기안서에는 결제방법이 불필요(집행 시점에 지출결의서에서 결정) → PURCHASE
fields_schema 에서 payment_method 필드만 제거. 지출결의서(DISBURSEMENT)에는 유지.
드리프트 안전: key='payment_method' 요소만 필터링 제거(다른 필드/순서 보존).
"""
from alembic import op

revision = "e4f5a6b7c8d9"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


_REMOVE_SQL = """
UPDATE approval_forms
SET fields_schema = (
    SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
    FROM jsonb_array_elements(fields_schema) AS elem
    WHERE elem->>'key' <> 'payment_method'
)
WHERE code = 'PURCHASE'
"""

# 롤백: payment_method 를 다시 삽입(집행조건 앞 위치, 이미 있으면 미삽입)
_RESTORE_SQL = """
UPDATE approval_forms
SET fields_schema = jsonb_insert(
    fields_schema, '{3}',
    '{"key":"payment_method","label":"결제방법","type":"select","required":true,"options":["현금-선결제","익월결제","카드결제"]}'::jsonb
)
WHERE code = 'PURCHASE'
  AND NOT (fields_schema @> '[{"key":"payment_method"}]'::jsonb)
"""


def upgrade() -> None:
    op.execute(_REMOVE_SQL)


def downgrade() -> None:
    op.execute(_RESTORE_SQL)
