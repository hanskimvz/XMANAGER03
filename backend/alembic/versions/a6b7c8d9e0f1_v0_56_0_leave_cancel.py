"""v0.56.0 휴가 취소 기능 (휴가취소 신청서 + 원장 무효화)

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-06

- leave_ledger.voided 추가: 취소된 휴가의 USAGE 행을 삭제하지 않고 무효 처리
  (잔여 합산에서 제외 + 거래원장에 빗금 표시로 감사 보존)
- LEAVE(휴가 신청서) phase NONE→PRE: 승인된 휴가에 '후속 작성(휴가취소)' 버튼 노출
- LEAVE_CANCEL(휴가취소 신청서) 신규: phase POST, linked_form_code=LEAVE
  → 관련문서로 원 휴가 신청서를 걸고, 승인 시 원 USAGE 무효화(일수 복구)
"""
import json
from alembic import op
import sqlalchemy as sa

revision = "a6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None

_CANCEL_FIELDS = [
    {"key": "reason", "label": "취소 사유", "type": "textarea", "required": True,
     "help": "휴가 취소 사유를 입력하세요"},
]


def upgrade() -> None:
    # 1) 원장 무효화 컬럼
    op.add_column("leave_ledger",
                  sa.Column("voided", sa.Boolean(), nullable=False, server_default="false"))
    # 2) 휴가 신청서를 PRE 로 승격(후속 취소 신청 연결용)
    op.execute("UPDATE approval_forms SET phase='PRE' WHERE code='LEAVE'")
    # 3) 휴가취소 신청서 양식 삽입(없을 때만)
    cf = json.dumps(_CANCEL_FIELDS, ensure_ascii=False).replace("'", "''")
    op.execute(
        "INSERT INTO approval_forms (code, name, fields_schema, phase, linked_form_code, is_active, sort_order) "
        f"SELECT 'LEAVE_CANCEL', '휴가취소 신청서', '{cf}'::jsonb, 'POST', 'LEAVE', true, 12 "
        "WHERE NOT EXISTS (SELECT 1 FROM approval_forms WHERE code='LEAVE_CANCEL')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM approval_forms WHERE code='LEAVE_CANCEL'")
    op.execute("UPDATE approval_forms SET phase='NONE' WHERE code='LEAVE'")
    op.drop_column("leave_ledger", "voided")
