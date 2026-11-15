"""
연차 거래 원장 (v0.45.0)

회계연도 기준 연차의 모든 변동(발생/사용/수당지급/조정)을 한 줄씩 기록하는 단일 진실원천.
- 잔여 = Σ amount (누적). 이월은 별도 행 없이 누적합으로 자연 표현(미사용분이 다음 해로 이어짐).
- amount 부호: 발생/조정(+), 사용/수당지급(−).

설계: 전자결재_연차관리_개발계획.md §3.2
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.sql import func

from app.core.database import Base

# entry_type 값
ENTRY_GRANT = "GRANT"            # 연 발생(회계연도 부여: 첫해 일괄/다음해 일괄/3년차+ 15)
ENTRY_USAGE = "USAGE"            # 사용(승인된 휴가 결재에서 동기화, source_doc_id 연결)
ENTRY_ALLOWANCE_PAID = "ALLOWANCE_PAID"  # 연차수당 지급(연말, 관리자 입력) → 이월에서 차감 효과
ENTRY_ADJUST = "ADJUST"          # 수동 조정/오버라이드(도입 초기 opening 포함)

# source_type 값
SOURCE_AUTO = "AUTO"        # 엔진 자동 생성(발생)
SOURCE_APPROVAL = "APPROVAL"  # 휴가 결재 동기화(사용)
SOURCE_MANUAL = "MANUAL"    # 관리자 수동(수당/조정)


class LeaveLedger(Base):
    """연차 거래 원장 1행 = 한 건의 발생/사용/수당/조정."""
    __tablename__ = "leave_ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False, index=True, comment="귀속 회계연도(YYYY)")
    entry_type = Column(String(20), nullable=False, comment="GRANT/USAGE/ALLOWANCE_PAID/ADJUST")
    amount = Column(Float, nullable=False, comment="발생/조정 +, 사용/수당지급 −")
    event_date = Column(Date, nullable=True, comment="발생/처리일")
    source_type = Column(String(20), nullable=False, default=SOURCE_MANUAL, comment="AUTO/APPROVAL/MANUAL")
    source_doc_id = Column(Integer, ForeignKey("approval_documents.id", ondelete="SET NULL"),
                           nullable=True, comment="USAGE 시 휴가 결재 문서")
    memo = Column(String(300), nullable=True, comment="사유/비고(조정·수당 필수)")
    # v0.56.0: 휴가 취소 시 원 USAGE 행을 삭제하지 않고 무효 처리(빗금 표시 + 잔여 계산 제외)
    voided = Column(Boolean, nullable=False, default=False, server_default="false",
                    comment="취소로 무효화된 행(잔여 합산 제외, 감사용 보존)")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="처리자(관리자)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # 자동 발생(GRANT/AUTO)·결재 사용(USAGE/source_doc)을 멱등 동기화하기 위한 조회 인덱스
        Index("ix_leave_ledger_user_fy", "user_id", "fiscal_year"),
        Index("ix_leave_ledger_user_type", "user_id", "entry_type"),
    )
