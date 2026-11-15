"""자유게시판 서비스 (v1.02.0).

- 열람/작성: 로그인한 전 직원.
- 수정: 작성자 본인만. 삭제: 작성자 본인 또는 관리자(ADMIN — 게시판 관리 목적).
- 익명: author_id 는 저장하되 응답에는 작성자 id·이름을 싣지 않는다(관리자에게도 동일).
- 본문 HTML 은 공지와 같은 sanitizer 로 정화 후 저장. 댓글은 순수 텍스트.
"""
from typing import Dict, List, Optional

import nh3
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.free_board import FreeBoardPost, FreeBoardComment
from app.models.user import User
from app.schemas.free_board import (
    PostCreate, PostUpdate, CommentCreate,
    PostListItem, PostListResponse, PostDetail, CommentResponse,
)
from app.services.announcement_service import sanitize_html


def _is_admin(user: User) -> bool:
    return getattr(user, "role", None) == "ADMIN"


# 제목·댓글은 순수 텍스트로 저장한다. 화면에서 텍스트로만 출력(자동 이스케이프)하므로
# HTML 정화기를 거치지 않는다 — 거치면 'R&D', '<3' 같은 글자가 &amp; 등으로 바뀌어 저장된다.

def _clean_title(text: str) -> str:
    """제목: 앞뒤 공백 제거 + 연속 공백/줄바꿈을 한 칸으로."""
    return " ".join((text or "").split())


def _clean_comment(text: str) -> str:
    """댓글: 앞뒤 공백만 제거(줄바꿈 유지)."""
    return (text or "").strip()


def _body_is_empty(html: str) -> bool:
    """텍스트도 이미지도 없는 본문(<p></p> 등)인지."""
    if "<img" in html:
        return False
    return not nh3.clean(html, tags=set()).strip()


def _author_names(db: Session, user_ids: set) -> Dict[int, str]:
    if not user_ids:
        return {}
    return {uid: name for uid, name in
            db.query(User.id, User.name).filter(User.id.in_(user_ids)).all()}


def _comment_counts(db: Session, post_ids: List[int]) -> Dict[int, int]:
    if not post_ids:
        return {}
    return dict(
        db.query(FreeBoardComment.post_id, func.count())
        .filter(FreeBoardComment.post_id.in_(post_ids), FreeBoardComment.is_deleted.is_(False))
        .group_by(FreeBoardComment.post_id).all()
    )


# ==================== 글 ====================

def get_post(db: Session, post_id: int) -> FreeBoardPost:
    post = db.query(FreeBoardPost).filter(
        FreeBoardPost.id == post_id, FreeBoardPost.is_active.is_(True)).first()
    if post is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    return post


def list_posts(db: Session, user: User, page: int, size: int,
               category: Optional[str], q: Optional[str]) -> PostListResponse:
    base = db.query(FreeBoardPost).filter(FreeBoardPost.is_active.is_(True))
    if category:
        base = base.filter(FreeBoardPost.category == category)
    if q:
        base = base.filter(FreeBoardPost.title.ilike(f"%{q}%"))

    total = base.count()
    rows = (base.order_by(FreeBoardPost.created_at.desc(), FreeBoardPost.id.desc())
            .offset(max(0, (page - 1) * size)).limit(size).all())

    # 익명 글의 작성자는 이름 조회 대상에서도 제외
    names = _author_names(db, {r.author_id for r in rows if not r.is_anonymous})
    counts = _comment_counts(db, [r.id for r in rows])

    items = [PostListItem(
        id=r.id, category=r.category, title=r.title, is_anonymous=r.is_anonymous,
        author_name=None if r.is_anonymous else names.get(r.author_id),
        is_mine=(r.author_id == user.id),
        view_count=r.view_count, comment_count=int(counts.get(r.id, 0)),
        created_at=r.created_at,
    ) for r in rows]
    return PostListResponse(items=items, total=total, page=page, size=size)


def _comment_responses(db: Session, post: FreeBoardPost, user: User) -> List[CommentResponse]:
    rows = (db.query(FreeBoardComment)
            .filter(FreeBoardComment.post_id == post.id)
            .order_by(FreeBoardComment.created_at.asc(), FreeBoardComment.id.asc()).all())
    # 삭제된 댓글은 살아 있는 답글이 있을 때만 자리 표시로 남긴다
    alive_parents = {c.parent_id for c in rows if c.parent_id and not c.is_deleted}
    rows = [c for c in rows if not c.is_deleted or c.id in alive_parents]
    visible_ids = {c.id for c in rows}
    names = _author_names(db, {c.author_id for c in rows if not c.is_anonymous and not c.is_deleted})
    admin = _is_admin(user)

    out = []
    for c in rows:
        # 부모가 목록에서 빠진 답글은 최상위로 올린다(방어 — 정상 흐름에선 발생하지 않음)
        parent_id = c.parent_id if c.parent_id in visible_ids else None
        if c.is_deleted:
            out.append(CommentResponse(
                id=c.id, parent_id=parent_id, content="", is_anonymous=True,
                is_deleted=True, created_at=c.created_at))
            continue
        mine = c.author_id == user.id
        out.append(CommentResponse(
            id=c.id, parent_id=parent_id, content=c.content, is_anonymous=c.is_anonymous,
            author_name=None if c.is_anonymous else names.get(c.author_id),
            # 익명 글의 글쓴이가 실명 댓글을 달면 '글쓴이' 표시로 신원이 드러나므로,
            # 글과 댓글의 익명 여부가 같을 때만 표시한다
            is_post_author=(c.author_id == post.author_id and c.is_anonymous == post.is_anonymous),
            is_mine=mine, can_delete=(mine or admin), created_at=c.created_at))
    return out


def to_detail(db: Session, post: FreeBoardPost, user: User) -> PostDetail:
    mine = post.author_id == user.id
    comments = _comment_responses(db, post, user)
    author_name = None
    if not post.is_anonymous:
        author_name = db.query(User.name).filter(User.id == post.author_id).scalar()
    return PostDetail(
        id=post.id, category=post.category, title=post.title, body=post.body,
        is_anonymous=post.is_anonymous, author_name=author_name,
        is_mine=mine, can_edit=mine, can_delete=(mine or _is_admin(user)),
        view_count=post.view_count,
        comment_count=sum(1 for c in comments if not c.is_deleted),
        created_at=post.created_at, updated_at=post.updated_at,
        comments=comments,
    )


def increase_view(db: Session, post: FreeBoardPost) -> None:
    """조회수 +1. DB 에서 원자적으로 증가(동시 열람 시 누락 방지), updated_at 은 건드리지 않는다."""
    db.query(FreeBoardPost).filter(FreeBoardPost.id == post.id).update(
        {FreeBoardPost.view_count: FreeBoardPost.view_count + 1,
         FreeBoardPost.updated_at: FreeBoardPost.updated_at},
        synchronize_session=False)
    db.commit()
    db.refresh(post)


def create_post(db: Session, user: User, payload: PostCreate) -> FreeBoardPost:
    title = _clean_title(payload.title)
    body = sanitize_html(payload.body)
    if not title:
        raise HTTPException(status_code=400, detail="제목을 입력하세요")
    if _body_is_empty(body):
        raise HTTPException(status_code=400, detail="내용을 입력하세요")
    post = FreeBoardPost(
        category=payload.category, title=title, body=body,
        is_anonymous=payload.is_anonymous, author_id=user.id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, user: User, post: FreeBoardPost, payload: PostUpdate) -> FreeBoardPost:
    if post.author_id != user.id:
        raise HTTPException(status_code=403, detail="본인이 작성한 글만 수정할 수 있습니다")
    data = payload.model_dump(exclude_unset=True)
    if data.get("category") is not None:
        post.category = data["category"]
    if data.get("title") is not None:
        title = _clean_title(data["title"])
        if not title:
            raise HTTPException(status_code=400, detail="제목을 입력하세요")
        post.title = title
    if data.get("body") is not None:
        body = sanitize_html(data["body"])
        if _body_is_empty(body):
            raise HTTPException(status_code=400, detail="내용을 입력하세요")
        post.body = body
    if data.get("is_anonymous") is not None:
        post.is_anonymous = data["is_anonymous"]
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, user: User, post: FreeBoardPost) -> None:
    """소프트 삭제(본인 또는 관리자)."""
    if post.author_id != user.id and not _is_admin(user):
        raise HTTPException(status_code=403, detail="본인이 작성한 글만 삭제할 수 있습니다")
    post.is_active = False
    db.commit()


# ==================== 댓글 ====================

def add_comment(db: Session, user: User, post: FreeBoardPost, payload: CommentCreate) -> FreeBoardComment:
    content = _clean_comment(payload.content)
    if not content:
        raise HTTPException(status_code=400, detail="댓글 내용을 입력하세요")
    parent_id = None
    if payload.parent_id is not None:
        parent = db.query(FreeBoardComment).filter(
            FreeBoardComment.id == payload.parent_id,
            FreeBoardComment.post_id == post.id,
            FreeBoardComment.is_deleted.is_(False)).first()
        if parent is None:
            raise HTTPException(status_code=400, detail="답글을 달 댓글을 찾을 수 없습니다")
        # 답글은 1단계만: 답글에 답글을 달면 같은 부모 아래로 붙인다
        parent_id = parent.parent_id or parent.id
    comment = FreeBoardComment(
        post_id=post.id, parent_id=parent_id, content=content,
        is_anonymous=payload.is_anonymous, author_id=user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, user: User, post: FreeBoardPost, comment_id: int) -> None:
    """댓글 삭제(본인 또는 관리자). 답글이 남아 있으면 행을 남기고 '삭제된 댓글'로 표시한다."""
    comment = db.query(FreeBoardComment).filter(
        FreeBoardComment.id == comment_id,
        FreeBoardComment.post_id == post.id,
        FreeBoardComment.is_deleted.is_(False)).first()
    if comment is None:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")
    if comment.author_id != user.id and not _is_admin(user):
        raise HTTPException(status_code=403, detail="본인이 작성한 댓글만 삭제할 수 있습니다")
    comment.is_deleted = True
    db.commit()
