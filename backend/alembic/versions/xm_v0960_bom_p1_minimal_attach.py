"""v0.96.0 BOM 개편 P1 — 미분류 부품(is_classified) + 부품 첨부(part_attachment)

Revision ID: xm_v0960_bom_p1
Revises: xm_v0950_statement_of_origin
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v0960_bom_p1"
down_revision = "xm_v0950_statement_of_origin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parts", sa.Column(
        "is_classified", sa.Boolean(), nullable=False, server_default="true"))
    op.create_index("ix_parts_is_classified", "parts", ["is_classified"])

    op.create_table(
        "part_attachment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("part_id", sa.Integer(), sa.ForeignKey("parts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="OTHER"),
        sa.Column("filename", sa.String(length=300), nullable=False),
        sa.Column("filepath", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_part_attachment_part_id", "part_attachment", ["part_id"])


def downgrade() -> None:
    op.drop_index("ix_part_attachment_part_id", table_name="part_attachment")
    op.drop_table("part_attachment")
    op.drop_index("ix_parts_is_classified", table_name="parts")
    op.drop_column("parts", "is_classified")
