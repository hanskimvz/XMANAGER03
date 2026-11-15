"""v1.0.0 지출결의서(DISBURSEMENT)에서 시행일/실집행액 필드 제거

Revision ID: xm_v1000_disb_cols
Revises: xm_v0990_po_disb
Create Date: 2026-09-15

지출결의서 fields_schema 에서 다음 두 필드를 제거:
  - exec_date(시행일/집행일): 집행 시행일은 최종승인(집행) 화면에서 입력·기록되고
    문서 상세에서 확인 가능하므로, 폼 필드(칼럼)로는 불필요.
  - actual_amount(실집행액): 특이사항이 있을 때만 비고(note)에 기재하는 방식으로 전환.
드리프트 안전: 해당 key 요소만 필터링 제거(다른 필드/순서 보존). 백엔드 집행 로직은
form_data.exec_date 를 계속 기록하므로 영향 없음(폼 노출만 제거).
"""
from alembic import op

revision = "xm_v1000_disb_cols"
down_revision = "xm_v0990_po_disb"
branch_labels = None
depends_on = None


_REMOVE_SQL = """
UPDATE approval_forms
SET fields_schema = (
    SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
    FROM jsonb_array_elements(fields_schema) AS elem
    WHERE elem->>'key' NOT IN ('exec_date', 'actual_amount')
)
WHERE code = 'DISBURSEMENT'
"""

# 롤백: 원위치(비고 앞)에 두 필드를 다시 삽입. 이미 있으면 미삽입.
_RESTORE_EXEC = """
UPDATE approval_forms
SET fields_schema = jsonb_insert(
    fields_schema, '{5}',
    '{"key":"exec_date","label":"시행일(집행일)","type":"date","required":false,"help":"집행 담당이 승인(집행) 시 입력"}'::jsonb
)
WHERE code = 'DISBURSEMENT'
  AND NOT (fields_schema @> '[{"key":"exec_date"}]'::jsonb)
"""

_RESTORE_ACTUAL = """
UPDATE approval_forms
SET fields_schema = jsonb_insert(
    fields_schema, '{6}',
    '{"key":"actual_amount","label":"실집행액","type":"number","required":false,"help":"미입력 시 청구 금액과 동일"}'::jsonb
)
WHERE code = 'DISBURSEMENT'
  AND NOT (fields_schema @> '[{"key":"actual_amount"}]'::jsonb)
"""


def upgrade() -> None:
    op.execute(_REMOVE_SQL)


def downgrade() -> None:
    op.execute(_RESTORE_EXEC)
    op.execute(_RESTORE_ACTUAL)
