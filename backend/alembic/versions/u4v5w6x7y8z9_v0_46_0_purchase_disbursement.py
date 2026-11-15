"""v0.46.0 구매기안서→지출결의서 연결형 (구매 집행 절차)

- PURCHASE: phase NONE→PRE + 필드 추가(결제방법/집행조건/예정일/금액)
- DISBURSEMENT(지출결의서) 신규: phase POST, linked_form_code=PURCHASE
- 문서번호 접두어는 코드(approval_service._DOC_PREFIX)에서 처리(PE)

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-06-22
"""
import json
from alembic import op


revision = "u4v5w6x7y8z9"
down_revision = "t3u4v5w6x7y8"
branch_labels = None
depends_on = None

_PURCHASE_FIELDS = [
    {"key": "item", "label": "품목", "type": "text", "required": True},
    {"key": "quantity", "label": "수량", "type": "number", "required": True},
    {"key": "unit_price", "label": "단가", "type": "number", "required": False},
    {"key": "amount", "label": "금액(합계)", "type": "number", "required": True, "help": "부가세 포함 집행 예정 금액"},
    {"key": "vendor", "label": "거래처", "type": "text", "required": False},
    {"key": "payment_method", "label": "결제방법", "type": "select", "required": True,
     "options": ["현금-선결제", "익월결제", "카드결제"]},
    {"key": "execution_condition", "label": "집행조건", "type": "select", "required": True,
     "options": ["검수완료 후", "선집행", "익월", "지정일"], "help": "자금 집행 시점 기준"},
    {"key": "planned_exec_date", "label": "집행 예정일", "type": "date", "required": False,
     "help": "집행조건이 '지정일'일 때 입력"},
    {"key": "reason", "label": "사유", "type": "textarea", "required": False},
]

_DISBURSEMENT_FIELDS = [
    {"key": "vendor", "label": "거래처", "type": "text", "required": False},
    {"key": "amount", "label": "청구 금액", "type": "number", "required": True},
    {"key": "payment_method", "label": "결제방법", "type": "select", "required": False,
     "options": ["현금-선결제", "익월결제", "카드결제"]},
    {"key": "request_note", "label": "집행 요청 사유/시점", "type": "textarea", "required": False,
     "help": "예: 검수 완료로 집행 요청 / 선집행 요청 등"},
    {"key": "exec_date", "label": "시행일(집행일)", "type": "date", "required": False,
     "help": "집행 담당이 승인(집행) 시 입력"},
    {"key": "actual_amount", "label": "실집행액", "type": "number", "required": False,
     "help": "미입력 시 청구 금액과 동일"},
    {"key": "note", "label": "비고", "type": "textarea", "required": False},
]


def upgrade() -> None:
    # SQL 문자열 리터럴용 단일따옴표 이스케이프(JSON help 텍스트에 ' 포함)
    pf = json.dumps(_PURCHASE_FIELDS, ensure_ascii=False).replace("'", "''")
    df = json.dumps(_DISBURSEMENT_FIELDS, ensure_ascii=False).replace("'", "''")
    op.execute(
        f"UPDATE approval_forms SET phase='PRE', fields_schema='{pf}'::jsonb WHERE code='PURCHASE'"
    )
    op.execute(
        "INSERT INTO approval_forms (code, name, fields_schema, phase, linked_form_code, is_active, sort_order) "
        f"SELECT 'DISBURSEMENT', '지출결의서', '{df}'::jsonb, 'POST', 'PURCHASE', true, 9 "
        "WHERE NOT EXISTS (SELECT 1 FROM approval_forms WHERE code='DISBURSEMENT')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM approval_forms WHERE code='DISBURSEMENT'")
    op.execute("UPDATE approval_forms SET phase='NONE' WHERE code='PURCHASE'")
