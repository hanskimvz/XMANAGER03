"""v0.47.0 모듈별 RBAC enforce 토글 (rbac_module_policy)

- rbac_module_policy: module(PK) / enforced / updated_at
- 전역 RBAC_MODE 와 별개로 모듈 단위 권한 강제 on/off(관리자 UI).

Revision ID: v5w6x7y8z9a0
Revises: u4v5w6x7y8z9
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa


revision = "v5w6x7y8z9a0"
down_revision = "u4v5w6x7y8z9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rbac_module_policy",
        sa.Column("module", sa.String(length=30), primary_key=True),
        sa.Column("enforced", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("rbac_module_policy")
