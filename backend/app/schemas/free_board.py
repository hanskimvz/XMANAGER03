"""자유게시판 스키마 (v1.02.0).

익명 글·댓글은 응답에 작성자 id 를 싣지 않는다 — author_name 은 None, 본인 여부는 is_mine 으로만 전달.
"""
from typing import List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field

FreeBoardCategory = Literal["CHAT", "SUGGESTION", "COMPLAINT", "HEART"]

# 본문에 base64 이미지가 들어가므로 넉넉히 잡되 상한은 둔다(약 10MB)
_BODY_MAX = 10_000_000


# ==================== 입력 ====================

class PostCreate(BaseModel):
    category: FreeBoardCategory = Field(..., description="분류 코드")
    title: str = Field(..., min_length=1, max_length=300, description="제목")
    body: str = Field(..., min_length=1, max_length=_BODY_MAX, description="본문 HTML(TipTap)")
    is_anonymous: bool = Field(False, description="익명으로 작성")


class PostUpdate(BaseModel):
    """부분 수정 — 보낸 필드만 갱신."""
    category: Optional[FreeBoardCategory] = None
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    body: Optional[str] = Field(None, min_length=1, max_length=_BODY_MAX)
    is_anonymous: Optional[bool] = None


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="댓글 내용(텍스트)")
    is_anonymous: bool = Field(False, description="익명으로 작성")
    parent_id: Optional[int] = Field(None, description="답글이면 부모 댓글 id")


# ==================== 출력 ====================

class CommentResponse(BaseModel):
    id: int
    parent_id: Optional[int] = None
    content: str  # 삭제된 댓글은 빈 문자열
    is_anonymous: bool
    author_name: Optional[str] = None  # 익명/삭제 시 None
    is_post_author: bool = False       # 글쓴이가 단 댓글
    is_mine: bool = False
    can_delete: bool = False
    is_deleted: bool = False
    created_at: datetime


class PostListItem(BaseModel):
    id: int
    category: FreeBoardCategory
    title: str
    is_anonymous: bool
    author_name: Optional[str] = None  # 익명이면 None
    is_mine: bool = False
    view_count: int = 0
    comment_count: int = 0
    created_at: datetime


class PostListResponse(BaseModel):
    items: List[PostListItem]
    total: int
    page: int
    size: int


class PostDetail(BaseModel):
    id: int
    category: FreeBoardCategory
    title: str
    body: str
    is_anonymous: bool
    author_name: Optional[str] = None
    is_mine: bool = False
    can_edit: bool = False    # 본인만
    can_delete: bool = False  # 본인 또는 관리자
    view_count: int = 0
    comment_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    comments: List[CommentResponse] = []
