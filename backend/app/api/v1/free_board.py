"""
자유게시판 API (v1.02.0)

A 예외 라우터: 자체 인증(require_auth) — 로그인한 전 직원이 열람/작성.
- 수정: 작성자 본인만. 삭제: 작성자 본인 또는 관리자(ADMIN).
- 익명 글·댓글은 응답에 작성자 정보를 싣지 않는다(본인 여부는 is_mine).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_auth
from app.models.user import User
from app.schemas.free_board import (
    FreeBoardCategory, PostCreate, PostUpdate, CommentCreate,
    PostListResponse, PostDetail,
)
from app.services import free_board_service as svc

router = APIRouter(prefix="/free-board", tags=["자유게시판"])


@router.get("", response_model=PostListResponse)
def list_posts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[FreeBoardCategory] = Query(None, description="분류 코드"),
    q: Optional[str] = Query(None, description="제목 검색"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return svc.list_posts(db, user, page, size, category, q)


@router.get("/{post_id}", response_model=PostDetail)
def get_post(
    post_id: int,
    count_view: bool = Query(True, description="조회수 증가 여부(댓글 등록 후 재조회 시 false)"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    post = svc.get_post(db, post_id)
    if count_view:
        svc.increase_view(db, post)
    return svc.to_detail(db, post, user)


@router.post("", response_model=PostDetail, status_code=201)
def create_post(payload: PostCreate, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    post = svc.create_post(db, user, payload)
    return svc.to_detail(db, post, user)


@router.put("/{post_id}", response_model=PostDetail)
def update_post(post_id: int, payload: PostUpdate,
                user: User = Depends(require_auth), db: Session = Depends(get_db)):
    post = svc.update_post(db, user, svc.get_post(db, post_id), payload)
    return svc.to_detail(db, post, user)


@router.delete("/{post_id}", status_code=204)
def delete_post(post_id: int, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    svc.delete_post(db, user, svc.get_post(db, post_id))


# ==================== 댓글 ====================

@router.post("/{post_id}/comments", response_model=PostDetail, status_code=201)
def add_comment(post_id: int, payload: CommentCreate,
                user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """댓글 등록 후 갱신된 글 상세(댓글 목록 포함)를 돌려준다."""
    post = svc.get_post(db, post_id)
    svc.add_comment(db, user, post, payload)
    return svc.to_detail(db, post, user)


@router.delete("/{post_id}/comments/{comment_id}", response_model=PostDetail)
def delete_comment(post_id: int, comment_id: int,
                   user: User = Depends(require_auth), db: Session = Depends(get_db)):
    post = svc.get_post(db, post_id)
    svc.delete_comment(db, user, post, comment_id)
    return svc.to_detail(db, post, user)
