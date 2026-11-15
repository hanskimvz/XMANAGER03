"""전자결재 기록 시각을 분 단위로 통일 (초/마이크로초 절사)

문서 표시·인쇄는 모두 분 단위인데 저장은 초까지 들어가 있어,
시각 비교·정정 시 초 단위 잔차 때문에 값이 어긋나 보이는 문제가 있었다.
**앞으로** 기록되는 시각은 분 단위까지만 남긴다.

이 마이그레이션은 DB 기본값만 바꾼다(now() -> date_trunc('minute', now())).
애플리케이션 쪽은 ApprovalService._now() / models.approval.minute_now() 가 담당.

기존 데이터는 건드리지 않는다(과거 기록 보존). 이미 쌓인 행의 초까지 맞추려면
아래 SQL 을 별도로 실행한다 — 표시값은 바뀌지 않고 초만 0 이 된다:

    UPDATE approval_documents SET created_at = date_trunc('minute', created_at),
                                  updated_at = date_trunc('minute', updated_at),
                                  drafted_at = date_trunc('minute', drafted_at),
                                  completed_at = date_trunc('minute', completed_at);
    UPDATE approval_lines   SET acted_at    = date_trunc('minute', acted_at);
    UPDATE approval_actions SET acted_at    = date_trunc('minute', acted_at);

Revision ID: xm_v1010_appr_min
Revises: xm_v1000_disb_cols
"""
from alembic import op

revision = "xm_v1010_appr_min"
down_revision = "xm_v1000_disb_cols"
branch_labels = None
depends_on = None


# 기본값이 now() 로 걸려 있어 분 단위로 바꿔야 하는 컬럼
_DEFAULTED = [
    ("approval_documents", "created_at"),
    ("approval_documents", "updated_at"),
    ("approval_actions", "acted_at"),
    ("approval_attachments", "uploaded_at"),
]


def _col_exists(table: str, column: str) -> bool:
    return bool(op.get_bind().exec_driver_sql(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    ).scalar())


def upgrade() -> None:
    for table, column in _DEFAULTED:
        if _col_exists(table, column):
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {column} "
                f"SET DEFAULT date_trunc('minute', now())"
            )


def downgrade() -> None:
    for table, column in _DEFAULTED:
        if _col_exists(table, column):
            op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT now()")
