"""
거래처 메모/노트 모델
업체별 정성적 이력(전략 메모, 주의사항, 내부 평가 등)을 시간순으로 관리합니다.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PartnerNote(Base):
    __tablename__ = "partner_note"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("business_partner.id", ondelete="CASCADE"), nullable=False, index=True)

    note_type = Column(String(20), nullable=False, default="GENERAL",
                       comment="메모 유형 (GENERAL/STRATEGY/RISK/MEETING/INTERNAL)")
    content = Column(Text, nullable=False, comment="메모 내용")
    is_pinned = Column(Boolean, default=False, comment="상단 고정 여부")
    created_by = Column(String(100), comment="작성자")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계
    partner = relationship("BusinessPartner", backref="notes")
