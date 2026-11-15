"""v0.34.0 approval forms / references / attachments / leave

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-06-18

전자결재 v0.34.0:
- approval_forms 생성 + 5종 시드(FREE/PURCHASE/MEETING/TRIP/LEAVE)
- approval_documents.form_id 에 FK(approval_forms.id) 추가
- approval_references 생성(참조자 CC)
- approval_attachments 생성(첨부파일)
- users.annual_leave_days 추가(연 부여 연차)
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'j3k4l5m6n7o8'
down_revision: Union[str, None] = 'i2j3k4l5m6n7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 5종 양식 시드 정의 ----
_FORM_SEEDS = [
    {
        "code": "FREE",
        "name": "일반 기안서",
        "sort_order": 1,
        "fields_schema": [],
    },
    {
        "code": "PURCHASE",
        "name": "구매 신청서",
        "sort_order": 2,
        "fields_schema": [
            {"key": "item", "label": "품목", "type": "text", "required": True},
            {"key": "quantity", "label": "수량", "type": "number", "required": True},
            {"key": "unit_price", "label": "단가", "type": "number", "required": False},
            {"key": "vendor", "label": "거래처", "type": "text", "required": False},
            {"key": "reason", "label": "사유", "type": "textarea", "required": True},
        ],
    },
    {
        "code": "MEETING",
        "name": "회의록",
        "sort_order": 3,
        "fields_schema": [
            {"key": "meeting_at", "label": "일시", "type": "date", "required": True},
            {"key": "place", "label": "장소", "type": "text", "required": False},
            {"key": "attendees", "label": "참석자", "type": "text", "required": True},
            {"key": "agenda", "label": "안건", "type": "textarea", "required": True},
            {"key": "decisions", "label": "결정사항", "type": "textarea", "required": False},
        ],
    },
    {
        "code": "TRIP",
        "name": "출장 신청서",
        "sort_order": 4,
        "fields_schema": [
            {"key": "destination", "label": "출장지", "type": "text", "required": True},
            {"key": "start_date", "label": "시작일", "type": "date", "required": True},
            {"key": "end_date", "label": "종료일", "type": "date", "required": True},
            {"key": "purpose", "label": "목적", "type": "textarea", "required": True},
            {"key": "companions", "label": "동행자", "type": "text", "required": False},
            {"key": "transport", "label": "교통수단", "type": "text", "required": False},
            {"key": "expense", "label": "예상경비", "type": "number", "required": False},
        ],
    },
    {
        "code": "LEAVE",
        "name": "휴가 신청서",
        "sort_order": 5,
        "fields_schema": [
            {"key": "leave_type", "label": "휴가유형", "type": "select", "required": True,
             "options": ["연차", "반차", "병가", "경조", "기타"]},
            {"key": "start_date", "label": "시작일", "type": "date", "required": True},
            {"key": "end_date", "label": "종료일", "type": "date", "required": True},
            {"key": "days", "label": "일수", "type": "number", "required": True,
             "help": "연차/반차 기준 자동계산"},
            {"key": "reason", "label": "사유", "type": "textarea", "required": False},
            {"key": "substitute", "label": "대직자", "type": "text", "required": False},
        ],
    },
]


def upgrade() -> None:
    # ---- 1. approval_forms 생성 ----
    op.create_table(
        'approval_forms',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('code', sa.String(length=30), nullable=False, comment='양식 코드'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='양식 이름'),
        sa.Column('fields_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default='[]', comment='입력 필드 정의 배열'),
        sa.Column('default_line', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='기본 결재선 정의(선택)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='활성 여부'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment='정렬 순서'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.UniqueConstraint('code', name='uq_approval_forms_code'),
    )
    op.create_index('ix_approval_forms_code', 'approval_forms', ['code'])

    # ---- 2. approval_forms 5종 시드 INSERT ----
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
                "code": f["code"],
                "name": f["name"],
                "fields_schema": f["fields_schema"],
                "is_active": True,
                "sort_order": f["sort_order"],
            }
            for f in _FORM_SEEDS
        ],
    )

    # ---- 3. approval_documents.form_id 에 FK 추가 ----
    op.create_foreign_key(
        'fk_approval_documents_form_id',
        'approval_documents', 'approval_forms',
        ['form_id'], ['id'],
    )

    # ---- 4. approval_references 생성 ----
    op.create_table(
        'approval_references',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('approval_documents.id', ondelete='CASCADE'),
                  nullable=False, comment='문서 ID'),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=False, comment='참조 사용자'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.UniqueConstraint('document_id', 'user_id', name='uq_approval_references_doc_user'),
    )
    op.create_index('ix_approval_references_document_id', 'approval_references', ['document_id'])
    op.create_index('ix_approval_references_user_id', 'approval_references', ['user_id'])

    # ---- 5. approval_attachments 생성 ----
    op.create_table(
        'approval_attachments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('approval_documents.id', ondelete='CASCADE'),
                  nullable=False, comment='문서 ID'),
        sa.Column('original_name', sa.String(length=255), nullable=False, comment='원본 파일명'),
        sa.Column('stored_path', sa.String(length=500), nullable=False, comment='storage root 기준 상대 경로'),
        sa.Column('content_type', sa.String(length=120), nullable=True, comment='MIME 타입'),
        sa.Column('file_size', sa.BigInteger(), nullable=False, server_default='0', comment='파일 크기(bytes)'),
        sa.Column('uploaded_by', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=False, comment='업로더'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='업로드 시각'),
    )
    op.create_index('ix_approval_attachments_document_id', 'approval_attachments', ['document_id'])

    # ---- 6. users.annual_leave_days 추가 ----
    op.add_column('users',
        sa.Column('annual_leave_days', sa.Integer(), nullable=True,
                  server_default='15', comment='연 부여 연차 일수(v0.34.0)'))


def downgrade() -> None:
    # 역순 drop
    op.drop_column('users', 'annual_leave_days')

    op.drop_index('ix_approval_attachments_document_id', table_name='approval_attachments')
    op.drop_table('approval_attachments')

    op.drop_index('ix_approval_references_user_id', table_name='approval_references')
    op.drop_index('ix_approval_references_document_id', table_name='approval_references')
    op.drop_table('approval_references')

    op.drop_constraint('fk_approval_documents_form_id', 'approval_documents', type_='foreignkey')

    op.drop_index('ix_approval_forms_code', table_name='approval_forms')
    op.drop_table('approval_forms')
