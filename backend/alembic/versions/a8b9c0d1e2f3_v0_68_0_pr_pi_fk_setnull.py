"""v0.68.0 생산요청 품목의 PI FK를 ON DELETE SET NULL 로 변경

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-07-27

DRAFT PI를 수정하면 품목을 삭제·재생성하는데, 그 품목을 참조하는 생산요청이 있으면
기존 NO ACTION FK 때문에 삭제가 IntegrityError 로 막혔다. SET NULL 로 바꿔
링크만 NULL 로 떨어뜨리고(잔여수량은 pi_number 폴백으로 복구) 편집이 실패하지 않게 한다.
"""
from alembic import op

revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

TABLE = "production_request_item"


def upgrade() -> None:
    op.drop_constraint("production_request_item_pi_document_id_fkey", TABLE, type_="foreignkey")
    op.create_foreign_key(
        "production_request_item_pi_document_id_fkey", TABLE, "sales_document",
        ["pi_document_id"], ["id"], ondelete="SET NULL",
    )
    op.drop_constraint("production_request_item_pi_item_id_fkey", TABLE, type_="foreignkey")
    op.create_foreign_key(
        "production_request_item_pi_item_id_fkey", TABLE, "sales_document_item",
        ["pi_item_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("production_request_item_pi_document_id_fkey", TABLE, type_="foreignkey")
    op.create_foreign_key(
        "production_request_item_pi_document_id_fkey", TABLE, "sales_document",
        ["pi_document_id"], ["id"],
    )
    op.drop_constraint("production_request_item_pi_item_id_fkey", TABLE, type_="foreignkey")
    op.create_foreign_key(
        "production_request_item_pi_item_id_fkey", TABLE, "sales_document_item",
        ["pi_item_id"], ["id"],
    )
