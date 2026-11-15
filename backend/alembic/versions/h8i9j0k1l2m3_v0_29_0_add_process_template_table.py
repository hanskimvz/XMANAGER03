"""v0.29.0 add process_template table with seed data

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-04-06

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


revision: str = 'h8i9j0k1l2m3'
down_revision: str = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'process_template',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('template_name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('steps', sa.JSON(), server_default='[]'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # 기본 공정 템플릿 시드
    templates = [
        {
            "name": "커넥터 조립 (기본)",
            "desc": "인서트 → 조립 → 검사/포장",
            "steps": [
                {"task_name": "인서트 작업", "assigned_team": "인서트팀", "sort_order": 0},
                {"task_name": "조립", "assigned_team": "조립팀", "sort_order": 1},
                {"task_name": "검사/포장", "assigned_team": "품질팀", "sort_order": 2},
            ]
        },
        {
            "name": "커넥터 조립 (가공 포함)",
            "desc": "인서트 → K-1 가공 → 조립 → 검사/포장",
            "steps": [
                {"task_name": "인서트 작업", "assigned_team": "인서트팀", "sort_order": 0},
                {"task_name": "K-1 가공", "assigned_team": "가공팀", "sort_order": 1},
                {"task_name": "조립", "assigned_team": "조립팀", "sort_order": 2},
                {"task_name": "검사/포장", "assigned_team": "품질팀", "sort_order": 3},
            ]
        },
        {
            "name": "케이블 조립체",
            "desc": "인서트 → K-1 가공 → 조립 → 케이블 작업 → 검사/포장",
            "steps": [
                {"task_name": "인서트 작업", "assigned_team": "인서트팀", "sort_order": 0},
                {"task_name": "K-1 가공", "assigned_team": "가공팀", "sort_order": 1},
                {"task_name": "조립", "assigned_team": "조립팀", "sort_order": 2},
                {"task_name": "케이블 작업", "assigned_team": "조립팀", "sort_order": 3},
                {"task_name": "검사/포장", "assigned_team": "품질팀", "sort_order": 4},
            ]
        },
        {
            "name": "Kit (부품만)",
            "desc": "가공 → 검사 → 포장",
            "steps": [
                {"task_name": "가공", "assigned_team": "가공팀", "sort_order": 0},
                {"task_name": "검사", "assigned_team": "품질팀", "sort_order": 1},
                {"task_name": "포장", "assigned_team": "포장팀", "sort_order": 2},
            ]
        },
    ]

    for t in templates:
        op.execute(
            sa.text(
                "INSERT INTO process_template (template_name, description, steps) "
                "VALUES (:name, :desc, :steps)"
            ).bindparams(
                name=t["name"],
                desc=t["desc"],
                steps=json.dumps(t["steps"]),
            )
        )


def downgrade() -> None:
    op.drop_table('process_template')
