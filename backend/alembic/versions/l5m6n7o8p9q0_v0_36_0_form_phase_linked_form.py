"""v0.36.0 form phase / linked form (단계형 사전→사후 문서 연계)

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-06-19

전자결재 v0.36.0:
- approval_forms.phase 추가 — 절차 단계(NONE/PRE/POST)를 양식 정의로 구분
- approval_forms.linked_form_code 추가 — 사후(POST) 양식이 짝이 되는 사전(PRE) 양식 code
- 기존 양식 단계 부여: TRIP→PRE, EXPENSE→POST(linked_form_code=TRIP),
  나머지(FREE/PURCHASE/MEETING/LEAVE)는 NONE 유지
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'l5m6n7o8p9q0'
down_revision: Union[str, None] = 'k4l5m6n7o8p9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- 1. approval_forms 컬럼 2종 추가 ----
    op.add_column(
        'approval_forms',
        sa.Column('phase', sa.String(length=10), nullable=False, server_default='NONE',
                  comment='절차 단계: 단독/사전/사후'),
    )
    op.add_column(
        'approval_forms',
        sa.Column('linked_form_code', sa.String(length=30), nullable=True,
                  comment='사후(POST) 양식이 짝이 되는 사전(PRE) 양식 code'),
    )

    # ---- 2. 기존 양식 단계 부여 ----
    op.execute("UPDATE approval_forms SET phase = 'PRE' WHERE code = 'TRIP'")
    op.execute(
        "UPDATE approval_forms SET phase = 'POST', linked_form_code = 'TRIP' "
        "WHERE code = 'EXPENSE'"
    )
    # 나머지(FREE/PURCHASE/MEETING/LEAVE)는 server_default 'NONE' 유지


def downgrade() -> None:
    op.drop_column('approval_forms', 'linked_form_code')
    op.drop_column('approval_forms', 'phase')
