"""
가격 이력 (Price History) 모델
부품별 구매 가격 이력을 관리합니다.

v0.18.0: 원가관리 기능 추가
- 모든 입고 건의 단가 기록
- 공급업체별, 기간별 가격 추적
- 평균단가 계산의 기반 데이터
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PriceHistory(Base):
    """
    가격 이력 (Price History)
    부품별 구매 가격 이력을 기록합니다.

    가격 유형(price_type):
    - PURCHASE: 구매 단가 (발주/입고 시)
    - STANDARD: 기준단가 변경
    - MANUAL: 수동 입력
    - QUOTE: 견적가
    """
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 부품 참조 (필수)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True, comment="부품 ID")

    # 가격 정보
    price_type = Column(String(20), nullable=False, default="PURCHASE", index=True, comment="가격유형 (PURCHASE/STANDARD/MANUAL/QUOTE)")
    unit_price = Column(Numeric(15, 4), nullable=False, comment="단가")
    currency = Column(String(10), nullable=False, default="KRW", comment="통화")

    # 원화 환산 (외화인 경우)
    exchange_rate = Column(Numeric(12, 4), default=1, comment="환율 (원화 기준)")
    unit_price_krw = Column(Numeric(15, 4), comment="원화 환산 단가")

    # 수량 정보 (구매 시)
    quantity = Column(Numeric(15, 3), comment="수량")

    # 공급업체 정보
    supplier_id = Column(Integer, ForeignKey("supplier.id", ondelete="SET NULL"), index=True, comment="공급업체 ID")

    # 참조 문서 (발주서, 입고 등)
    reference_type = Column(String(30), comment="참조유형 (PO/RECEIVING/QUOTATION/MANUAL)")
    reference_id = Column(String(50), index=True, comment="참조문서번호")
    reference_date = Column(DateTime(timezone=True), comment="참조일자 (발주일/입고일)")

    # 상세 정보
    remarks = Column(Text, comment="비고")

    # 감사
    created_by = Column(Integer, comment="생성자 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="생성일시")

    # 인덱스 설정
    __table_args__ = (
        # 부품별 + 날짜별 조회 최적화
        Index('ix_price_history_part_date', 'part_id', 'created_at'),
        # 부품별 + 공급업체별 조회 최적화
        Index('ix_price_history_part_supplier', 'part_id', 'supplier_id'),
        # 부품별 + 가격유형별 조회 최적화
        Index('ix_price_history_part_type', 'part_id', 'price_type'),
    )

    # Relationships
    part = relationship("Part")
    supplier = relationship("Supplier")


class ExchangeRate(Base):
    """
    환율 정보 (Exchange Rate)
    외화 가격을 원화로 환산하기 위한 환율 정보

    환율 출처(source):
    - MANUAL: 수동 입력
    - API: 외부 API 연동
    - BANK: 은행 고시환율
    """
    __tablename__ = "exchange_rate"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 통화 정보
    currency_code = Column(String(10), nullable=False, index=True, comment="통화코드 (USD, EUR, JPY 등)")
    currency_name = Column(String(50), comment="통화명 (미국 달러, 유로, 일본 엔 등)")

    # 환율 (원화 기준)
    rate = Column(Numeric(12, 4), nullable=False, comment="환율 (1 외화 = ? KRW)")

    # 유효 기간
    effective_date = Column(DateTime(timezone=True), nullable=False, index=True, comment="적용일자")
    expiry_date = Column(DateTime(timezone=True), comment="만료일자")

    # 출처
    source = Column(String(20), default="MANUAL", comment="출처 (MANUAL/API/BANK)")

    # 상태
    is_active = Column(String(1), default="Y", comment="사용여부 (Y/N)")

    # 감사
    created_by = Column(Integer, comment="생성자 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_by = Column(Integer, comment="수정자 ID")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")

    # 인덱스 설정
    __table_args__ = (
        # 통화별 + 날짜별 조회 최적화
        Index('ix_exchange_rate_currency_date', 'currency_code', 'effective_date'),
    )
