"""v0.55.0 결재 관련 문서 다중 연결 (related_document_ids)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-06

지출결의서 등에서 관련 구매기안서를 여러 개 걸 수 있도록 approval_documents 에
related_document_ids(JSONB int 배열) 추가. 기존 단일 related_document_id 값은
[id] 형태로 백필하여 하위호환 유지.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("approval_documents", sa.Column("related_document_ids", JSONB(), nullable=True))
    # 기존 단일 연결을 배열로 백필
    op.execute("""
        UPDATE approval_documents
        SET related_document_ids = jsonb_build_array(related_document_id)
        WHERE related_document_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column("approval_documents", "related_document_ids")
