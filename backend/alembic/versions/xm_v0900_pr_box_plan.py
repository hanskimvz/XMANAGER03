"""v0.90.0 생산요청 분할선적 박스 분할계획(box_plan)

Revision ID: xm_v0900_pr_box_plan
Revises: xm_v0890_incoterms_freight
Create Date: 2026-08-14

영업이 생산요청서에 "N개씩 M박스"로 박스 분할계획을 작성 → 생산팀이 보고 포장 →
영업이 박스별로 CI(1박스=1CI)를 발행할 때 사용.
box_plan: [{box_no, items:[{pr_item_id, quantity}], remarks}]
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0900_pr_box_plan"
down_revision = "xm_v0890_incoterms_freight"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_request", sa.Column("box_plan", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("production_request", "box_plan")
