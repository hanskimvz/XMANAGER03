"""인앱 알림 API (v0.54.0)

개인 알림함 — 본인 알림만 조회/읽음처리. 별도 RBAC 없음(require_auth).
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_auth
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["알림"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    svc = NotificationService(db)
    items, total, unread = svc.list_for_user(user.id, limit=limit, offset=offset, unread_only=unread_only)
    return NotificationListResponse(
        items=[
            NotificationItem(
                id=n.id,
                type=n.type,
                title=n.title,
                message=n.message,
                link=n.link,
                related_type=n.related_type,
                related_id=n.related_id,
                actor_name=(n.actor.name if n.actor else None),
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in items
        ],
        total=total,
        unread=unread,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return UnreadCountResponse(count=NotificationService(db).unread_count(user.id))


@router.post("/{notif_id}/read")
def mark_read(
    notif_id: int,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ok = NotificationService(db).mark_read(notif_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    cnt = NotificationService(db).mark_all_read(user.id)
    return {"ok": True, "updated": cnt}
