"""v0.37.0 meeting phase / projects master / document project_id

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0
Create Date: 2026-06-19

전자결재 v0.37.0:
- 회의 단계형: MEETING_PLAN(회의 안건서, PRE) 신규 시드 + 기존 MEETING(회의록)을 POST 로 전환(linked_form_code=MEETING_PLAN)
- 프로젝트 마스터: approval_projects 신규 테이블 + 4종 시드(COMMON/DEV/MASS/SALES)
- approval_documents.project_id 추가 + FK(approval_projects.id)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'm6n7o8p9q0r1'
down_revision: Union[str, None] = 'l5m6n7o8p9q0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 회의 안건서(PRE) 양식 시드 — fields_schema 는 파이썬 list 그대로(json.dumps 금지) ----
_MEETING_PLAN_FIELDS = [
    {"key": "meeting_title", "label": "회의명", "type": "text", "required": True},
    {"key": "meeting_at", "label": "일시", "type": "date", "required": True},
    {"key": "place", "label": "장소", "type": "text", "required": False},
    {"key": "attendees", "label": "참석 예정자", "type": "text", "required": True},
    {"key": "agenda", "label": "안건", "type": "textarea", "required": True},
    {"key": "purpose", "label": "목적", "type": "textarea", "required": False},
]

# ---- 프로젝트 마스터 시드(관리자가 이후 편집/추가) ----
_PROJECT_SEEDS = [
    {"code": "COMMON", "name": "공통/일반", "sort_order": 0},
    {"code": "DEV", "name": "신규 개발", "sort_order": 1},
    {"code": "MASS", "name": "양산", "sort_order": 2},
    {"code": "SALES", "name": "영업/수출", "sort_order": 3},
]


def upgrade() -> None:
    # ---- 1. 회의 단계형 ----
    # 1-1. MEETING_PLAN(회의 안건서, PRE) 신규 시드
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
                "code": "MEETING_PLAN",
                "name": "회의 안건서",
                "fields_schema": _MEETING_PLAN_FIELDS,
                "phase": "PRE",
                "linked_form_code": None,
                "is_active": True,
                "sort_order": 7,
            }
        ],
    )

    # 1-2. 기존 MEETING(회의록) → POST + linked_form_code=MEETING_PLAN
    op.execute(
        "UPDATE approval_forms SET phase = 'POST', linked_form_code = 'MEETING_PLAN' "
        "WHERE code = 'MEETING'"
    )

    # ---- 2. 프로젝트 마스터 ----
    op.create_table(
        'approval_projects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, comment='ID'),
        sa.Column('code', sa.String(length=30), nullable=False, comment='프로젝트 코드'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='프로젝트 이름'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='활성 여부'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment='정렬 순서'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.UniqueConstraint('code', name='uq_approval_projects_code'),
    )
    op.create_index('ix_approval_projects_code', 'approval_projects', ['code'])

    projects_table = sa.table(
        'approval_projects',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('sort_order', sa.Integer),
    )
    op.bulk_insert(
        projects_table,
        [
            {
                "code": p["code"],
                "name": p["name"],
                "is_active": True,
                "sort_order": p["sort_order"],
            }
            for p in _PROJECT_SEEDS
        ],
    )

    # ---- 3. approval_documents.project_id + FK ----
    op.add_column(
        'approval_documents',
        sa.Column('project_id', sa.Integer(), nullable=True, comment='프로젝트'),
    )
    op.create_foreign_key(
        'fk_approval_documents_project_id',
        'approval_documents', 'approval_projects',
        ['project_id'], ['id'],
    )


def downgrade() -> None:
    # ---- 3. project_id FK/컬럼 drop ----
    op.drop_constraint('fk_approval_documents_project_id', 'approval_documents', type_='foreignkey')
    op.drop_column('approval_documents', 'project_id')

    # ---- 2. approval_projects drop ----
    op.drop_index('ix_approval_projects_code', table_name='approval_projects')
    op.drop_table('approval_projects')

    # ---- 1. 회의 단계형 원복 ----
    op.execute("DELETE FROM approval_forms WHERE code = 'MEETING_PLAN'")
    op.execute(
        "UPDATE approval_forms SET phase = 'NONE', linked_form_code = NULL "
        "WHERE code = 'MEETING'"
    )
