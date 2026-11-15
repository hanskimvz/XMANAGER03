"""v0.39.0 meeting expense form (multi followup)

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
Create Date: 2026-06-19

전자결재 v0.39.0:
- MEETING_EXPENSE(회의비 정산서, POST) 신규 시드 — linked_form_code=MEETING_PLAN.
  → MEETING_PLAN(PRE) 의 후속이 MEETING(회의록) + MEETING_EXPENSE 2개가 됨(후속 리스트화).
- fields_schema 는 파이썬 list 그대로(json.dumps 금지 / 이중 인코딩 금지).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'o8p9q0r1s2t3'
down_revision: Union[str, None] = 'n7o8p9q0r1s2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 회의비 정산서(POST) 양식 시드 — fields_schema 는 파이썬 list 그대로 ----
_MEETING_EXPENSE_FIELDS = [
    {"key": "result_summary", "label": "회의 결과 요약", "type": "textarea", "required": True},
    {"key": "venue_cost", "label": "장소/대관비", "type": "number", "required": False},
    {"key": "refreshment_cost", "label": "다과/식대", "type": "number", "required": False},
    {"key": "etc_cost", "label": "기타비용", "type": "number", "required": False},
    {"key": "total_cost", "label": "합계", "type": "number", "required": True,
     "help": "비용 항목 합계 자동"},
    {"key": "note", "label": "비고", "type": "textarea", "required": False},
]


def upgrade() -> None:
    forms_table = sa.table(
        'approval_forms',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('fields_schema', postgresql.JSONB(astext_type=sa.Text())),
        sa.column('phase', sa.String),
        sa.column('linked_form_code', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('sort_order', sa.Integer),
    )
    op.bulk_insert(
        forms_table,
        [
            {
                "code": "MEETING_EXPENSE",
                "name": "회의비 정산서",
                "fields_schema": _MEETING_EXPENSE_FIELDS,
                "phase": "POST",
                "linked_form_code": "MEETING_PLAN",
                "is_active": True,
                "sort_order": 8,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM approval_forms WHERE code = 'MEETING_EXPENSE'")
