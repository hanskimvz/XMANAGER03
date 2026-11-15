"""
재고 로트 스키마 (v0.7.0)
로트 추적 및 FIFO 출고 관련 스키마
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 기본 정보 스키마 ====================

class PartInfo(BaseModel):
    """부품 간략 정보"""
    id: int
    part_number: str
    part_number_display: Optional[str] = None
    part_name: str
    specification: Optional[str] = None

    class Config:
        from_attributes = True


class SupplierInfo(BaseModel):
    """공급업체 간략 정보"""
    id: int
    partner_code: str
    partner_name: str

    class Config:
        from_attributes = True


class PurchaseOrderInfo(BaseModel):
    """발주서 간략 정보"""
    id: int
    po_number: str
    order_date: date

    class Config:
        from_attributes = True


# ==================== 로트 스키마 ====================

class InventoryLotBase(BaseModel):
    """로트 기본 스키마"""
    lot_number: str = Field(..., max_length=50, description="로트/배치 번호")
    quantity_received: Decimal = Field(..., ge=0, description="입고 수량")
    received_date: Optional[datetime] = Field(None, description="입고일시")
    expiry_date: Optional[date] = Field(None, description="유효기간")
    supplier_lot_number: Optional[str] = Field(None, max_length=50, description="공급업체 로트번호")
    unit_cost: Optional[Decimal] = Field(None, ge=0, description="입고 단가")
    remarks: Optional[str] = Field(None, description="비고")


class InventoryLotCreate(InventoryLotBase):
    """로트 생성 스키마"""
    part_id: int = Field(..., description="부품 ID")
    purchase_order_id: Optional[int] = Field(None, description="발주서 ID")
    supplier_id: Optional[int] = Field(None, description="공급업체 ID")
    warehouse_location_id: Optional[int] = Field(None, description="보관위치 ID")


class InventoryLotUpdate(BaseModel):
    """로트 수정 스키마"""
    expiry_date: Optional[date] = None
    supplier_lot_number: Optional[str] = None
    warehouse_location_id: Optional[int] = None
    remarks: Optional[str] = None


class InventoryLotResponse(InventoryLotBase):
    """로트 응답 스키마"""
    id: int
    part_id: int
    quantity_on_hand: Decimal
    quantity_issued: Decimal
    status: str
    purchase_order_id: Optional[int] = None
    supplier_id: Optional[int] = None
    warehouse_location_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 관계 데이터
    part: Optional[PartInfo] = None
    supplier: Optional[SupplierInfo] = None
    purchase_order: Optional[PurchaseOrderInfo] = None

    class Config:
        from_attributes = True


class InventoryLotListItem(BaseModel):
    """로트 목록 아이템 (가벼운 응답)"""
    id: int
    part_id: int
    lot_number: str
    quantity_received: Decimal
    quantity_on_hand: Decimal
    quantity_issued: Decimal
    received_date: datetime
    expiry_date: Optional[date] = None
    status: str
    supplier_lot_number: Optional[str] = None
    unit_cost: Optional[Decimal] = None
    supplier_id: Optional[int] = None
    supplier: Optional[SupplierInfo] = None  # 공급업체 정보

    class Config:
        from_attributes = True


# ==================== FIFO 출고 관련 스키마 ====================

class FIFOLotSuggestion(BaseModel):
    """FIFO 출고 제안 로트"""
    lot_id: int
    lot_number: str
    received_date: datetime
    available_quantity: Decimal
    suggested_quantity: Decimal
    expiry_date: Optional[date] = None
    unit_cost: Optional[Decimal] = None
    supplier_name: Optional[str] = None  # 공급업체명


class FIFOSuggestionResponse(BaseModel):
    """FIFO 출고 제안 응답"""
    part_id: int
    requested_quantity: Decimal
    is_sufficient: bool
    total_available: Decimal
    shortage: Decimal
    lots: List[FIFOLotSuggestion]


# ==================== 로트별 출고 스키마 ====================

class LotIssueItem(BaseModel):
    """로트별 출고 항목"""
    lot_id: int = Field(..., description="로트 ID")
    quantity: Decimal = Field(..., gt=0, description="출고 수량")


class WorkOrderItemIssueRequest(BaseModel):
    """작업지시서 항목 출고 요청"""
    item_id: int = Field(..., description="작업지시서 항목 ID")
    issue_quantity: Decimal = Field(..., gt=0, description="출고 수량")
    use_fifo: bool = Field(True, description="FIFO 자동 적용 여부")
    lot_selections: Optional[List[LotIssueItem]] = Field(None, description="수동 로트 선택 (use_fifo=False일 때)")


class WorkOrderIssueRequest(BaseModel):
    """작업지시서 출고 요청 (전체)"""
    items: List[WorkOrderItemIssueRequest]


class WorkOrderItemIssueResponse(BaseModel):
    """작업지시서 항목 출고 응답"""
    id: int
    work_order_item_id: int
    lot_id: Optional[int] = None
    lot_number: Optional[str] = None
    quantity: Decimal
    issue_date: datetime
    returned_quantity: Decimal

    class Config:
        from_attributes = True


# ==================== 생산 가용수량 체크 스키마 ====================

class BOMItemAvailability(BaseModel):
    """BOM 항목별 가용수량"""
    part_id: int
    part_number: str
    part_name: str
    required_per_unit: Decimal  # 단위당 소요량
    required_quantity: Decimal  # 전체 필요량
    available_quantity: Decimal  # 가용 재고
    shortage: Decimal  # 부족량
    status: str  # SUFFICIENT / INSUFFICIENT / OUT_OF_STOCK


class LimitingPart(BaseModel):
    """제한 부품 (병목)"""
    part_id: int
    part_number: str
    part_name: str
    required_per_unit: Decimal
    available_quantity: Decimal
    can_produce: int  # 생산 가능 수량


class ProductionAvailabilityResponse(BaseModel):
    """생산 가용수량 체크 응답"""
    product_part_id: int
    requested_quantity: Decimal
    can_produce: int  # 현재 재고로 생산 가능한 최대 수량
    limiting_parts: List[LimitingPart]  # 병목 부품 목록
    items: List[BOMItemAvailability]  # 전체 BOM 항목별 상태


# ==================== 페이지네이션 ====================

class PaginatedLotResponse(BaseModel):
    """페이지네이션 로트 응답"""
    items: List[InventoryLotListItem]
    total: int
    skip: int
    limit: int
    has_more: bool
