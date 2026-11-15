"""
공정 로그 (Work Order Process Log) 모델
작업지시서 내 세부 공정별 시작/완료 시간을 기록합니다.

v0.24.0: 초기 구현

기존 7단계 워크플로우와 독립적으로 운영.
공정 타입은 자유롭게 추가 가능 (코드 변경 없이 새 공정 추가).

공정 타입 예시:
  INSERT_CHECK    - 인서트 재고 확인
  INSERT_ISSUE    - 인서트 출고
  K1_PROCESSING   - K-1 가공
  ASSEMBLY        - 커넥터 조립
  INSPECTION      - 검사
  PACKING         - 포장
  SHIPPING_PREP   - 출하 준비
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class WorkOrderProcessLog(Base):
    """
    공정 로그
    작업지시서의 세부 공정별 시작/완료 시점과 소요시간을 기록
    """
    __tablename__ = "work_order_process_log"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 작업지시서 참조
    work_order_id = Column(Integer, ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="작업지시서 ID")

    # 공정 유형 (자유 입력 — 새 공정 추가 시 코드 변경 불필요)
    process_type = Column(String(30), nullable=False, index=True, comment="공정 유형")

    # 공정 표시명 (UI 표시용)
    process_name = Column(String(100), comment="공정명 (예: 인서트 출고, K-1 가공)")

    # 시간 기록
    started_at = Column(DateTime(timezone=True), comment="시작 시점")
    completed_at = Column(DateTime(timezone=True), comment="완료 시점")

    # 소요시간 (시간 단위, 완료 시 자동 계산)
    duration_hours = Column(Numeric(10, 2), comment="소요시간 (시간)")

    # 담당자/팀
    worker_name = Column(String(100), comment="작업자/담당팀")

    # 비고
    remarks = Column(Text, comment="비고")

    # 정렬 (공정 순서)
    sort_order = Column(Integer, default=0, comment="공정 순서")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

    # Relationships
    work_order = relationship("WorkOrder", backref="process_logs")

    def __repr__(self):
        return f"<WorkOrderProcessLog(wo_id={self.work_order_id}, type={self.process_type}, duration={self.duration_hours}h)>"
