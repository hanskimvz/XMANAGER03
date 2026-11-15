"""
자유게시판 (v1.02.0)

- free_board_posts: 글 1건(분류/제목/본문 HTML/익명 여부/조회수/소프트삭제).
- free_board_comments: 댓글. parent_id 로 1단계 답글(대댓글)을 표현한다.

익명 처리:
  author_id 는 익명 글·댓글에도 **항상 저장**한다(본인 수정/삭제 판정에 필요).
  대신 API 응답에서는 익명이면 작성자 id·이름을 내보내지 않고 is_mine 만 내려준다.
  → 화면/API 로는 작성자를 알 수 없지만, DB 를 직접 조회하면 알 수 있다.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

# 분류 코드 -> 한글 라벨 (프런트 api/freeBoard.ts 의 FREE_BOARD_CATEGORIES 와 동일하게 유지)
FREE_BOARD_CATEGORIES = {
    "CHAT": "잡담",
    "SUGGESTION": "건의",
    "COMPLAINT": "불만",
    "HEART": "속마음",
}


class FreeBoardPost(Base):
    """자유게시판 글 1건."""
    __tablename__ = "free_board_posts"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(20), nullable=False, index=True,
                      comment="분류 코드(CHAT 잡담/SUGGESTION 건의/COMPLAINT 불만/HEART 속마음)")
    title = Column(String(300), nullable=False, comment="제목")
    body = Column(Text, nullable=False, comment="본문 HTML(TipTap 산출물, 서버 sanitize 후 저장)")
    is_anonymous = Column(Boolean, nullable=False, default=False, server_default="false",
                          comment="익명 글 여부(True 면 응답에서 작성자 정보 제외)")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True,
                       comment="작성자(익명 글도 저장 — 본인 수정/삭제 판정용)")
    view_count = Column(Integer, nullable=False, default=0, server_default="0", comment="조회수")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true",
                       index=True, comment="활성(소프트 삭제 플래그)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    comments = relationship(
        "FreeBoardComment", back_populates="post",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ('CHAT', 'SUGGESTION', 'COMPLAINT', 'HEART')",
            name="ck_free_board_posts_category",
        ),
        # 목록: 활성 글을 최신순으로(분류 필터 포함)
        Index("ix_free_board_posts_active_created", "is_active", "created_at"),
        Index("ix_free_board_posts_active_cat_created", "is_active", "category", "created_at"),
    )


class FreeBoardComment(Base):
    """자유게시판 댓글. parent_id 가 있으면 그 댓글의 답글(1단계만 허용 — 서비스에서 검증)."""
    __tablename__ = "free_board_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer, ForeignKey("free_board_posts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    parent_id = Column(
        Integer, ForeignKey("free_board_comments.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="답글이면 부모 댓글 id",
    )
    content = Column(Text, nullable=False, comment="댓글 내용(순수 텍스트)")
    is_anonymous = Column(Boolean, nullable=False, default=False, server_default="false",
                          comment="익명 댓글 여부")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True,
                       comment="작성자(익명 댓글도 저장)")
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="false",
                        comment="삭제됨(답글이 달린 댓글은 행을 남기고 내용만 가린다)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    post = relationship("FreeBoardPost", back_populates="comments")

    __table_args__ = (
        Index("ix_free_board_comments_post_created", "post_id", "created_at"),
    )
