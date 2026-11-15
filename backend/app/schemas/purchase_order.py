"""
발주서 스키마
API 요청/응답을 위한 Pydantic 스키마를 정의합니다.

v0.6.0: 입출고 관리 기능 추가
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ==================== Enum 정의 ====================

class PurchaseOrderStatus(str, Enum):
    """발주서 상태 (결재는 is_paid 필드로 별도 관리)"""
    DRAFT = "DRAFT"           # 작성중
    ORDERED = "ORDERED"       # 주문완료
    CONFIRMED = "CONFIRMED"   # 납기확정
    RECEIVED = "RECEIVED"     # 입고완료
    COMPLETED = "COMPLETED"   # [DEPRECATED] 기존 데이터 호환용 - 새 데이터는 is_paid 사용
    CANCELLED = "CANCELLED"   # 취소


# ==================== 참조 정보 (간략) ====================

class PartInfo(BaseModel):
    """부품 간략 정보"""
    id: int
    part_number: str
    part_number_display: Optional[str] = None
    part_name: str
    part_name_en: Optional[str] = None
    specification: Optional[str] = None

    class Config:
        from_attributes = True


class SupplierInfo(BaseModel):
    """공급업체 간략 정보"""
    id: int
    partner_code: str
    partner_name: str
    business_number: Optional[str] = None
    manager_name: Optional[str] = None
    tel: Optional[str] = None

    class Config:
        from_attributes = True


class UnitInfo(BaseModel):
    """단위 간략 정보"""
    id: int
    code: str
    name_ko: str

    class Config:
        from_attributes = True


# ==================== 발주서 항목 (PurchaseOrderItem) 스키마 ====================

class PurchaseOrderItemBase(BaseModel):
    """발주서 항목 기본 스키마"""
    # v0.91.0 BOM 미등록(자유입력) 품목 지원: part_id 또는 custom_product_name 중 하나 필수
    part_id: Optional[int] = Field(None, description="부품 ID (BOM 등록 품목)")
    custom_product_code: Optional[str] = Field(None, max_length=100, description="BOM 미등록 품목 품번(자유입력)")
    custom_product_name: Optional[str] = Field(None, max_length=200, description="BOM 미등록 품목 품명(자유입력)")
    ordered_quantity: Decimal = Field(..., gt=0, description="발주 수량")
    unit_price: Decimal = Field(..., ge=0, description="단가")
    unit_id: Optional[int] = Field(None, description="단위 ID")
    line_remarks: Optional[str] = Field(None, description="항목 비고")
    sort_order: int = Field(default=0, description="정렬순서")

    @model_validator(mode="after")
    def _require_part_or_custom(self):
        if not self.part_id and not (self.custom_product_name and self.custom_product_name.strip()):
            raise ValueError("part_id 또는 custom_product_name 중 하나는 필수입니다.")
        return self


class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    """발주서 항목 생성 스키마"""
    pass


class PurchaseOrderItemUpdate(BaseModel):
    """발주서 항목 수정 스키마"""
    ordered_quantity: Optional[Decimal] = Field(None, gt=0, description="발주 수량")
    unit_price: Optional[Decimal] = Field(None, ge=0, description="단가")
    unit_id: Optional[int] = Field(None, description="단위 ID")
    line_remarks: Optional[str] = Field(None, description="항목 비고")
    sort_order: Optional[int] = Field(None, description="정렬순서")


class PurchaseOrderItemResponse(BaseModel):
    """발주서 항목 응답 스키마"""
    id: int
    purchase_order_id: int
    part_id: Optional[int] = None
    custom_product_code: Optional[str] = None
    custom_product_name: Optional[str] = None
    ordered_quantity: Decimal
    received_quantity: Decimal
    defective_quantity: Decimal
    unit_price: Decimal
    line_total: Optional[Decimal] = None
    unit_id: Optional[int] = None
    line_remarks: Optional[str] = None
    sort_order: int

    # 조인된 정보
    part: Optional[PartInfo] = None
    unit: Optional[UnitInfo] = None

    class Config:
        from_attributes = True


# ==================== 입고 처리 스키마 ====================

class ReceiveItemRequest(BaseModel):
    """입고 항목 요청 스키마"""
    item_id: int = Field(..., description="발주 항목 ID")
    received_quantity: Decimal = Field(..., ge=0, description="입고 수량")
    defective_quantity: Decimal = Field(default=Decimal(0), ge=0, description="불량 수량")
    # 최종 입고 시 가격 조정 (선택사항)
    final_unit_price: Optional[Decimal] = Field(None, ge=0, description="최종 단가 (조정)")
    final_line_total: Optional[Decimal] = Field(None, ge=0, description="최종 총액 (조정)")


class ReceiveRequest(BaseModel):
    """입고 처리 요청 스키마"""
    items: List[ReceiveItemRequest] = Field(..., min_length=1, description="입고 항목 목록")
    actual_delivery_date: Optional[date] = Field(None, description="실제 입고일")
    remarks: Optional[str] = Field(None, description="비고")
    is_final_receive: bool = Field(default=False, description="최종 입고 여부 (가격 조정 시 True)")


# ==================== 발주서 (PurchaseOrder) 스키마 ====================

class PurchaseOrderBase(BaseModel):
    """발주서 기본 스키마"""
    supplier_id: int = Field(..., description="공급업체 ID")
    order_date: date = Field(..., description="발주일")
    expected_delivery_date: Optional[date] = Field(None, description="예상 납기일")
    currency: str = Field(default="KRW", description="통화")
    payment_terms: Optional[str] = Field(None, description="결제 조건")
    delivery_terms: Optional[str] = Field(None, description="납품 조건")
    remarks: Optional[str] = Field(None, description="비고")


class PurchaseOrderCreate(PurchaseOrderBase):
    """발주서 생성 스키마"""
    items: Optional[List[PurchaseOrderItemCreate]] = Field(default=[], description="발주 항목 목록")


class PurchaseOrderUpdate(BaseModel):
    """발주서 수정 스키마 (DRAFT 상태에서만)"""
    supplier_id: Optional[int] = Field(None, description="공급업체 ID")
    order_date: Optional[date] = Field(None, description="발주일")
    expected_delivery_date: Optional[date] = Field(None, description="예상 납기일")
    currency: Optional[str] = Field(None, description="통화")
    payment_terms: Optional[str] = Field(None, description="결제 조건")
    delivery_terms: Optional[str] = Field(None, description="납품 조건")
    remarks: Optional[str] = Field(None, description="비고")


class PurchaseOrderResponse(BaseModel):
    """발주서 응답 스키마"""
    id: int
    po_number: str
    supplier_id: int
    order_date: date
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    total_amount: Decimal
    currency: str
    tax_amount: Decimal
    discount_amount: Decimal
    status: PurchaseOrderStatus
    is_paid: bool = False
    paid_date: Optional[date] = None
    paid_amount: Optional[Decimal] = None
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    remarks: Optional[str] = None
    document_files: Optional[List[Any]] = None
    # v0.98.0 기안 파생(항목 수정 잠금) · 발송 완료
    source_approval_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    sent_by: Optional[int] = None
    disbursement_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None

    # 조인된 정보
    supplier: Optional[SupplierInfo] = None
    items: Optional[List[PurchaseOrderItemResponse]] = None

    class Config:
        from_attributes = True


class PurchaseOrderListResponse(BaseModel):
    """발주서 목록 응답 스키마 (간략)"""
    id: int
    po_number: str
    supplier_id: int
    order_date: date
    expected_delivery_date: Optional[date] = None
    total_amount: Decimal
    status: PurchaseOrderStatus
    is_paid: bool = False
    source_approval_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    disbursement_id: Optional[int] = None
    created_at: datetime

    # 조인된 정보
    supplier: Optional[SupplierInfo] = None
    item_count: Optional[int] = None  # 항목 수

    class Config:
        from_attributes = True


class PurchaseOrderPaginatedResponse(BaseModel):
    """발주서 목록 페이지네이션 응답"""
    items: List[PurchaseOrderListResponse] = Field(description="발주서 목록")
    total: int = Field(description="총 개수")
    skip: int = Field(description="건너뛴 개수")
    limit: int = Field(description="조회 개수")
    has_more: bool = Field(description="추가 데이터 존재 여부")


# ==================== 납기 확정 스키마 ====================

class ConfirmDeliveryRequest(BaseModel):
    """납기 확정 요청 스키마"""
    expected_delivery_date: date = Field(..., description="확정 납기일")
    remarks: Optional[str] = Field(None, description="비고")


class PaymentRequest(BaseModel):
    """결제 처리 요청 스키마"""
    is_paid: bool = Field(..., description="결제 여부")
    paid_date: Optional[date] = Field(None, description="결제일")
    paid_amount: Optional[Decimal] = Field(None, description="결제 금액")
