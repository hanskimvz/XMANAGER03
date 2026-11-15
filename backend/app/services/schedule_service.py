"""일정 등록 서비스 (v1.03.0).

- 열람/등록: 로그인한 전 직원.
- 수정/삭제: 등록자 본인 또는 관리자(ADMIN). 삭제는 소프트 삭제.
- 행사(EVENT)는 대상자 없음(전사 일정), 휴가/외근/출장은 대상자 필수.
"""
import calendar
from datetime import date
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.schedule import Schedule
from app.models.user import User
from app.schemas.schedule import ScheduleCreate, ScheduleItem, ScheduleListResponse


def _is_admin(user: User) -> bool:
    return getattr(user, "role", None) == "ADMIN"


def _can_edit(row: Schedule, user: User) -> bool:
    return row.created_by == user.id or _is_admin(user)


def _user_names(db: Session, user_ids: set) -> Dict[int, str]:
    user_ids.discard(None)
    if not user_ids:
        return {}
    return {uid: name for uid, name in
            db.query(User.id, User.name).filter(User.id.in_(user_ids)).all()}


def _to_items(db: Session, rows: List[Schedule], user: User) -> List[ScheduleItem]:
    names = _user_names(db, {r.target_user_id for r in rows} | {r.created_by for r in rows})
    return [ScheduleItem(
        id=r.id, schedule_type=r.schedule_type, title=r.title,
        target_user_id=r.target_user_id, target_name=names.get(r.target_user_id),
        start_date=r.start_date, end_date=r.end_date,
        location=r.location, memo=r.memo, source=r.source,
        created_by_name=names.get(r.created_by),
        can_edit=_can_edit(r, user), created_at=r.created_at,
    ) for r in rows]


def to_item(db: Session, row: Schedule, user: User) -> ScheduleItem:
    return _to_items(db, [row], user)[0]


def _overlapping(query, date_from: Optional[date], date_to: Optional[date]):
    """[date_from, date_to] 구간과 하루라도 겹치는 일정만."""
    if date_to is not None:
        query = query.filter(Schedule.start_date <= date_to)
    if date_from is not None:
        query = query.filter(Schedule.end_date >= date_from)
    return query


def get_schedule(db: Session, schedule_id: int) -> Schedule:
    row = db.query(Schedule).filter(
        Schedule.id == schedule_id, Schedule.is_active.is_(True)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다")
    return row


def list_schedules(db: Session, user: User, page: int, size: int,
                   schedule_type: Optional[str], month: Optional[str],
                   q: Optional[str]) -> ScheduleListResponse:
    base = db.query(Schedule).filter(Schedule.is_active.is_(True))
    if schedule_type:
        base = base.filter(Schedule.schedule_type == schedule_type)
    if month:
        year, mon = int(month[:4]), int(month[5:7])
        if not 1 <= mon <= 12:
            raise HTTPException(status_code=400, detail="조회 월이 올바르지 않습니다")
        last_day = calendar.monthrange(year, mon)[1]
        base = _overlapping(base, date(year, mon, 1), date(year, mon, last_day))
    q = (q or "").strip()
    if q:
        like = f"%{q}%"
        base = base.outerjoin(User, User.id == Schedule.target_user_id).filter(or_(
            Schedule.title.ilike(like),
            Schedule.location.ilike(like),
            User.name.ilike(like),
        ))

    total = base.count()
    rows = (base.order_by(Schedule.start_date.asc(), Schedule.id.asc())
            .offset(max(0, (page - 1) * size)).limit(size).all())
    return ScheduleListResponse(items=_to_items(db, rows, user), total=total, page=page, size=size)


def calendar_schedules(db: Session, user: User,
                       date_from: Optional[date], date_to: Optional[date]) -> List[ScheduleItem]:
    """캘린더 표기용 — 조회 구간과 겹치는 활성 일정 전부."""
    base = _overlapping(db.query(Schedule).filter(Schedule.is_active.is_(True)), date_from, date_to)
    rows = base.order_by(Schedule.start_date.asc(), Schedule.id.asc()).all()
    return _to_items(db, rows, user)


def _clean(text: Optional[str]) -> Optional[str]:
    text = (text or "").strip()
    return text or None


def _apply(db: Session, row: Schedule, payload: ScheduleCreate) -> None:
    """입력 검증 후 행에 반영(등록/수정 공용)."""
    title = " ".join((payload.title or "").split())
    if not title:
        raise HTTPException(status_code=400, detail="제목을 입력하세요")
    end_date = payload.end_date or payload.start_date
    if end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="종료일은 시작일보다 빠를 수 없습니다")

    target_user_id = None
    if payload.schedule_type != "EVENT":
        if payload.target_user_id is None:
            raise HTTPException(status_code=400, detail="대상자를 선택하세요")
        exists = db.query(User.id).filter(User.id == payload.target_user_id).first()
        if exists is None:
            raise HTTPException(status_code=400, detail="대상자를 찾을 수 없습니다")
        target_user_id = payload.target_user_id

    row.schedule_type = payload.schedule_type
    row.title = title
    row.target_user_id = target_user_id
    row.start_date = payload.start_date
    row.end_date = end_date
    row.location = _clean(payload.location)
    row.memo = _clean(payload.memo)


def create_schedule(db: Session, user: User, payload: ScheduleCreate) -> Schedule:
    row = Schedule(created_by=user.id, source="MANUAL")
    _apply(db, row, payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_schedule(db: Session, user: User, row: Schedule, payload: ScheduleCreate) -> Schedule:
    if not _can_edit(row, user):
        raise HTTPException(status_code=403, detail="본인이 등록한 일정만 수정할 수 있습니다")
    _apply(db, row, payload)
    db.commit()
    db.refresh(row)
    return row


def delete_schedule(db: Session, user: User, row: Schedule) -> None:
    """소프트 삭제(등록자 본인 또는 관리자)."""
    if not _can_edit(row, user):
        raise HTTPException(status_code=403, detail="본인이 등록한 일정만 삭제할 수 있습니다")
    row.is_active = False
    db.commit()
