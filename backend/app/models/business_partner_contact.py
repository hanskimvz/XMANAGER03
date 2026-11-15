"""
거래처 담당자 모델 (v0.31.0)
한 거래처에 여러 담당자를 등록할 수 있습니다.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.core.database import Base


class BusinessPartnerContact(Base):
    __tablename__ = "business_partner_contact"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("business_partner.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(100), nullable=False, comment="담당자명")
    position = Column(String(50), comment="직책")
    role = Column(String(20), comment="역할 (PURCHASING/TECHNICAL/SALES/GENERAL)")
    email = Column(String(200))
    tel_office = Column(String(50), comment="사무실 전화")
    tel_mobile = Column(String(50), comment="휴대폰")

    is_primary = Column(Boolean, default=False, server_default="false", comment="기본 담당자 여부")
    sort_order = Column(Integer, default=0, server_default="0")
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계
    partner = relationship("BusinessPartner", backref=backref("contacts", cascade="all, delete-orphan", passive_deletes=True))
