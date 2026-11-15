"""
작업지시서 공정 작업 (Work Order Task) 모델
v0.29.0: 작업지시서 하위 공정 단계 관리

작업지시서 1건 안에 여러 공정 작업이 순서대로 진행됩니다.
예: 인서트 작업 → K-1 가공 → 조립 → 검사/포장
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class WorkOrderTask(Base):
    __tablename__ = "work_order_task"

    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False, index=True)

    task_name = Column(String(100), nullable=False, comment="공정명 (인서트, K-1 가공, 조립 등)")
    assigned_team = Column(String(100), comment="담당팀")
    status = Column(String(20), default="PENDING", comment="상태 (PENDING/IN_PROGRESS/COMPLETED)")

    sort_order = Column(Integer, default=0, comment="공정 순서")
    started_at = Column(DateTime(timezone=True), comment="시작 시간")
    completed_at = Column(DateTime(timezone=True), comment="완료 시간")
    remarks = Column(Text, comment="비고")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    work_order = relationship("WorkOrder", back_populates="tasks")
