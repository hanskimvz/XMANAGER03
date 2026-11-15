"""
회사 공지사항 API (v0.50.0)

A 예외 라우터: 자체 인증.
- 읽기(목록/상세/다운로드): require_auth + 부서 가시성 필터(전 직원, 본인 부서/전체공개만).
- 쓰기(작성/수정/삭제/첨부/읽음영수): announcement_manager 가드 — 항상 announcement:manage 요구
  (경영지원팀/ADMIN). RBAC_MODE 와 무관하게 쓰기는 항상 차단(요구사항: 작성은 경영지원팀 전담).

본문 HTML 은 서버에서 nh3 로 sanitize 후 저장(저장형 XSS 차단).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_auth, security, get_current_user
from app.models.user import User
from app.models.announcement import Announcement, AnnouncementAttachment
from app.schemas.announcement import (
    AnnouncementCreate, AnnouncementUpdate, AnnouncementDetail,
    AnnouncementListResponse, AttachmentResponse, ReadReceiptList, UnreadCountResponse,
)
from app.services import announcement_service as svc

router = APIRouter(prefix="/announcements", tags=["공지사항"])


def announcement_manager(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """공지 작성/관리 가드. 항상 announcement:manage 를 요구(경영지원팀/ADMIN).
    전역 RBAC_MODE 와 무관(쓰기는 전담) — leave 와 동일한 '항상 enforce' 정책."""
    user = get_current_user(credentials, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다",
                            headers={"WWW-Authenticate": "Bearer"})
    from app.services.rbac_service import has_permission
    if not has_permission(db, user, "announcement:manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="공지 작성 권한이 없습니다(경영지원팀/관리자)")
    return user


# ==================== 읽기 ====================

@router.get("", response_model=AnnouncementListResponse)
def list_announcements(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="제목 검색"),
    include_inactive: bool = Query(False, description="보관(소프트삭제) 포함 — 관리자만 적용"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return svc.list_for_user(db, user, page, size, q, include_inactive)


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    return UnreadCountResponse(unread_total=svc.unread_total(db, user))


@router.get("/{ann_id}", response_model=AnnouncementDetail)
def get_announcement(ann_id: int, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    ann = svc.get_visible(db, user, ann_id)
    if ann is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다")
    detail = svc.to_detail(db, ann, user)  # is_unread 는 읽음 처리 직전 상태
    svc.mark_read(db, ann.id, user.id)
    return detail


@router.get("/{ann_id}/attachments/{att_id}/download")
def download_attachment(ann_id: int, att_id: int,
                        user: User = Depends(require_auth), db: Session = Depends(get_db)):
    ann = svc.get_visible(db, user, ann_id)  # 다운로드도 열람 범위 검증
    if ann is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다")
    att = db.query(AnnouncementAttachment).filter(
        AnnouncementAttachment.id == att_id,
        AnnouncementAttachment.announcement_id == ann_id).first()
    if att is None:
        raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다")
    full = svc.attachment_fullpath(att)
    return FileResponse(
        path=full, filename=att.original_name,
        media_type=att.content_type or "application/octet-stream",
        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"},
    )


# ==================== 쓰기(경영지원/ADMIN) ====================

@router.post("", response_model=AnnouncementDetail, status_code=201)
def create_announcement(payload: AnnouncementCreate,
                        mgr: User = Depends(announcement_manager), db: Session = Depends(get_db)):
    targets = svc.validate_departments(db, payload.target_departments)
    ann = Announcement(
        title=svc.sanitize_title(payload.title),
        body=svc.sanitize_html(payload.body),
        is_pinned=payload.is_pinned,
        target_departments=targets,
        created_by=mgr.id,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    # 작성자 본인은 자기 공지를 '읽음'으로 기록 → 본인 공지 미열람 배지 +1 방지
    svc.mark_read(db, ann.id, mgr.id)
    # 대상 부서(또는 전체) 직원에게 인앱 알림 발송 (best-effort — 실패해도 공지 등록은 유지)
    try:
        from app.services.notification_service import NotificationService
        notif = NotificationService(db).notify_announcement(ann, mgr.id)
        db.commit()
        # 커밋 성공 후에만 웹푸시 일괄 발송(롤백 시 phantom push 방지 + 스레드 폭증 방지)
        if notif and notif.get("recipient_ids"):
            from app.services import web_push_service
            web_push_service.send_to_users_async(
                notif["recipient_ids"], notif["title"], notif["body"], notif["url"]
            )
    except Exception:
        import logging
        db.rollback()
        logging.getLogger(__name__).exception("공지 알림 발송 실패(무시): 공지 등록은 완료됨")
    return svc.to_detail(db, ann, mgr)


@router.put("/{ann_id}", response_model=AnnouncementDetail)
def update_announcement(ann_id: int, payload: AnnouncementUpdate,
                        mgr: User = Depends(announcement_manager), db: Session = Depends(get_db)):
    ann = db.query(Announcement).filter(Announcement.id == ann_id).first()
    if ann is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다")
    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        ann.title = svc.sanitize_title(data["title"])
    if "body" in data and data["body"] is not None:
        ann.body = svc.sanitize_html(data["body"])
    if "is_pinned" in data and data["is_pinned"] is not None:
        ann.is_pinned = data["is_pinned"]
    if "target_departments" in data:
        ann.target_departments = svc.validate_departments(db, data["target_departments"])
    if "is_active" in data and data["is_active"] is not None:
        ann.is_active = data["is_active"]
    db.commit()
    db.refresh(ann)
    return svc.to_detail(db, ann, mgr)


@router.delete("/{ann_id}", status_code=204)
def delete_announcement(ann_id: int, hard: bool = Query(False, description="물리 삭제(파일까지)"),
                        mgr: User = Depends(announcement_manager), db: Session = Depends(get_db)):
    ann = db.query(Announcement).filter(Announcement.id == ann_id).first()
    if ann is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다")
    svc.delete_announcement(db, ann, hard=hard)


@router.post("/{ann_id}/attachments", response_model=AttachmentResponse)
async def upload_attachment(ann_id: int, file: UploadFile = File(...),
                            mgr: User = Depends(announcement_manager), db: Session = Depends(get_db)):
    ann = db.query(Announcement).filter(Announcement.id == ann_id).first()
    if ann is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다")
    att = await svc.save_attachment(db, ann, file, mgr.id)
    return svc._attachment_response(ann.id, att)


@router.delete("/{ann_id}/attachments/{att_id}", status_code=204)
def delete_attachment(ann_id: int, att_id: int,
                      mgr: User = Depends(announcement_manager), db: Session = Depends(get_db)):
    att = db.query(AnnouncementAttachment).filter(
        AnnouncementAttachment.id == att_id,
        AnnouncementAttachment.announcement_id == ann_id).first()
    if att is None:
        raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다")
    svc.delete_attachment(db, att)


@router.get("/{ann_id}/reads", response_model=ReadReceiptList)
def read_receipts(ann_id: int, mgr: User = Depends(announcement_manager), db: Session = Depends(get_db)):
    ann = db.query(Announcement).filter(Announcement.id == ann_id).first()
    if ann is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다")
    return svc.read_receipts(db, ann)
