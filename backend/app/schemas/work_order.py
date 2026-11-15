"""
작업지시서 스키마
API 요청/응답을 위한 Pydantic 스키마를 정의합니다.

v0.6.0: 입출고 관리 기능 추가
v0.19.0: 다중 제품 지원
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ==================== Enum 정의 ====================

class WorkOrderStatus(str, Enum):
    """작업지시서 상태 (7단계)"""
    RECEIVED = "RECEIVED"         # 접수
    APPROVED = "APPROVED"         # 승인
    ISSUED = "ISSUED"             # 부품출고
    IN_PROGRESS = "IN_PROGRESS"   # 작업중
    INSPECTION = "INSPECTION"     # 검사
    PACKED = "PACKED"             # 포장완료
    SHIPPED = "SHIPPED"           # 출하완료
    CANCELLED = "CANCELLED"       # 취소


class WorkOrderPriority(int, Enum):
    """작업지시서 우선순위"""
    NORMAL = 0    # 보통
    HIGH = 1      # 높음
    URGENT = 2    # 긴급


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


class CustomerInfo(BaseModel):
    """고객사 간략 정보"""
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


# ==================== 작업지시서 항목 (WorkOrderItem) 스키마 ====================

class WorkOrderItemBase(BaseModel):
    """작업지시서 항목 기본 스키마"""
    part_id: int = Field(..., description="부품 ID")
    required_quantity: Decimal = Field(..., gt=0, description="필요 수량")
    unit_id: Optional[int] = Field(None, description="단위 ID")
    bom_level: int = Field(default=1, description="BOM 레벨")
    line_remarks: Optional[str] = Field(None, description="항목 비고")
    sort_order: int = Field(default=0, description="정렬순서")


class WorkOrderItemCreate(WorkOrderItemBase):
    """작업지시서 항목 생성 스키마 (수동 추가용)"""
    bom_id: Optional[int] = Field(None, description="BOM ID")


class WorkOrderItemResponse(BaseModel):
    """작업지시서 항목 응답 스키마 (v0.19.0 다중 제품 지원)"""
    id: int
    work_order_id: int
    work_order_product_id: Optional[int] = None  # v0.19.0: 어느 제품의 BOM인지
    part_id: int
    bom_id: Optional[int] = None
    required_quantity: Decimal
    issued_quantity: Decimal
    additional_quantity: Decimal
    returned_quantity: Decimal
    unit_id: Optional[int] = None
    bom_level: int
    line_remarks: Optional[str] = None
    sort_order: int

    # 조인된 정보
    part: Optional[PartInfo] = None
    unit: Optional[UnitInfo] = None

    # 계산된 필드
    total_issued: Optional[Decimal] = None  # issued + additional
    pending_quantity: Optional[Decimal] = None  # required - total_issued + returned

    class Config:
        from_attributes = True


# ==================== 부품 출고 스키마 ====================

class IssueItemRequest(BaseModel):
    """출고 항목 요청 스키마"""
    item_id: int = Field(..., description="작업지시서 항목 ID")
    issue_quantity: Decimal = Field(..., ge=0, description="출고 수량")


class IssueRequest(BaseModel):
    """부품 출고 요청 스키마"""
    items: Optional[List[IssueItemRequest]] = Field(None, description="출고 항목 목록 (미지정 시 전체 출고)")
    remarks: Optional[str] = Field(None, description="비고")


class AdditionalIssueRequest(BaseModel):
    """추가 출고 요청 스키마"""
    quantity: Decimal = Field(..., gt=0, description="추가 출고 수량")
    reason: Optional[str] = Field(None, description="추가 출고 사유")


class ReturnRequest(BaseModel):
    """반납 요청 스키마"""
    quantity: Decimal = Field(..., gt=0, description="반납 수량")
    reason: Optional[str] = Field(None, description="반납 사유")


# ==================== 작업지시서 제품 (WorkOrderProduct) 스키마 (v0.19.0) ====================

class WorkOrderProductBase(BaseModel):
    """작업지시서 제품 기본 스키마"""
    product_part_id: int = Field(..., description="제품 부품 ID")
    order_quantity: Decimal = Field(..., gt=0, description="지시 수량")
    line_remarks: Optional[str] = Field(None, description="항목 비고")
    sort_order: int = Field(default=0, description="정렬순서")


class WorkOrderProductCreate(WorkOrderProductBase):
    """작업지시서 제품 생성 스키마"""
    pass


class WorkOrderProductUpdate(BaseModel):
    """작업지시서 제품 수정 스키마"""
    order_quantity: Optional[Decimal] = Field(None, gt=0, description="지시 수량")
    completed_quantity: Optional[Decimal] = Field(None, ge=0, description="완료 수량")
    defective_quantity: Optional[Decimal] = Field(None, ge=0, description="불량 수량")
    line_remarks: Optional[str] = Field(None, description="항목 비고")


class WorkOrderProductResponse(BaseModel):
    """작업지시서 제품 응답 스키마"""
    id: int
    work_order_id: int
    product_part_id: int
    order_quantity: Decimal
    completed_quantity: Decimal
    defective_quantity: Decimal
    sort_order: int
    line_remarks: Optional[str] = None

    # 조인된 정보
    product_part: Optional[PartInfo] = None

    class Config:
        from_attributes = True


# ==================== 작업지시서 (WorkOrder) 스키마 ====================

class WorkOrderBase(BaseModel):
    """작업지시서 기본 스키마 (v0.19.0 다중 제품 지원, v0.20.0 생산요청 연결)"""
    # [DEPRECATED] 단일 제품 필드 - 호환성을 위해 유지
    product_part_id: Optional[int] = Field(None, description="완제품 부품 ID (단일 제품, deprecated)")
    order_quantity: Optional[Decimal] = Field(None, gt=0, description="지시 수량 (단일 제품, deprecated)")

    # v0.20.0: 생산요청 연결
    production_request_id: Optional[int] = Field(None, description="생산요청 ID (생산요청에서 생성된 경우)")

    # v0.31.0: 작업지시 체인
    parent_wo_id: Optional[int] = Field(None, description="상위 WO ID (이 WO의 산출물이 투입되는 WO)")
    target_part_id: Optional[int] = Field(None, description="이 WO에서 만들려는 부품 ID")

    # v0.24.0: 주문 세부유형
    order_subtype: Optional[str] = Field("ASSEMBLED", description="주문 세부유형 (ASSEMBLED/KIT)")

    # 공통 필드
    customer_id: Optional[int] = Field(None, description="고객사 ID")
    customer_order_no: Optional[str] = Field(None, description="고객 주문번호")
    priority: int = Field(default=0, ge=0, le=2, description="우선순위 (0:보통, 1:높음, 2:긴급)")
    remarks: Optional[str] = Field(None, description="비고")

    # 예정일
    issue_scheduled_date: Optional[date] = Field(None, description="부품출고 예정일")
    production_scheduled_date: Optional[date] = Field(None, description="작업 예정일")
    inspection_scheduled_date: Optional[date] = Field(None, description="검사 예정일")
    packing_scheduled_date: Optional[date] = Field(None, description="포장 예정일")
    shipping_scheduled_date: Optional[date] = Field(None, description="출하 예정일")


class WorkOrderCreate(WorkOrderBase):
    """작업지시서 생성 스키마 (v0.19.0 다중 제품 지원)"""
    # v0.19.0: 다중 제품 목록
    products: Optional[List[WorkOrderProductCreate]] = Field(default=[], description="제품 목록 (다중 제품)")

    # BOM 자동 전개 여부 (기본: True)
    auto_expand_bom: bool = Field(default=True, description="BOM 자동 전개 여부")
    # 수동 항목 추가 (BOM 미사용 시)
    items: Optional[List[WorkOrderItemCreate]] = Field(default=[], description="수동 추가 항목")

    @model_validator(mode='after')
    def validate_products(self):
        """products 또는 product_part_id 중 하나는 필수"""
        if not self.products and not self.product_part_id:
            raise ValueError("products 또는 product_part_id 중 하나는 필수입니다.")
        # 단일 제품 필드가 있으면 products로 변환
        if self.product_part_id and self.order_quantity and not self.products:
            self.products = [WorkOrderProductCreate(
                product_part_id=self.product_part_id,
                order_quantity=self.order_quantity,
                sort_order=0
            )]
        return self


class WorkOrderUpdate(BaseModel):
    """작업지시서 수정 스키마 (RECEIVED 상태에서만)"""
    order_subtype: Optional[str] = Field(None, description="주문 세부유형 (ASSEMBLED/KIT)")
    customer_id: Optional[int] = Field(None, description="고객사 ID")
    customer_order_no: Optional[str] = Field(None, description="고객 주문번호")
    order_quantity: Optional[Decimal] = Field(None, gt=0, description="지시 수량 (deprecated)")
    priority: Optional[int] = Field(None, ge=0, le=2, description="우선순위")
    remarks: Optional[str] = Field(None, description="비고")

    # v0.19.0: 제품 수정
    products: Optional[List[WorkOrderProductCreate]] = Field(None, description="제품 목록 (다중 제품)")

    # 예정일 수정
    issue_scheduled_date: Optional[date] = Field(None, description="부품출고 예정일")
    production_scheduled_date: Optional[date] = Field(None, description="작업 예정일")
    inspection_scheduled_date: Optional[date] = Field(None, description="검사 예정일")
    packing_scheduled_date: Optional[date] = Field(None, description="포장 예정일")
    shipping_scheduled_date: Optional[date] = Field(None, description="출하 예정일")

    # v0.24.0: 포장 상세 정보
    packaging_boxes: Optional[int] = Field(None, ge=0, description="포장 박스 수")
    packaging_dimensions: Optional[str] = Field(None, max_length=100, description="박스 치수 (LxWxH cm)")
    packaging_gross_weight: Optional[Decimal] = Field(None, ge=0, description="총중량 (kg)")
    packaging_net_weight: Optional[Decimal] = Field(None, ge=0, description="순중량 (kg)")


class WorkOrderResponse(BaseModel):
    """작업지시서 응답 스키마 (v0.19.0 다중 제품 지원)"""
    id: int
    wo_number: str
    product_part_id: Optional[int] = None  # deprecated - 호환성용
    production_request_id: Optional[int] = None  # v0.22.0: 생산요청 ID
    parent_wo_id: Optional[int] = None  # v0.31.0: 상위 WO
    target_part_id: Optional[int] = None  # v0.31.0: 목적 부품
    customer_id: Optional[int] = None
    customer_order_no: Optional[str] = None
    order_quantity: Optional[Decimal] = None  # deprecated - 호환성용
    completed_quantity: Optional[Decimal] = None  # deprecated - 호환성용
    defective_quantity: Optional[Decimal] = None  # deprecated - 호환성용
    status: WorkOrderStatus
    priority: int

    # 단계별 일시
    received_date: Optional[datetime] = None
    approved_date: Optional[datetime] = None
    approved_by: Optional[int] = None
    issue_scheduled_date: Optional[date] = None
    issue_completed_date: Optional[datetime] = None
    production_scheduled_date: Optional[date] = None
    production_start_date: Optional[datetime] = None
    production_end_date: Optional[datetime] = None
    inspection_scheduled_date: Optional[date] = None
    inspection_completed_date: Optional[datetime] = None
    packing_scheduled_date: Optional[date] = None
    packing_completed_date: Optional[datetime] = None
    shipping_scheduled_date: Optional[date] = None
    shipping_completed_date: Optional[datetime] = None

    remarks: Optional[str] = None
    document_files: Optional[List[Any]] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None

    # v0.24.0
    order_subtype: Optional[str] = None
    packaging_boxes: Optional[int] = None
    packaging_dimensions: Optional[str] = None
    packaging_gross_weight: Optional[Decimal] = None
    packaging_net_weight: Optional[Decimal] = None

    # v0.21.0: 원본 요청서 수정 알림 플래그
    source_request_modified: bool = Field(default=False, description="원본 요청서 수정됨")

    # 조인된 정보
    product_part: Optional[PartInfo] = None  # deprecated - 호환성용 (첫번째 제품)
    customer: Optional[CustomerInfo] = None
    items: Optional[List[WorkOrderItemResponse]] = None

    # v0.19.0: 다중 제품
    products: Optional[List[WorkOrderProductResponse]] = None

    # v0.22.0: 생산요청서 첨부파일 (참조)
    source_request_attachments: Optional[List[Any]] = Field(default=None, description="원본 생산요청서 첨부파일")
    source_request_number: Optional[str] = Field(default=None, description="원본 생산요청서 번호")

    class Config:
        from_attributes = True


class WorkOrderListResponse(BaseModel):
    """작업지시서 목록 응답 스키마 (간략) (v0.19.0 다중 제품 지원)"""
    id: int
    wo_number: str
    product_part_id: Optional[int] = None  # deprecated - 호환성용
    parent_wo_id: Optional[int] = None  # v0.31.0: 상위 WO
    target_part_id: Optional[int] = None  # v0.31.0: 목적 부품
    customer_id: Optional[int] = None
    order_quantity: Optional[Decimal] = None  # deprecated - 호환성용
    completed_quantity: Optional[Decimal] = None  # deprecated - 호환성용
    status: WorkOrderStatus
    priority: int
    shipping_scheduled_date: Optional[date] = None
    created_at: datetime

    # v0.21.0: 원본 요청서 수정 알림 플래그
    source_request_modified: bool = Field(default=False, description="원본 요청서 수정됨")

    # 조인된 정보
    product_part: Optional[PartInfo] = None  # deprecated - 호환성용 (첫번째 제품)
    customer: Optional[CustomerInfo] = None
    item_count: Optional[int] = None  # 항목 수
    product_count: Optional[int] = None  # v0.19.0: 제품 수

    # v0.19.0: 다중 제품 (목록에서는 간략 정보)
    products: Optional[List[WorkOrderProductResponse]] = None

    class Config:
        from_attributes = True


class WorkOrderPaginatedResponse(BaseModel):
    """작업지시서 목록 페이지네이션 응답"""
    items: List[WorkOrderListResponse] = Field(description="작업지시서 목록")
    total: int = Field(description="총 개수")
    skip: int = Field(description="건너뛴 개수")
    limit: int = Field(description="조회 개수")
    has_more: bool = Field(description="추가 데이터 존재 여부")


# ==================== BOM 전개 미리보기 스키마 ====================

class BOMPreviewItem(BaseModel):
    """BOM 전개 미리보기 항목"""
    part_id: int
    part_number: str
    part_number_display: Optional[str] = None
    part_name: str
    bom_id: Optional[int] = None
    bom_level: int
    unit_quantity: Decimal  # BOM 상 단위 수량
    total_quantity: Decimal  # 지시수량 * 단위수량
    current_stock: Optional[Decimal] = None  # 현재고
    stock_status: Optional[str] = None  # 재고 상태 (SUFFICIENT/INSUFFICIENT)


class BOMPreviewResponse(BaseModel):
    """BOM 전개 미리보기 응답"""
    product_part_id: int
    product_part_name: str
    order_quantity: Decimal
    items: List[BOMPreviewItem]
    has_insufficient_stock: bool = False  # 재고 부족 항목 존재 여부


# ==================== 생산 완료 스키마 ====================

class ProductionCompleteRequest(BaseModel):
    """생산 완료 요청 스키마"""
    completed_quantity: Decimal = Field(..., ge=0, description="완료 수량")
    defective_quantity: Decimal = Field(default=Decimal(0), ge=0, description="불량 수량")
    remarks: Optional[str] = Field(None, description="비고")


# ==================== 상태 변경 스키마 ====================

class StatusChangeRequest(BaseModel):
    """상태 변경 공통 요청 스키마"""
    remarks: Optional[str] = Field(None, description="비고")
