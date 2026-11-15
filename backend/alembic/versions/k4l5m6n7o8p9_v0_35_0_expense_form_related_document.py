"""v0.35.0 expense form / related document link

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-06-19

전자결재 v0.35.0:
- approval_documents.related_document_id 추가(self-FK) — 정산서→출장신청서 등 문서 연결
- approval_forms 에 EXPENSE(출장 정산서) 양식 1종 시드
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'k4l5m6n7o8p9'
down_revision: Union[str, None] = 'j3k4l5m6n7o8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- EXPENSE 양식 시드 정의 (fields_schema 는 파이썬 list 그대로 — json.dumps 금지) ----
_EXPENSE_FORM = {
    "code": "EXPENSE",
    "name": "출장 정산서",
    "sort_order": 6,
    "fields_schema": [
        {"key": "result_summary", "label": "결과 요약", "type": "textarea", "required": True},
        {"key": "actual_start", "label": "실제 시작일", "type": "date", "required": False},
        {"key": "actual_end", "label": "실제 종료일", "type": "date", "required": False},
        {"key": "transport_cost", "label": "교통비", "type": "number", "required": False},
        {"key": "lodging_cost", "label": "숙박비", "type": "number", "required": False},
        {"key": "meal_cost", "label": "식대", "type": "number", "required": False},
        {"key": "etc_cost", "label": "기타비용", "type": "number", "required": False},
        {"key": "total_cost", "label": "합계", "type": "number", "required": True,
         "help": "항목 합계 자동"},
        {"key": "note", "label": "비고", "type": "textarea", "required": False},
    ],
}


def upgrade() -> None:
    # ---- 1. approval_documents.related_document_id 추가(self-FK) ----
    op.add_column(
        'approval_documents',
        sa.Column('related_document_id', sa.Integer(), nullable=True,
                  comment='관련 문서(정산서→출장신청서 등)'),
    )
    op.create_foreign_key(
        'fk_approval_documents_related_document_id',
        'approval_documents', 'approval_documents',
        ['related_document_id'], ['id'],
    )

    # ---- 2. EXPENSE 양식 시드 INSERT (fields_schema 는 파이썬 list 그대로) ----
    forms_table = sa.table(
        'approval_forms',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('fields_schema', postgresql.JSONB(astext_type=sa.Text())),
        sa.column('is_active', sa.Boolean),
        sa.column('sort_order', sa.Integer),
    )
    op.bulk_insert(
        forms_table,
        [
            {
                "code": _EXPENSE_FORM["code"],
                "name": _EXPENSE_FORM["name"],
                "fields_schema": _EXPENSE_FORM["fields_schema"],
                "is_active": True,
                "sort_order": _EXPENSE_FORM["sort_order"],
            }
        ],
    )


def downgrade() -> None:
    # ---- EXPENSE 양식 삭제 ----
    op.execute("DELETE FROM approval_forms WHERE code = 'EXPENSE'")

    # ---- related_document_id FK/컬럼 drop ----
    op.drop_constraint(
        'fk_approval_documents_related_document_id',
        'approval_documents', type_='foreignkey',
    )
    op.drop_column('approval_documents', 'related_document_id')
