"""자유게시판 (글/댓글)

2개 테이블:
- free_board_posts: 글 1건(분류/제목/본문 HTML/익명 여부/조회수/소프트삭제).
- free_board_comments: 댓글(parent_id 자기참조로 1단계 답글, FK CASCADE).

익명 글·댓글도 author_id 는 저장한다(본인 수정/삭제 판정용). API 응답에서만 가린다.

Revision ID: xm_v1020_free_board
Revises: xm_v1010_appr_min
"""
from alembic import op
import sqlalchemy as sa

revision = "xm_v1020_free_board"
down_revision = "xm_v1010_appr_min"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "free_board_posts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_anonymous", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("view_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "category IN ('CHAT', 'SUGGESTION', 'COMPLAINT', 'HEART')",
            name="ck_free_board_posts_category",
        ),
    )
    op.create_index("ix_free_board_posts_id", "free_board_posts", ["id"])
    op.create_index("ix_free_board_posts_category", "free_board_posts", ["category"])
    op.create_index("ix_free_board_posts_author_id", "free_board_posts", ["author_id"])
    op.create_index("ix_free_board_posts_is_active", "free_board_posts", ["is_active"])
    op.create_index("ix_free_board_posts_created_at", "free_board_posts", ["created_at"])
    op.create_index("ix_free_board_posts_active_created", "free_board_posts",
                    ["is_active", "created_at"])
    op.create_index("ix_free_board_posts_active_cat_created", "free_board_posts",
                    ["is_active", "category", "created_at"])

    op.create_table(
        "free_board_comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("post_id", sa.Integer,
                  sa.ForeignKey("free_board_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.Integer,
                  sa.ForeignKey("free_board_comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_anonymous", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_free_board_comments_id", "free_board_comments", ["id"])
    op.create_index("ix_free_board_comments_post_id", "free_board_comments", ["post_id"])
    op.create_index("ix_free_board_comments_parent_id", "free_board_comments", ["parent_id"])
    op.create_index("ix_free_board_comments_author_id", "free_board_comments", ["author_id"])
    op.create_index("ix_free_board_comments_post_created", "free_board_comments",
                    ["post_id", "created_at"])


def downgrade() -> None:
    op.drop_table("free_board_comments")
    op.drop_table("free_board_posts")
