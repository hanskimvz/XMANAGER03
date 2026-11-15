"""v0.38.0 projects master 공용화 (approval_projects -> projects)

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-06-19

전자결재 v0.38.0:
- 전자결재 전용이던 프로젝트 마스터를 전사 공용 도메인으로 일반화.
- approval_projects 테이블을 projects 로 rename (데이터/시드 보존).
- approval_documents.project_id FK 는 테이블 객체 참조라 rename 후에도 유효 — 변경 불필요.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'n7o8p9q0r1s2'
down_revision: Union[str, None] = 'm6n7o8p9q0r1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # approval_projects -> projects 로 rename (데이터/시드/FK 보존)
    op.rename_table('approval_projects', 'projects')


def downgrade() -> None:
    op.rename_table('projects', 'approval_projects')
