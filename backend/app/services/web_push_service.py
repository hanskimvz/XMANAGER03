"""웹푸시 발송 서비스 (v0.59.0)

- VAPID 키는 app_settings('vapid_keys')에 1회 생성·영구 저장(키가 바뀌면 기존 구독 무효).
- send_to_user(): 사용자의 모든 구독으로 Web Push 발송. 만료(404/410) 구독은 자동 삭제.
- 알림(NotificationService.create)에서 백그라운드 스레드로 호출 → 요청 지연 없음.
"""

import base64
import json
import logging
import threading

logger = logging.getLogger(__name__)

VAPID_SUBJECT = "mailto:admin@xbeamtech.co.kr"
_VAPID_KEY = "vapid_keys"


def _gen_vapid():
    from py_vapid import Vapid01
    from cryptography.hazmat.primitives import serialization
    v = Vapid01()
    v.generate_keys()
    raw_pub = v.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    public = base64.urlsafe_b64encode(raw_pub).rstrip(b"=").decode()
    private_pem = v.private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode()
    return public, private_pem


def get_or_create_vapid(db) -> tuple:
    """(public_key_b64url, private_pem) 반환. 없으면 생성·저장."""
    from app.models.app_setting import AppSetting
    row = db.query(AppSetting).filter(AppSetting.key == _VAPID_KEY).first()
    if row and row.value and row.value.get("public") and row.value.get("private_pem"):
        return row.value["public"], row.value["private_pem"]
    public, private_pem = _gen_vapid()
    if row is None:
        row = AppSetting(key=_VAPID_KEY, value={"public": public, "private_pem": private_pem})
        db.add(row)
    else:
        row.value = {"public": public, "private_pem": private_pem}
    db.commit()
    return public, private_pem


def get_public_key(db) -> str:
    return get_or_create_vapid(db)[0]


def _send_one(subscription_info: dict, payload: str, private_pem: str) -> int:
    """단일 구독 발송. 성공 200/201, 만료 404/410, 그 외 예외. HTTP status 반환."""
    from pywebpush import webpush, WebPushException
    from py_vapid import Vapid01
    vapid = Vapid01.from_pem(private_pem.encode())
    try:
        resp = webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=vapid,
            vapid_claims={"sub": VAPID_SUBJECT},
            timeout=10,
        )
        return resp.status_code
    except WebPushException as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code in (404, 410):
            return code
        raise


def _send_to_user_worker(user_id: int, title: str, body: str, url: str):
    """백그라운드 스레드: 새 세션으로 사용자 구독 조회 후 발송, 만료 구독 삭제."""
    from app.core.database import SessionLocal
    from app.models.push_subscription import PushSubscription
    db = SessionLocal()
    try:
        subs = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
        if not subs:
            return
        _pub, private_pem = get_or_create_vapid(db)
        payload = json.dumps({"title": title, "body": body, "url": url or "/"})
        dead = []
        for s in subs:
            info = {"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}}
            try:
                code = _send_one(info, payload, private_pem)
                if code in (404, 410):
                    dead.append(s.id)
            except Exception:
                logger.warning("web push 발송 실패(user=%s endpoint=%s)", user_id, s.endpoint[:40])
        if dead:
            db.query(PushSubscription).filter(PushSubscription.id.in_(dead)).delete(synchronize_session=False)
            db.commit()
    except Exception:
        logger.exception("web push 워커 오류(user=%s)", user_id)
    finally:
        db.close()


def send_to_user_async(user_id: int, title: str, body: str, url: str):
    """요청을 막지 않도록 데몬 스레드로 발송. 구독 없으면 사실상 no-op."""
    try:
        threading.Thread(
            target=_send_to_user_worker, args=(user_id, title, body, url),
            daemon=True,
        ).start()
    except Exception:
        logger.exception("web push 스레드 시작 실패")


def _send_to_users_worker(user_ids: list, title: str, body: str, url: str):
    """다수 수신자 일괄 발송(공지 등): 스레드 1개 + 세션 1개로 모든 구독을 한 번에 조회,
    HTTP 발송만 제한된 스레드풀로 병렬화. 스레드 폭증·커넥션 풀 고갈 방지."""
    import concurrent.futures
    from app.core.database import SessionLocal
    from app.models.push_subscription import PushSubscription
    db = SessionLocal()
    try:
        subs = db.query(PushSubscription).filter(
            PushSubscription.user_id.in_(user_ids)
        ).all()
        if not subs:
            return
        _pub, private_pem = get_or_create_vapid(db)
        payload = json.dumps({"title": title, "body": body, "url": url or "/"})

        def _one(s):
            info = {"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}}
            try:
                code = _send_one(info, payload, private_pem)
                return (s.id, code in (404, 410))
            except Exception:
                logger.warning("web push 발송 실패(user=%s)", s.user_id)
                return (s.id, False)

        dead = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            for sid, is_dead in ex.map(_one, subs):
                if is_dead:
                    dead.append(sid)
        if dead:
            db.query(PushSubscription).filter(
                PushSubscription.id.in_(dead)
            ).delete(synchronize_session=False)
            db.commit()
    except Exception:
        logger.exception("web push 배치 워커 오류")
    finally:
        db.close()


def send_to_users_async(user_ids, title: str, body: str, url: str):
    """다수 수신자 일괄 발송(데몬 스레드 1개). 커밋 완료 후 호출 권장."""
    ids = list(user_ids or [])
    if not ids:
        return
    try:
        threading.Thread(
            target=_send_to_users_worker, args=(ids, title, body, url),
            daemon=True,
        ).start()
    except Exception:
        logger.exception("web push 배치 스레드 시작 실패")
