"""
가격 이력 스키마
API 요청/응답을 위한 Pydantic 스키마를 정의합니다.

v0.18.0: 원가관리 기능 추가
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ==================== Enums ====================

class PriceType(str, Enum):
    """가격 유형"""
    PURCHASE = "PURCHASE"      # 구매 단가 (발주/입고 시)
    STANDARD = "STANDARD"      # 기준단가 변경
    MANUAL = "MANUAL"          # 수동 입력
    QUOTE = "QUOTE"            # 견적가


class Currency(str, Enum):
    """통화 코드"""
    KRW = "KRW"  # 원화
    USD = "USD"  # 미국 달러
    EUR = "EUR"  # 유로
    JPY = "JPY"  # 일본 엔
    CNY = "CNY"  # 중국 위안
    GBP = "GBP"  # 영국 파운드


# ==================== 가격 이력 스키마 ====================

class PriceHistoryBase(BaseModel):
    """가격 이력 기본 스키마"""
    part_id: int = Field(..., description="부품 ID")
    price_type: PriceType = Field(default=PriceType.PURCHASE, description="가격유형")
    unit_price: Decimal = Field(..., description="단가")
    currency: str = Field(default="KRW", max_length=10, description="통화")
    exchange_rate: Optional[Decimal] = Field(default=1, description="환율")
    quantity: Optional[Decimal] = Field(None, description="수량")
    supplier_id: Optional[int] = Field(None, description="공급업체 ID")
    reference_type: Optional[str] = Field(None, max_length=30, description="참조유형")
    reference_id: Optional[str] = Field(None, max_length=50, description="참조문서번호")
    reference_date: Optional[datetime] = Field(None, description="참조일자")
    remarks: Optional[str] = Field(None, description="비고")


class PriceHistoryCreate(PriceHistoryBase):
    """가격 이력 생성 스키마"""
    pass


class PriceHistoryResponse(PriceHistoryBase):
    """가격 이력 응답 스키마"""
    id: int
    unit_price_krw: Optional[Decimal] = Field(None, description="원화 환산 단가")
    created_by: Optional[int] = None
    created_at: datetime

    # 관계 데이터
    supplier_name: Optional[str] = Field(None, description="공급업체명")

    class Config:
        from_attributes = True


class PriceHistoryListResponse(BaseModel):
    """가격 이력 목록 응답"""
    items: List[PriceHistoryResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


# ==================== 환율 스키마 ====================

class ExchangeRateBase(BaseModel):
    """환율 기본 스키마"""
    currency_code: str = Field(..., max_length=10, description="통화코드")
    currency_name: Optional[str] = Field(None, max_length=50, description="통화명")
    rate: Decimal = Field(..., description="환율 (1 외화 = ? KRW)")
    effective_date: datetime = Field(..., description="적용일자")
    expiry_date: Optional[datetime] = Field(None, description="만료일자")
    source: str = Field(default="MANUAL", max_length=20, description="출처")


class ExchangeRateCreate(ExchangeRateBase):
    """환율 생성 스키마"""
    pass


class ExchangeRateUpdate(BaseModel):
    """환율 수정 스키마"""
    rate: Optional[Decimal] = None
    expiry_date: Optional[datetime] = None
    is_active: Optional[str] = None


class ExchangeRateResponse(ExchangeRateBase):
    """환율 응답 스키마"""
    id: int
    is_active: str = "Y"
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 부품 원가 정보 스키마 ====================

class PartPriceInfo(BaseModel):
    """부품 원가 정보 (조회용)"""
    part_id: int
    part_number: str
    part_name: str

    # 기준단가
    standard_price: Decimal = Field(default=0, description="기준단가")
    standard_price_currency: str = Field(default="KRW", description="기준단가 통화")

    # 재고단가 (이동평균)
    inventory_avg_price: Decimal = Field(default=0, description="재고단가")
    inventory_avg_price_currency: str = Field(default="KRW", description="재고단가 통화")

    # 최근단가
    latest_price: Decimal = Field(default=0, description="최근단가")
    latest_price_currency: str = Field(default="KRW", description="최근단가 통화")
    latest_price_date: Optional[datetime] = Field(None, description="최근단가 갱신일")
    latest_price_supplier: Optional[str] = Field(None, description="최근단가 공급업체")

    # 평균단가 (캐시)
    avg_price_30d: Decimal = Field(default=0, description="평균단가 (최근 30일)")
    avg_price_90d: Decimal = Field(default=0, description="평균단가 (최근 90일)")
    avg_price_last5: Decimal = Field(default=0, description="평균단가 (최근 5건)")
    avg_price_last10: Decimal = Field(default=0, description="평균단가 (최근 10건)")

    # BOM 원가 정보 (v0.18.0)
    cost_type: Optional[str] = Field(default="MANUAL", description="원가 유형 (MANUAL/BOM/PROCESS)")
    material_cost: Decimal = Field(default=0, description="재료비")
    material_cost_currency: str = Field(default="KRW", description="재료비 통화")
    labor_cost: Decimal = Field(default=0, description="가공비")
    labor_cost_currency: str = Field(default="KRW", description="가공비 통화")
    overhead_cost: Decimal = Field(default=0, description="경비")
    overhead_cost_currency: str = Field(default="KRW", description="경비 통화")
    calculated_cost: Decimal = Field(default=0, description="계산된 원가")
    calculated_cost_currency: str = Field(default="KRW", description="계산된 원가 통화")
    cost_calculated_at: Optional[datetime] = Field(None, description="원가 계산 일시")

    class Config:
        from_attributes = True


class PartStandardPriceUpdate(BaseModel):
    """부품 기준단가 수정"""
    standard_price: Decimal = Field(..., description="기준단가")
    standard_price_currency: str = Field(default="KRW", description="통화")
    remarks: Optional[str] = Field(None, description="변경 사유")


class AvgPriceRequest(BaseModel):
    """평균단가 계산 요청"""
    part_id: int = Field(..., description="부품 ID")
    # 기간별 계산
    from_date: Optional[datetime] = Field(None, description="시작일")
    to_date: Optional[datetime] = Field(None, description="종료일")
    # 건수별 계산
    last_count: Optional[int] = Field(None, ge=1, le=100, description="최근 N건")
    # 공급업체 필터
    supplier_id: Optional[int] = Field(None, description="공급업체 ID (특정 공급업체만)")


class AvgPriceResponse(BaseModel):
    """평균단가 계산 응답"""
    part_id: int
    avg_price: Decimal = Field(..., description="평균단가")
    avg_price_krw: Decimal = Field(..., description="원화 환산 평균단가")
    currency: str = Field(default="KRW", description="통화")
    count: int = Field(..., description="계산에 사용된 건수")
    from_date: Optional[datetime] = Field(None, description="시작일")
    to_date: Optional[datetime] = Field(None, description="종료일")
    min_price: Decimal = Field(default=0, description="최저가")
    max_price: Decimal = Field(default=0, description="최고가")
