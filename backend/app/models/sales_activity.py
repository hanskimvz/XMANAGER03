"""
영업 대응 현황 (Sales Activity) 모델
고객별 프로젝트 단위로 영업 대응 이력을 추적합니다.

v0.27.0: 초기 구현
"""

from sqlalchemy import Column, Integer, String, Text, Date, Numeric, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SalesActivity(Base):
    """영업 프로젝트 (고객별 대응 건)"""
    __tablename__ = "sales_activity"

    id = Column(Integer, primary_key=True, index=True)

    # 고객 정보
    customer_id = Column(Integer, ForeignKey("business_partner.id"), nullable=True, comment="거래처 ID (선택)")
    customer_name = Column(String(200), comment="거래처명 (직접 입력 또는 BP에서 자동)")
    country = Column(String(100), comment="나라")

    # 프로젝트 정보
    title = Column(String(300), nullable=False, comment="프로젝트명")
    assigned_to = Column(String(100), comment="담당자")
    status = Column(String(20), default="IN_PROGRESS", comment="상태 (IN_PROGRESS/WAITING/COMPLETED/ON_HOLD/DROPPED)")
    inquiry_type = Column(String(20), default="GENERAL", comment="문의 유형 (TECHNICAL/QUOTATION/GENERAL/CLAIM/SAMPLE)")
    # v0.57.0: 우선순위 2축(긴급=시급성, 중요=전략가치) — 상태/유형과 독립
    is_urgent = Column(Boolean, nullable=False, default=False, server_default="false", comment="긴급")
    is_important = Column(Boolean, nullable=False, default=False, server_default="false", comment="중요")

    # 현재 단계 & 다음 단계 & 지연 사유
    current_step = Column(Text, comment="현재 진행 단계")
    next_step = Column(Text, comment="다음 필요 단계")
    pending_reason = Column(Text, comment="지연 사유")

    # 부가 정보
    expected_amount = Column(Numeric(15, 2), comment="예상 금액")
    expected_currency = Column(String(3), default="KRW", comment="통화")

    # Nextcloud 저장 폴더(베이스 기준 상대경로) — 이 영업 건 문서 PDF 자동 저장 위치
    nextcloud_folder = Column(String(500), nullable=True, comment="Nextcloud 저장 폴더(상대경로)")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계
    customer = relationship("BusinessPartner", foreign_keys=[customer_id])
    logs = relationship("SalesActivityLog", back_populates="activity", cascade="all, delete-orphan",
                        order_by="desc(SalesActivityLog.created_at)")


class SalesActivityLog(Base):
    """영업 대응 이력 (코멘트, 변경 이력)"""
    __tablename__ = "sales_activity_log"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("sales_activity.id", ondelete="CASCADE"), nullable=False)

    # 로그 유형 (v0.31.0):
    # COMMENT - 사용자 코멘트
    # NEXT_STEP - 다음 단계 변경
    # PENDING_REASON - 지연 사유 변경
    # STATUS - 상태 변경
    # INQUIRY_TYPE - 문의 유형 변경
    # ASSIGNEE - 담당자 변경
    log_type = Column(String(20), nullable=False, default="COMMENT", server_default="COMMENT", comment="로그 유형")

    content = Column(Text, nullable=False, comment="로그 내용")
    logged_by = Column(String(100), comment="작성자")

    # v0.78.0 코멘트 첨부 이미지/파일 [{filename, filepath, mimetype, size}]
    attachment_files = Column(JSON, comment="코멘트 첨부(스크린샷/사진) 목록 (JSON)")

    # v0.80.0 수정 기록 (누가/언제 수정했는지)
    edited_by = Column(String(100), comment="마지막 수정자")
    edited_at = Column(DateTime(timezone=True), comment="마지막 수정 시각")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    activity = relationship("SalesActivity", back_populates="logs")
