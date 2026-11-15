"""웹푸시 API (v0.59.0)

- GET  /push/vapid-public-key : 프론트가 구독(subscribe) 시 쓸 공개키
- POST /push/subscribe        : 브라우저 구독 정보 저장(endpoint 기준 upsert)
- POST /push/unsubscribe      : 구독 해제
"""

from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_auth
from app.models.user import User
from app.models.push_subscription import PushSubscription
from app.services import web_push_service

router = APIRouter(prefix="/push", tags=["웹푸시"])


class SubKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: SubKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


@router.get("/vapid-public-key")
def vapid_public_key(db: Session = Depends(get_db)):
    return {"public_key": web_push_service.get_public_key(db)}


@router.post("/subscribe")
def subscribe(payload: PushSubscribeRequest, request: Request,
              user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """구독 저장 — 같은 endpoint면 소유자/키 갱신(기기 재구독·계정 전환 대응)."""
    ua = (request.headers.get("user-agent") or "")[:300]
    sub = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    if sub:
        sub.user_id = user.id
        sub.p256dh = payload.keys.p256dh
        sub.auth = payload.keys.auth
        sub.user_agent = ua
    else:
        sub = PushSubscription(
            user_id=user.id, endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh, auth=payload.keys.auth, user_agent=ua,
        )
        db.add(sub)
    db.commit()
    return {"ok": True}


@router.post("/unsubscribe")
def unsubscribe(payload: PushUnsubscribeRequest,
                user: User = Depends(require_auth), db: Session = Depends(get_db)):
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == payload.endpoint,
        PushSubscription.user_id == user.id,
    ).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}
