"""
재고 관리 스키마
API 요청/응답을 위한 Pydantic 스키마를 정의합니다.

v0.5.0: 재고관리 기능 추가
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ==================== Enum 정의 ====================

class TransactionType(str, Enum):
    """재고 거래 유형"""
    IN = "IN"           # 입고
    OUT = "OUT"         # 출고
    ADJUST = "ADJUST"   # 조정 (수량 직접 설정)
    RETURN = "RETURN"   # 반품
    COUNT = "COUNT"     # 실사


class InventoryStatus(str, Enum):
    """재고 상태"""
    NORMAL = "NORMAL"           # 정상
    LOW = "LOW"                 # 부족 (재주문점 미만)
    EXCESS = "EXCESS"           # 과잉 (추후 확장용)
    OUT_OF_STOCK = "OUT_OF_STOCK"  # 재고없음


# ==================== 부품 정보 (간략) ====================

class PartInfo(BaseModel):
    """부품 간략 정보 (재고 응답용)"""
    id: int
    part_number: str
    part_number_display: Optional[str] = None
    part_name: str
    part_name_en: Optional[str] = None
    specification: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== 재고 (Inventory) 스키마 ====================

class InventoryBase(BaseModel):
    """재고 기본 스키마"""
    part_id: int = Field(..., description="부품 ID")
    quantity_on_hand: Decimal = Field(default=Decimal(0), description="현재고")
    reorder_point: Optional[Decimal] = Field(None, description="재주문점")
    reorder_qty: Optional[Decimal] = Field(None, description="재주문량")
    unit_cost: Optional[Decimal] = Field(None, description="단가")
    remarks: Optional[str] = Field(None, description="비고")


class InventoryCreate(InventoryBase):
    """재고 생성 스키마"""
    pass


class InventoryUpdate(BaseModel):
    """재고 수정 스키마 (수량 제외 - 조정 API 사용)"""
    reorder_point: Optional[Decimal] = Field(None, description="재주문점")
    reorder_qty: Optional[Decimal] = Field(None, description="재주문량")
    unit_cost: Optional[Decimal] = Field(None, description="단가")
    remarks: Optional[str] = Field(None, description="비고")


class InventoryAdjust(BaseModel):
    """재고 조정 스키마"""
    quantity: Decimal = Field(..., description="조정 수량")
    transaction_type: TransactionType = Field(..., description="거래 유형 (IN/OUT/ADJUST)")
    reason: Optional[str] = Field(None, description="사유")
    reference_type: Optional[str] = Field(None, description="참조 유형 (PO/MO/SO/MANUAL)")
    reference_id: Optional[str] = Field(None, description="참조 문서 번호")
    remarks: Optional[str] = Field(None, description="비고")
    # 로트 생성 옵션 (입고 시 사용)
    create_lot: Optional[bool] = Field(None, description="로트 함께 생성 여부 (입고 시)")
    lot_number: Optional[str] = Field(None, description="로트 번호 (비워두면 자동생성)")
    unit_cost: Optional[Decimal] = Field(None, description="입고 단가")


class InventoryResponse(BaseModel):
    """재고 응답 스키마"""
    id: int
    part_id: int
    quantity_on_hand: Decimal
    quantity_reserved: Optional[Decimal] = None
    quantity_available: Optional[Decimal] = None
    reorder_point: Optional[Decimal] = None
    reorder_qty: Optional[Decimal] = None
    warehouse_location_id: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    status: InventoryStatus
    last_count_date: Optional[datetime] = None
    remarks: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # 부품 정보 (조인)
    part: Optional[PartInfo] = None

    class Config:
        from_attributes = True


class InventoryListResponse(BaseModel):
    """재고 목록 응답 스키마 (간략)"""
    id: int
    part_id: int
    quantity_on_hand: Decimal
    reorder_point: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    status: InventoryStatus
    updated_at: Optional[datetime] = None

    # 부품 정보 (조인)
    part: Optional[PartInfo] = None

    class Config:
        from_attributes = True


class InventorySearchParams(BaseModel):
    """재고 검색 파라미터"""
    keyword: Optional[str] = Field(None, description="검색 키워드 (품번, 부품명)")
    status: Optional[InventoryStatus] = Field(None, description="상태 필터")
    low_stock_only: bool = Field(default=False, description="부족 재고만 조회")

    # 페이지네이션
    skip: int = Field(default=0, ge=0, description="건너뛸 개수")
    limit: int = Field(default=50, ge=1, le=1000, description="조회 개수")
    order_by: str = Field(default="updated_at", description="정렬 기준 컬럼")
    order_desc: bool = Field(default=True, description="내림차순 정렬 여부")


class InventoryPaginatedResponse(BaseModel):
    """재고 목록 페이지네이션 응답"""
    items: List[InventoryListResponse] = Field(description="재고 목록")
    total: int = Field(description="총 개수")
    skip: int = Field(description="건너뛴 개수")
    limit: int = Field(description="조회 개수")
    has_more: bool = Field(description="추가 데이터 존재 여부")


# ==================== 재고 거래 (InventoryTransaction) 스키마 ====================

class InventoryTransactionCreate(BaseModel):
    """재고 거래 생성 스키마 (내부용)"""
    inventory_id: Optional[int] = Field(None, description="재고 ID")
    part_id: int = Field(..., description="부품 ID")
    transaction_type: TransactionType = Field(..., description="거래 유형")
    quantity: Decimal = Field(..., description="변동 수량")
    quantity_before: Optional[Decimal] = Field(None, description="변동 전 수량")
    quantity_after: Optional[Decimal] = Field(None, description="변동 후 수량")
    reference_type: Optional[str] = Field(None, description="참조 유형")
    reference_id: Optional[str] = Field(None, description="참조 문서 번호")
    reason: Optional[str] = Field(None, description="사유")
    remarks: Optional[str] = Field(None, description="비고")
    created_by: Optional[int] = Field(None, description="생성자 ID")


class InventoryTransactionResponse(BaseModel):
    """재고 거래 응답 스키마"""
    id: int
    inventory_id: Optional[int] = None
    part_id: int
    transaction_type: TransactionType
    quantity: Decimal
    quantity_before: Optional[Decimal] = None
    quantity_after: Optional[Decimal] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    reason: Optional[str] = None
    remarks: Optional[str] = None
    document_files: Optional[List] = None  # v0.6.0 추가
    transaction_date: datetime
    created_by: Optional[int] = None
    created_at: datetime

    # 부품 정보 (조인)
    part: Optional[PartInfo] = None

    class Config:
        from_attributes = True


class InventoryTransactionSearchParams(BaseModel):
    """재고 거래 검색 파라미터"""
    inventory_id: Optional[int] = Field(None, description="재고 ID 필터")
    part_id: Optional[int] = Field(None, description="부품 ID 필터")
    transaction_type: Optional[TransactionType] = Field(None, description="거래 유형 필터")
    from_date: Optional[datetime] = Field(None, description="시작일")
    to_date: Optional[datetime] = Field(None, description="종료일")

    # 페이지네이션
    skip: int = Field(default=0, ge=0, description="건너뛸 개수")
    limit: int = Field(default=50, ge=1, le=1000, description="조회 개수")
    order_by: str = Field(default="transaction_date", description="정렬 기준 컬럼")
    order_desc: bool = Field(default=True, description="내림차순 정렬 여부")


class InventoryTransactionPaginatedResponse(BaseModel):
    """재고 거래 목록 페이지네이션 응답"""
    items: List[InventoryTransactionResponse] = Field(description="거래 이력 목록")
    total: int = Field(description="총 개수")
    skip: int = Field(description="건너뛴 개수")
    limit: int = Field(description="조회 개수")
    has_more: bool = Field(description="추가 데이터 존재 여부")
