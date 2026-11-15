"""일정 등록 스키마 (v1.03.0)."""
from typing import List, Literal, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

ScheduleType = Literal["EVENT", "LEAVE", "FIELDWORK", "TRIP"]


# ==================== 입력 ====================

class ScheduleCreate(BaseModel):
    schedule_type: ScheduleType = Field(..., description="유형 코드")
    title: str = Field(..., min_length=1, max_length=200, description="제목")
    target_user_id: Optional[int] = Field(None, description="대상자(행사는 생략)")
    start_date: date = Field(..., description="시작일")
    end_date: Optional[date] = Field(None, description="종료일(생략 시 시작일)")
    location: Optional[str] = Field(None, max_length=200, description="장소")
    memo: Optional[str] = Field(None, max_length=2000, description="메모")


class ScheduleUpdate(ScheduleCreate):
    """전체 수정 — 등록과 같은 필드를 모두 보낸다."""


# ==================== 출력 ====================

class ScheduleItem(BaseModel):
    id: int
    schedule_type: ScheduleType
    title: str
    target_user_id: Optional[int] = None
    target_name: Optional[str] = None   # 행사(대상자 없음)면 None
    start_date: date
    end_date: date
    location: Optional[str] = None
    memo: Optional[str] = None
    source: str = "MANUAL"
    created_by_name: Optional[str] = None
    can_edit: bool = False              # 등록자 본인 또는 관리자
    created_at: Optional[datetime] = None


class ScheduleListResponse(BaseModel):
    items: List[ScheduleItem]
    total: int
    page: int
    size: int
