"""
일정 등록 (v1.03.0)

- schedules: 경영관리 > 일정등록에서 직접 등록한 일정 1건(행사/휴가/외근/출장).
  게시판 > 일정 캘린더가 발주서·작업지시서·전자결재(휴가/출장)와 함께 이 테이블을 읽어 표시한다.

source:
  지금은 'MANUAL'(직접 등록)만 쓴다. 이후 휴가신청서 등 다른 출처와 연동할 때를 위한 자리.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey, Index, CheckConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base

# 유형 코드 -> 한글 라벨 (프런트 api/schedule.ts 의 SCHEDULE_TYPES 와 동일하게 유지)
SCHEDULE_TYPES = {
    "EVENT": "행사",
    "LEAVE": "휴가",
    "FIELDWORK": "외근",
    "TRIP": "출장",
}


class Schedule(Base):
    """직접 등록한 일정 1건."""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    schedule_type = Column(String(20), nullable=False, index=True,
                           comment="유형 코드(EVENT 행사/LEAVE 휴가/FIELDWORK 외근/TRIP 출장)")
    title = Column(String(200), nullable=False, comment="제목")
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True,
                            comment="대상자(행사는 NULL — 전사 일정)")
    start_date = Column(Date, nullable=False, comment="시작일")
    end_date = Column(Date, nullable=False, comment="종료일(하루짜리는 시작일과 동일)")
    location = Column(String(200), nullable=True, comment="장소")
    memo = Column(Text, nullable=True, comment="메모")
    source = Column(String(20), nullable=False, default="MANUAL", server_default="MANUAL",
                    comment="출처(MANUAL 직접 등록)")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True,
                        comment="등록자(수정/삭제 판정용)")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true",
                       comment="활성(소프트 삭제 플래그)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "schedule_type IN ('EVENT', 'LEAVE', 'FIELDWORK', 'TRIP')",
            name="ck_schedules_type",
        ),
        CheckConstraint("end_date >= start_date", name="ck_schedules_date_range"),
        # 캘린더/목록: 활성 일정을 기간으로 조회
        Index("ix_schedules_active_dates", "is_active", "start_date", "end_date"),
    )
