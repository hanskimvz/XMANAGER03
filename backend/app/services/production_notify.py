"""생산요청 알림 수신자(지정 인원) 설정 — AppSetting 저장/조회.

관리자가 지정한 '생산 알림 수신자'를 생산 단계별로 개별 저장한다.
- requested   : 새 생산요청 등록 시(#1)
- in_progress : 생산 시작(진행중 진입) 시
- shipped     : 생산 출고 완료 시

단계별 목록은 AppSetting 한 키(NEW_KEY)에 {event: [user_id,...]} 로 저장한다.
기존 단일 목록(LEGACY_KEY = production_notify_user_ids)은 requested 로 자동 승계한다.
"""
from typing import List, Dict
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting

NEW_KEY = "production_notify_recipients"
LEGACY_KEY = "production_notify_user_ids"

# 지원 이벤트(생산 단계)
EVENTS = ("requested", "in_progress", "shipped")


def _coerce_ids(v) -> List[int]:
    out: List[int] = []
    for x in (v or []):
        try:
            out.append(int(x))
        except (ValueError, TypeError):
            continue
    return out


def get_all_notify_recipients(db: Session) -> Dict[str, List[int]]:
    """단계별 수신자 목록 {event: [user_id,...]}. 신규 키 우선, 없으면 레거시 승계."""
    row = db.query(AppSetting).filter(AppSetting.key == NEW_KEY).first()
    if row and isinstance(row.value, dict):
        return {e: _coerce_ids(row.value.get(e)) for e in EVENTS}
    # 레거시(단일 목록) → requested 로 승계
    legacy = db.query(AppSetting).filter(AppSetting.key == LEGACY_KEY).first()
    req: List[int] = []
    if legacy and legacy.value:
        raw = legacy.value.get("user_ids") if isinstance(legacy.value, dict) else legacy.value
        req = _coerce_ids(raw)
    return {"requested": req, "in_progress": [], "shipped": []}


def get_notify_recipient_ids(db: Session, event: str = "requested") -> List[int]:
    """특정 단계의 수신자 목록."""
    return get_all_notify_recipients(db).get(event, [])


def set_all_notify_recipients(db: Session, mapping: Dict[str, List[int]]) -> Dict[str, List[int]]:
    """단계별 수신자 목록 일괄 저장."""
    clean = {e: _coerce_ids((mapping or {}).get(e)) for e in EVENTS}
    row = db.query(AppSetting).filter(AppSetting.key == NEW_KEY).first()
    if row is None:
        row = AppSetting(key=NEW_KEY, value=clean)
        db.add(row)
    else:
        row.value = clean
    db.commit()
    return clean
