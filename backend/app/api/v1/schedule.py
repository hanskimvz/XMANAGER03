"""
일정 등록 API (v1.03.0)

A 예외 라우터: 자체 인증(require_auth) — 로그인한 전 직원이 열람/등록.
- 수정/삭제: 등록자 본인 또는 관리자(ADMIN).
- /schedules/calendar 는 게시판 > 일정 캘린더가 사용한다.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_auth
from app.models.user import User
from app.schemas.schedule import (
    ScheduleType, ScheduleCreate, ScheduleUpdate, ScheduleItem, ScheduleListResponse,
)
from app.services import schedule_service as svc

router = APIRouter(prefix="/schedules", tags=["일정 등록"])


@router.get("", response_model=ScheduleListResponse)
def list_schedules(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    schedule_type: Optional[ScheduleType] = Query(None, description="유형 코드"),
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$", description="조회 월 YYYY-MM"),
    q: Optional[str] = Query(None, description="제목·대상자·장소 검색"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return svc.list_schedules(db, user, page, size, schedule_type, month, q)


@router.get("/calendar", response_model=List[ScheduleItem])
def calendar_schedules(
    date_from: Optional[date] = Query(None, description="조회 시작일 YYYY-MM-DD"),
    date_to: Optional[date] = Query(None, description="조회 종료일 YYYY-MM-DD"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """캘린더 표기용 — 조회 구간과 겹치는 등록 일정."""
    return svc.calendar_schedules(db, user, date_from, date_to)


@router.post("", response_model=ScheduleItem, status_code=201)
def create_schedule(payload: ScheduleCreate,
                    user: User = Depends(require_auth), db: Session = Depends(get_db)):
    return svc.to_item(db, svc.create_schedule(db, user, payload), user)


@router.put("/{schedule_id}", response_model=ScheduleItem)
def update_schedule(schedule_id: int, payload: ScheduleUpdate,
                    user: User = Depends(require_auth), db: Session = Depends(get_db)):
    row = svc.update_schedule(db, user, svc.get_schedule(db, schedule_id), payload)
    return svc.to_item(db, row, user)


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int,
                    user: User = Depends(require_auth), db: Session = Depends(get_db)):
    svc.delete_schedule(db, user, svc.get_schedule(db, schedule_id))
