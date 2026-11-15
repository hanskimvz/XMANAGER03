"""
작업지시서 공정 작업 스키마
v0.29.0
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class WorkOrderTaskCreate(BaseModel):
    task_name: str = Field(..., max_length=100, description="공정명")
    assigned_team: Optional[str] = Field(None, max_length=100, description="담당팀")
    sort_order: int = Field(0, description="순서")
    remarks: Optional[str] = Field(None, description="비고")


class WorkOrderTaskUpdate(BaseModel):
    task_name: Optional[str] = None
    assigned_team: Optional[str] = None
    status: Optional[str] = None  # PENDING/IN_PROGRESS/COMPLETED
    sort_order: Optional[int] = None
    remarks: Optional[str] = None


class WorkOrderTaskResponse(BaseModel):
    id: int
    work_order_id: int
    task_name: str
    assigned_team: Optional[str] = None
    status: str
    sort_order: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    remarks: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


TASK_STATUS_LABELS = {
    "PENDING": "대기",
    "IN_PROGRESS": "진행중",
    "COMPLETED": "완료",
}
