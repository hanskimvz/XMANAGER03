"""
공휴일 API — 일정 캘린더 표시용.

data.go.kr 서비스키를 브라우저에 노출하지 않도록 백엔드가 대신 조회·캐시한다.
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import require_auth
from app.models.user import User
from app.services import holiday_service

router = APIRouter(prefix="/holidays", tags=["공휴일"])

_MAX_RANGE_DAYS = 800  # 과도한 범위 조회 방지(연도별 외부 호출)


class HolidayItem(BaseModel):
    date: str  # YYYY-MM-DD
    name: str


@router.get("", response_model=List[HolidayItem])
def list_holidays(
    date_from: date = Query(..., description="조회 시작일 YYYY-MM-DD"),
    date_to: date = Query(..., description="조회 종료일 YYYY-MM-DD"),
    actor: User = Depends(require_auth),
):
    """기간 내 공휴일 목록. 외부 API 장애/키 미설정 시 빈 배열."""
    if (date_to - date_from).days > _MAX_RANGE_DAYS:
        raise HTTPException(status_code=400, detail="조회 기간이 너무 깁니다")
    return holiday_service.list_holidays(date_from, date_to)
