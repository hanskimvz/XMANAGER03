"""회사 공지사항 서비스 (v0.50.0).

라우터는 얇게 유지하고, 가시성 필터·읽음 멱등 처리·첨부 저장·집계를 여기에 모은다.
- 부서 가시성: target_departments NULL/[] = 전체, 아니면 본인 부서 포함 시 열람. 관리자는 전체.
- 읽음: (공지,사용자) UNIQUE + ON CONFLICT DO NOTHING 로 멱등 기록.
- 본문 HTML 은 nh3 로 sanitize 후 저장(저장형 XSS 차단).
"""
import uuid
import shutil
from pathlib import Path
from typing import List, Optional

import nh3
from fastapi import HTTPException, UploadFile
from sqlalchemy import func, or_, case
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.models.announcement import (
    Announcement, AnnouncementAttachment, AnnouncementRead,
)
from app.models.user import User
from app.models.department import Department
from app.schemas.announcement import (
    AnnouncementListItem, AnnouncementListResponse, AnnouncementDetail,
    AttachmentResponse, ReadReceipt, ReadReceiptList, UnreadUser,
)

# 첨부 허용 확장자: 문서 + 이미지(공지에 PDF/이미지 첨부 흔함)
_ALLOWED_EXT = set(settings.ALLOWED_DOCUMENT_EXTENSIONS) | set(settings.ALLOWED_PHOTO_EXTENSIONS)


# ==================== sanitize ====================

# 리치텍스트 에디터(frontend components/editor)가 만드는 서식만 추가 허용한다.
# - span/mark 의 style: 글자색·글자 크기·형광펜 색 (CSS 속성은 아래 3종만 통과)
# - img src 의 data:image/*;base64 : 본문에 직접 넣은 이미지
_STYLE_TAGS = ("span", "mark")
_STYLE_PROPERTIES = {"color", "font-size", "background-color"}
_DATA_IMAGE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/gif;base64,",
    "data:image/webp;base64,",
)

_HTML_ATTRIBUTES = {tag: set(attrs) for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()}
for _tag in _STYLE_TAGS:
    _HTML_ATTRIBUTES.setdefault(_tag, set()).add("style")
_HTML_URL_SCHEMES = set(nh3.ALLOWED_URL_SCHEMES) | {"data"}


def _filter_attribute(tag: str, attr: str, value: str) -> Optional[str]:
    """data: URL 은 img src 의 래스터 이미지에만 허용 — 링크 등 그 외 위치에서는 제거."""
    if value.strip().lower().startswith("data:"):
        if tag == "img" and attr == "src" and value.strip().lower().startswith(_DATA_IMAGE_PREFIXES):
            return value
        return None
    return value


def sanitize_html(html: Optional[str]) -> str:
    """TipTap 산출 HTML 정화(script/onerror 등 제거).

    nh3(ammonia) 기본 허용목록 + 에디터 서식(색/크기/형광펜 style, 본문 이미지 data URL).
    """
    return nh3.clean(
        html or "",
        attributes=_HTML_ATTRIBUTES,
        attribute_filter=_filter_attribute,
        url_schemes=_HTML_URL_SCHEMES,
        filter_style_properties=_STYLE_PROPERTIES,
    )


def sanitize_title(text: Optional[str]) -> str:
    """제목은 순수 텍스트 — 모든 태그 제거 + 공백 정리(저장형 XSS 방어)."""
    cleaned = nh3.clean(text or "", tags=set())
    return " ".join(cleaned.split()).strip()


# ==================== 권한/가시성 ====================

def is_manager(db: Session, user: User) -> bool:
    """공지 '전체 보기/작성' 판정 단일 출처."""
    if getattr(user, "role", None) == "ADMIN":
        return True
    from app.services.rbac_service import has_permission
    return has_permission(db, user, "announcement:manage")


def _visible_query(db: Session, user: User):
    """비관리자: 활성 + (전체공개 OR 본인부서 타깃) 공지만.
    target_departments 가 배열이 아닌 값(SQL NULL·JSON null·객체 등)이면 '전체 공개'로 간주.
    (jsonb_array_length 는 배열이 아닌 값에 대해 에러 → CASE 로 배열일 때만 호출)"""
    dept = getattr(user, "department", None)
    # 전체 공개: 배열이면 길이 0, 배열이 아니면(널 포함) 무조건 공개
    public = case(
        (func.jsonb_typeof(Announcement.target_departments) == "array",
         func.jsonb_array_length(Announcement.target_departments) == 0),
        else_=True,
    )
    cond = public
    if dept:
        cond = or_(public, Announcement.target_departments.contains([dept]))
    return db.query(Announcement).filter(Announcement.is_active.is_(True), cond)


def get_visible(db: Session, user: User, announcement_id: int) -> Optional[Announcement]:
    """열람 가능한 공지 1건 반환(없거나 범위 밖이면 None — 라우터에서 404)."""
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if ann is None:
        return None
    if is_manager(db, user):
        return ann
    if not ann.is_active:
        return None
    tdept = ann.target_departments
    if tdept and len(tdept) > 0 and getattr(user, "department", None) not in tdept:
        return None
    return ann


# ==================== 목록/집계 ====================

def _unread_total(db: Session, user: User, mgr: bool) -> int:
    if mgr:
        base = db.query(Announcement.id).filter(Announcement.is_active.is_(True))
    else:
        base = _visible_query(db, user).with_entities(Announcement.id)
    read_subq = db.query(AnnouncementRead.announcement_id).filter(
        AnnouncementRead.user_id == user.id)
    return base.filter(~Announcement.id.in_(read_subq)).count()


def list_for_user(db: Session, user: User, page: int, size: int,
                  q: Optional[str], include_inactive: bool) -> AnnouncementListResponse:
    mgr = is_manager(db, user)
    if mgr:
        base = db.query(Announcement)
        if not include_inactive:
            base = base.filter(Announcement.is_active.is_(True))
    else:
        base = _visible_query(db, user)
    if q:
        base = base.filter(Announcement.title.ilike(f"%{q}%"))

    total = base.count()
    rows = (base.order_by(
                Announcement.is_pinned.desc(),
                Announcement.published_at.desc(),
                Announcement.id.desc())
            .offset(max(0, (page - 1) * size)).limit(size).all())

    ids = [r.id for r in rows]
    authors, att_counts, read_counts, my_reads = {}, {}, {}, set()
    if ids:
        author_ids = {r.created_by for r in rows}
        authors = {uid: name for uid, name in
                   db.query(User.id, User.name).filter(User.id.in_(author_ids)).all()}
        att_counts = dict(db.query(AnnouncementAttachment.announcement_id, func.count())
                          .filter(AnnouncementAttachment.announcement_id.in_(ids))
                          .group_by(AnnouncementAttachment.announcement_id).all())
        read_counts = dict(db.query(AnnouncementRead.announcement_id, func.count())
                           .filter(AnnouncementRead.announcement_id.in_(ids))
                           .group_by(AnnouncementRead.announcement_id).all())
        my_reads = {aid for (aid,) in db.query(AnnouncementRead.announcement_id)
                    .filter(AnnouncementRead.announcement_id.in_(ids),
                            AnnouncementRead.user_id == user.id).all()}

    items = [AnnouncementListItem(
        id=r.id, title=r.title, is_pinned=r.is_pinned,
        target_departments=r.target_departments, published_at=r.published_at,
        is_active=r.is_active, created_by=r.created_by,
        author_name=authors.get(r.created_by),
        attachment_count=int(att_counts.get(r.id, 0)),
        read_count=int(read_counts.get(r.id, 0)),
        is_unread=(r.id not in my_reads),
    ) for r in rows]

    return AnnouncementListResponse(
        items=items, total=total, page=page, size=size,
        unread_total=_unread_total(db, user, mgr),
    )


def unread_total(db: Session, user: User) -> int:
    return _unread_total(db, user, is_manager(db, user))


def to_detail(db: Session, ann: Announcement, user: User) -> AnnouncementDetail:
    atts = [_attachment_response(ann.id, a) for a in sorted(ann.attachments, key=lambda x: x.id)]
    read_count = (db.query(func.count()).select_from(AnnouncementRead)
                  .filter(AnnouncementRead.announcement_id == ann.id).scalar() or 0)
    is_unread = db.query(AnnouncementRead.id).filter(
        AnnouncementRead.announcement_id == ann.id,
        AnnouncementRead.user_id == user.id).first() is None
    author_name = db.query(User.name).filter(User.id == ann.created_by).scalar()
    return AnnouncementDetail(
        id=ann.id, title=ann.title, body=ann.body, is_pinned=ann.is_pinned,
        target_departments=ann.target_departments, published_at=ann.published_at,
        is_active=ann.is_active, created_by=ann.created_by, author_name=author_name,
        created_at=ann.created_at, updated_at=ann.updated_at,
        attachments=atts, is_unread=is_unread, read_count=int(read_count),
    )


def mark_read(db: Session, announcement_id: int, user_id: int) -> None:
    """멱등 읽음 기록(중복 열람해도 1행). 별도 commit 으로 GET 안정성 보장.
    이 공지에 대한 종(인앱) 알림도 함께 읽음 처리 → 종 배지 즉시 감소."""
    stmt = (pg_insert(AnnouncementRead)
            .values(announcement_id=announcement_id, user_id=user_id)
            .on_conflict_do_nothing(index_elements=["announcement_id", "user_id"]))
    db.execute(stmt)
    from app.models.notification import Notification
    db.query(Notification).filter(
        Notification.recipient_id == user_id,
        Notification.related_type == "announcement",
        Notification.related_id == announcement_id,
        Notification.is_read == False,  # noqa: E712
    ).update({Notification.is_read: True, Notification.read_at: func.now()},
             synchronize_session=False)
    db.commit()


# ==================== 부서 코드 검증 ====================

def validate_departments(db: Session, codes: Optional[List[str]]) -> Optional[List[str]]:
    """대상 부서 코드 검증. None/[] 통과(전체). 미존재/비활성 코드는 400."""
    if not codes:
        return codes
    valid = {c for (c,) in db.query(Department.code).filter(Department.is_active.is_(True)).all()}
    unknown = [c for c in codes if c not in valid]
    if unknown:
        raise HTTPException(status_code=400, detail=f"존재하지 않는 부서 코드: {', '.join(unknown)}")
    # 중복 제거(순서 보존)
    return list(dict.fromkeys(codes))


# ==================== 첨부 ====================

def _attach_dir(announcement_id: int) -> Path:
    return settings.uploads_path / "announcements" / str(announcement_id) / "attachments"


def _attachment_response(ann_id: int, a: AnnouncementAttachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=a.id, original_name=a.original_name, file_size=a.file_size,
        content_type=a.content_type, created_at=a.created_at,
        download_url=f"{settings.API_V1_PREFIX}/announcements/{ann_id}/attachments/{a.id}/download",
    )


async def save_attachment(db: Session, ann: Announcement, file: UploadFile,
                          uploaded_by: int) -> AnnouncementAttachment:
    original = file.filename or "file"
    ext = Path(original).suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400,
                            detail=f"허용되지 않는 파일 형식입니다({ext}). 문서/이미지만 가능")
    # 크기 제한을 '읽으면서' 검사 → 전체를 메모리에 올린 뒤 거르지 않음(대용량 업로드 OOM 방지)
    max_size = settings.MAX_UPLOAD_SIZE
    max_mb = max_size // (1024 * 1024)
    chunks, total = [], 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(status_code=413, detail=f"파일이 너무 큽니다(최대 {max_mb}MB)")
        chunks.append(chunk)
    content = b"".join(chunks)

    d = _attach_dir(ann.id)
    d.mkdir(parents=True, exist_ok=True)
    # 경로탈출 방지: basename 만 사용
    safe = (Path(original).name.replace("\\", "_").replace("/", "_")) or "file"
    stored = f"{uuid.uuid4()}_{safe}"
    with open(d / stored, "wb") as f:
        f.write(content)

    att = AnnouncementAttachment(
        announcement_id=ann.id, original_name=safe,
        file_path=f"announcements/{ann.id}/attachments/{stored}",
        file_size=len(content), content_type=file.content_type, uploaded_by=uploaded_by,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


def delete_attachment(db: Session, att: AnnouncementAttachment) -> None:
    try:
        full = settings.uploads_path / att.file_path
        if full.exists():
            full.unlink()
    except OSError:
        pass  # 파일이 없어도 DB 행은 삭제
    db.delete(att)
    db.commit()


def attachment_fullpath(att: AnnouncementAttachment) -> Path:
    """다운로드용 절대경로(경로탈출 검증 포함)."""
    full = (settings.uploads_path / att.file_path).resolve()
    try:
        full.relative_to(settings.uploads_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="접근이 거부되었습니다")
    if not full.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    return full


# ==================== 삭제 ====================

def delete_announcement(db: Session, ann: Announcement, hard: bool = False) -> None:
    # 이 공지에 대한 종(인앱) 알림 정리 → 수신함에 죽은 링크가 남지 않도록
    from app.models.notification import Notification
    db.query(Notification).filter(
        Notification.related_type == "announcement",
        Notification.related_id == ann.id,
    ).delete(synchronize_session=False)
    if not hard:
        ann.is_active = False
        db.commit()
        return
    # 물리 파일 먼저 제거(캐스케이드는 행만 지움)
    for a in list(ann.attachments):
        try:
            full = settings.uploads_path / a.file_path
            if full.exists():
                full.unlink()
        except OSError:
            pass
    try:
        d = settings.uploads_path / "announcements" / str(ann.id)
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    except OSError:
        pass
    db.delete(ann)  # announcement_reads/attachments 는 FK CASCADE
    db.commit()


# ==================== 읽음 영수(관리자) ====================

def read_receipts(db: Session, ann: Announcement) -> ReadReceiptList:
    # 대상 인원: 전체공개면 전 활성자, 부서 타깃이면 해당 부서 활성자
    audience_q = db.query(User).filter(User.is_active.is_(True))
    tdept = ann.target_departments
    if tdept and len(tdept) > 0:
        audience_q = audience_q.filter(User.department.in_(tdept))
    audience = audience_q.all()

    read_rows = (db.query(AnnouncementRead.read_at, User.id, User.name, User.department)
                 .join(User, User.id == AnnouncementRead.user_id)
                 .filter(AnnouncementRead.announcement_id == ann.id)
                 .order_by(AnnouncementRead.read_at.desc()).all())
    read_uids = {r[1] for r in read_rows}
    read = [ReadReceipt(user_id=uid, name=name, department=dept, read_at=read_at)
            for (read_at, uid, name, dept) in read_rows]
    unread = [UnreadUser(user_id=u.id, name=u.name, department=u.department)
              for u in audience if u.id not in read_uids]

    return ReadReceiptList(
        announcement_id=ann.id, total_targeted=len(audience),
        read_count=len(read), read=read, unread=unread,
    )
