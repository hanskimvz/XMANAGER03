"""
거래처 선불 잔액 관리 (Partner Balance) 모델
선불 입금 → 주문마다 차감하는 Balance Sheet 관리
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PartnerBalanceTransaction(Base):
    """선불 잔액 입출금 이력"""
    __tablename__ = "partner_balance_transaction"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("business_partner.id", ondelete="CASCADE"), nullable=False, index=True)

    # DEPOSIT: 충전(입금), DEDUCT: 차감(PI 입금 처리)
    transaction_type = Column(String(20), nullable=False, comment="거래 유형 (DEPOSIT/DEDUCT)")
    amount = Column(Numeric(15, 2), nullable=False, comment="거래 금액")
    currency = Column(String(10), default="USD", comment="통화")
    balance_after = Column(Numeric(15, 2), nullable=False, comment="거래 후 잔액")

    # 참조 (PI 입금 처리 시)
    reference_doc_number = Column(String(50), comment="참조 문서번호 (PI-xxx)")
    reference_doc_id = Column(Integer, comment="참조 문서 ID")

    memo = Column(Text, comment="메모")
    created_by = Column(String(100), comment="처리자")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    partner = relationship("BusinessPartner", backref="balance_transactions")
