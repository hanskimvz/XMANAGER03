"""v0.82.0 거래처 기본 DESTINATION(도착지)

Revision ID: xm_v0820_default_dest
Revises: xm_v0810_nc_folder
Create Date: 2026-08-04

거래처(고객사)에 기본 DESTINATION 추가 — 생산요청서 작성 시 자동 채움.
default_shipping_mark / default_consignee 와 동일 패턴.
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0820_default_dest"
down_revision = "xm_v0810_nc_folder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("business_partner", sa.Column("default_destination", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("business_partner", "default_destination")
