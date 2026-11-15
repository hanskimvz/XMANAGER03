"""
거래처 배송지 모델 (v0.58.0)
한 거래처에 여러 배송지(수령처)를 등록. 회사 주소와 배송지가 다른 경우 대응.
문서(견적서/PI/CI)에서 저장된 배송지를 선택 → ship_to_address_id 로 참조.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.core.database import Base


class BusinessPartnerShippingAddress(Base):
    __tablename__ = "business_partner_shipping_address"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("business_partner.id", ondelete="CASCADE"), nullable=False, index=True)

    label = Column(String(100), comment="배송지 이름표 (예: 본사/○○물류창고)")
    name = Column(String(200), comment="수령처명 (회사/이름)")
    address = Column(Text, comment="배송 주소")
    contact = Column(String(100), comment="수령 담당자")
    phone = Column(String(50), comment="전화")
    email = Column(String(200), comment="이메일")

    is_default = Column(Boolean, default=False, server_default="false", comment="기본 배송지 여부")
    sort_order = Column(Integer, default=0, server_default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    partner = relationship("BusinessPartner",
                           backref=backref("shipping_addresses", cascade="all, delete-orphan", passive_deletes=True))
