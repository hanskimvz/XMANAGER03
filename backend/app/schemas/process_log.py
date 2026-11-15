"""
공정 로그 Pydantic 스키마
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ProcessLogCreate(BaseModel):
    """공정 시작 기록"""
    process_type: str = Field(..., max_length=30, description="공정 유형 (INSERT_ISSUE, K1_PROCESSING, ASSEMBLY 등)")
    process_name: Optional[str] = Field(None, max_length=100, description="공정명")
    worker_name: Optional[str] = Field(None, max_length=100, description="작업자/담당팀")
    remarks: Optional[str] = None
    sort_order: int = Field(0, description="공정 순서")


class ProcessLogComplete(BaseModel):
    """공정 완료 기록"""
    remarks: Optional[str] = None


class ProcessLogResponse(BaseModel):
    """공정 로그 응답"""
    id: int
    work_order_id: int
    process_type: str
    process_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_hours: Optional[Decimal] = None
    worker_name: Optional[str] = None
    remarks: Optional[str] = None
    sort_order: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadTimeByProcess(BaseModel):
    """공정별 평균 리드타임"""
    process_type: str
    process_name: Optional[str] = None
    avg_hours: float
    min_hours: float
    max_hours: float
    count: int


class LeadTimeSummary(BaseModel):
    """리드타임 분석 요약"""
    total_work_orders: int = Field(description="분석 대상 작업지시서 수")
    avg_total_hours: float = Field(description="전체 평균 리드타임 (시간)")
    by_process: List[LeadTimeByProcess] = Field(description="공정별 리드타임")
