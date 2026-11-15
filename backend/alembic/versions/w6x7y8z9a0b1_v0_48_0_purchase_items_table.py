"""v0.48.0 구매기안서/지출결의서 품목 표(items, 다품목) + 금액 자동합계

- PURCHASE: item/quantity/unit_price 단일 → items(표) 로 교체, amount=합계(자동)
- DISBURSEMENT: items(표) 추가(구매기안서에서 prefill 가능)
- items 행 구조: {name, qty, unit_price} (프론트에서 행 금액·합계 계산)

Revision ID: w6x7y8z9a0b1
Revises: v5w6x7y8z9a0
Create Date: 2026-06-22
"""
import json
from alembic import op


revision = "w6x7y8z9a0b1"
down_revision = "v5w6x7y8z9a0"
branch_labels = None
depends_on = None

_PURCHASE_FIELDS = [
    {"key": "items", "label": "품목", "type": "table", "required": True,
     "help": "행 추가로 여러 품목 입력 — 금액은 자동 합계"},
    {"key": "vendor", "label": "거래처", "type": "text", "required": False},
    {"key": "amount", "label": "금액(합계)", "type": "number", "required": False, "help": "품목 합계 자동"},
    {"key": "payment_method", "label": "결제방법", "type": "select", "required": True,
     "options": ["현금-선결제", "익월결제", "카드결제"]},
    {"key": "execution_condition", "label": "집행조건", "type": "select", "required": True,
     "options": ["검수완료 후", "선집행", "익월", "지정일"], "help": "자금 집행 시점 기준"},
    {"key": "planned_exec_date", "label": "집행 예정일", "type": "date", "required": False,
     "help": "집행조건이 지정일일 때 입력"},
    {"key": "reason", "label": "사유", "type": "textarea", "required": False},
]

_DISBURSEMENT_FIELDS = [
    {"key": "vendor", "label": "거래처", "type": "text", "required": False},
    {"key": "items", "label": "품목", "type": "table", "required": False,
     "help": "구매기안서에서 자동 복사 — 행 추가/수정 가능"},
    {"key": "amount", "label": "청구 금액", "type": "number", "required": False, "help": "품목 합계 자동(직접 입력도 가능)"},
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
    pf = json.dumps(_PURCHASE_FIELDS, ensure_ascii=False).replace("'", "''")
    df = json.dumps(_DISBURSEMENT_FIELDS, ensure_ascii=False).replace("'", "''")
    op.execute(f"UPDATE approval_forms SET fields_schema='{pf}'::jsonb WHERE code='PURCHASE'")
    op.execute(f"UPDATE approval_forms SET fields_schema='{df}'::jsonb WHERE code='DISBURSEMENT'")


def downgrade() -> None:
    # v0.46.0 단일 품목 스키마로 되돌림(간략 — items 제거)
    prev_purchase = [
        {"key": "item", "label": "품목", "type": "text", "required": True},
        {"key": "quantity", "label": "수량", "type": "number", "required": True},
        {"key": "unit_price", "label": "단가", "type": "number", "required": False},
        {"key": "amount", "label": "금액(합계)", "type": "number", "required": True},
        {"key": "vendor", "label": "거래처", "type": "text", "required": False},
        {"key": "payment_method", "label": "결제방법", "type": "select", "required": True,
         "options": ["현금-선결제", "익월결제", "카드결제"]},
        {"key": "execution_condition", "label": "집행조건", "type": "select", "required": True,
         "options": ["검수완료 후", "선집행", "익월", "지정일"]},
        {"key": "planned_exec_date", "label": "집행 예정일", "type": "date", "required": False},
        {"key": "reason", "label": "사유", "type": "textarea", "required": False},
    ]
    pf = json.dumps(prev_purchase, ensure_ascii=False).replace("'", "''")
    op.execute(f"UPDATE approval_forms SET fields_schema='{pf}'::jsonb WHERE code='PURCHASE'")
