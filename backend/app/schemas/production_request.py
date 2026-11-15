"""
생산 요청서 스키마
API 요청/응답 데이터 검증 및 직렬화를 담당합니다.

v0.20.0: 생산 요청서 기능 추가
v0.22.0: 다중 제품 지원
"""

from typing import Optional, List, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, model_validator


# ==================== 첨부파일 스키마 (v0.22.0) ====================

class AttachmentFile(BaseModel):
    """첨부파일 정보"""
    filename: str = Field(..., description="파일명")
    filepath: str = Field(..., description="저장 경로")
    mimetype: str = Field(..., description="MIME 타입")
    size: Optional[int] = Field(None, description="파일 크기 (bytes)")


class PackingBox(BaseModel):
    """출고 packing list 박스 라인 (v0.77.0)"""
    box_type: Optional[str] = Field(None, description="박스 종류/식별 (예: Carton A)")
    quantity: Optional[int] = Field(1, ge=0, description="동일 박스 개수")
    gross_weight: Optional[Decimal] = Field(None, description="총중량 kg (박스당)")
    net_weight: Optional[Decimal] = Field(None, description="순중량 kg (박스당)")
    length: Optional[Decimal] = Field(None, description="길이 cm")
    width: Optional[Decimal] = Field(None, description="너비 cm")
    height: Optional[Decimal] = Field(None, description="높이 cm")
    remarks: Optional[str] = Field(None, description="내용물/비고")


class BoxPlanLine(BaseModel):
    """박스 분할계획 — 박스 내 품목 라인 (v0.90.0)"""
    pr_item_id: Optional[int] = Field(None, description="생산요청 품목 ID (외주/커스텀은 null 가능)")
    product_code: Optional[str] = Field(None, description="표시용 품번(스냅샷)")
    quantity: Decimal = Field(..., ge=0, description="이 박스에 담을 수량")


class BoxPlanBox(BaseModel):
    """박스 분할계획 — 박스 1개 (v0.90.0)"""
    box_no: int = Field(..., ge=1, description="박스 번호(1부터)")
    items: List[BoxPlanLine] = Field(default_factory=list, description="박스 내 품목/수량")
    remarks: Optional[str] = Field(None, description="비고(포장 지시 등)")
    # 발행 추적(잔여박스) — 박스별 CI 발행 시 기록. 저장 시 라운드트립으로 보존
    ci_document_id: Optional[int] = Field(None, description="이 박스로 발행된 CI 문서 ID")
    ci_number: Optional[str] = Field(None, description="이 박스로 발행된 CI 번호")


class BoxPlanUpdate(BaseModel):
    """박스 분할계획 저장 — 영업이 작성(자동생성 후 수기조정)"""
    box_plan: Optional[List[BoxPlanBox]] = Field(None, description="박스 분할계획(없으면 계획 해제)")


class ProductionRequestShip(BaseModel):
    """생산 출고 처리 요청 — packing list와 함께 SHIPPED로 전환"""
    packing_list: Optional[List[PackingBox]] = Field(None, description="박스별 포장 명세")


class ProductionRequestStatus(str, Enum):
    """생산 요청서 상태"""
    REQUESTED = "REQUESTED"      # 요청됨 (영업팀 등록)
    HOLD = "HOLD"                # 보류
    REJECTED = "REJECTED"        # 반려됨
    APPROVED = "APPROVED"        # 승인됨 (= 생산부 확인)
    IN_PROGRESS = "IN_PROGRESS"  # 생산 진행중
    COMPLETED = "COMPLETED"      # 생산 완료
    SHIPPED = "SHIPPED"          # 출고 완료
    DELIVERED = "DELIVERED"      # 발송 완료
    CANCELLED = "CANCELLED"      # 취소됨


# ==================== 제품 항목 스키마 (v0.22.0) ====================

class ProductionRequestItemBase(BaseModel):
    """생산 요청서 제품 항목 기본 스키마.

    product_part_id(BOM 부품) 또는 custom_product_name(외주/직접입력) 중 하나는 필수.
    """
    product_part_id: Optional[int] = Field(None, description="제품 부품 ID (없으면 커스텀/외주 항목)")
    custom_product_code: Optional[str] = Field(None, max_length=100, description="커스텀 품번 (BOM 미등록·외주)")
    custom_product_name: Optional[str] = Field(None, max_length=200, description="커스텀 품명 (BOM 미등록·외주)")
    requested_quantity: Decimal = Field(..., gt=0, description="요청 수량")
    uom: Optional[str] = Field(None, description="단위 (예: EA/SET/M)")
    line_remarks: Optional[str] = Field(None, description="항목 비고")
    customer_requirements: Optional[str] = Field(None, description="고객 요구사항")
    sort_order: int = Field(default=0, description="정렬순서")

    @model_validator(mode='after')
    def validate_product_ref(self):
        """BOM 부품 id 또는 커스텀 품번/품명 중 하나는 있어야 함."""
        if not self.product_part_id and not (self.custom_product_code or self.custom_product_name):
            raise ValueError("제품 부품(BOM) 또는 커스텀 품번/품명 중 하나는 필수입니다.")
        return self


class ProductionRequestItemCreate(ProductionRequestItemBase):
    """생산 요청서 제품 항목 생성 스키마"""
    pass


class ProductionRequestItemUpdate(ProductionRequestItemBase):
    """생산 요청서 제품 항목 수정 스키마.

    id가 있으면 기존 항목 in-place 수정(PI 링크 보존), 없으면 신규 추가.
    """
    id: Optional[int] = Field(None, description="기존 항목 id (없으면 신규 추가)")


class ProductionRequestItemResponse(BaseModel):
    """생산 요청서 제품 항목 응답 스키마"""
    id: int
    production_request_id: int
    product_part_id: Optional[int] = None  # 커스텀/외주 항목이면 None
    custom_product_code: Optional[str] = None
    custom_product_name: Optional[str] = None
    requested_quantity: Decimal
    ci_quantity: Optional[Decimal] = 0
    uom: Optional[str] = None
    line_remarks: Optional[str] = None
    customer_requirements: Optional[str] = None
    work_order_id: Optional[int] = None
    sort_order: int
    attachment_files: Optional[List[dict]] = None  # 품목별 도면/첨부

    # 조인된 정보
    product_part: Optional["PartSimple"] = None

    class Config:
        from_attributes = True


# ==================== 요청서 기본 스키마 ====================

class ProductionRequestBase(BaseModel):
    """생산 요청서 기본 스키마 (v0.22.0 다중 제품 지원)"""
    customer_id: Optional[int] = Field(None, description="고객사 ID")
    customer_order_no: Optional[str] = Field(None, max_length=50, description="고객 주문번호")

    # [DEPRECATED] 단일 제품 필드 - 호환성을 위해 유지
    product_part_id: Optional[int] = Field(None, description="제품 부품 ID (단일 제품, deprecated)")
    requested_quantity: Optional[Decimal] = Field(None, gt=0, description="요청 수량 (단일 제품, deprecated)")

    due_date: Optional[date] = Field(None, description="희망 납기일")
    priority: int = Field(0, ge=0, le=2, description="우선순위 (0:보통, 1:높음, 2:긴급)")
    pi_number: Optional[str] = Field(None, max_length=50, description="PI 번호 (Proforma Invoice)")
    payment_status: Optional[str] = Field(None, description="입금현황 (UNPAID/PARTIAL/PAID)")
    country: Optional[str] = Field(None, max_length=100, description="국가")
    production_period: Optional[str] = Field(None, max_length=50, description="생산기간")
    shipping_mark: Optional[str] = Field(None, description="SHIPPING MARK")
    consignee: Optional[str] = Field(None, description="CONSIGNEE")
    destination: Optional[str] = Field(None, max_length=200, description="DESTINATION (도착지)")
    prepared_by_name: Optional[str] = Field(None, max_length=100, description="작성자명")
    remarks: Optional[str] = Field(None, description="비고")


class ProductionRequestCreate(ProductionRequestBase):
    """생산 요청서 생성 스키마 (v0.22.0 다중 제품 지원)"""
    requested_by: Optional[int] = Field(None, description="요청자 ID")

    # v0.22.0: 다중 제품 목록
    items: Optional[List[ProductionRequestItemCreate]] = Field(default=[], description="제품 목록 (다중 제품)")

    @model_validator(mode='after')
    def validate_items(self):
        """items 또는 product_part_id 중 하나는 필수"""
        if not self.items and not self.product_part_id:
            raise ValueError("items 또는 product_part_id 중 하나는 필수입니다.")
        # 단일 제품 필드가 있으면 items로 변환
        if self.product_part_id and self.requested_quantity and not self.items:
            self.items = [ProductionRequestItemCreate(
                product_part_id=self.product_part_id,
                requested_quantity=self.requested_quantity,
                sort_order=0
            )]
        return self


class ProductionRequestUpdate(BaseModel):
    """생산 요청서 수정 스키마 (v0.22.0 다중 제품 지원)"""
    customer_id: Optional[int] = None
    customer_order_no: Optional[str] = None

    # [DEPRECATED] 단일 제품 필드
    product_part_id: Optional[int] = None
    requested_quantity: Optional[Decimal] = None

    due_date: Optional[date] = None
    priority: Optional[int] = None
    pi_number: Optional[str] = None
    payment_status: Optional[str] = None
    country: Optional[str] = None
    production_period: Optional[str] = None
    shipping_mark: Optional[str] = None
    consignee: Optional[str] = None
    destination: Optional[str] = None
    prepared_by_name: Optional[str] = None
    remarks: Optional[str] = None

    # 진행 체크박스
    insert_shipped: Optional[bool] = None
    production_shipped: Optional[bool] = None
    needs_review: Optional[bool] = None

    # v0.22.0: 다중 제품 수정 (id 있으면 in-place 수정 → PI 링크/고객요구사항 보존)
    items: Optional[List[ProductionRequestItemUpdate]] = None

    # v0.22.0: 첨부파일
    attachment_files: Optional[List[AttachmentFile]] = None


class ProductionRequestFlagsUpdate(BaseModel):
    """진행 체크박스 토글 — status 워크플로우와 무관하게 모든 상태에서 허용"""
    insert_shipped: Optional[bool] = None
    production_shipped: Optional[bool] = None
    needs_review: Optional[bool] = None
    review_note: Optional[str] = None  # 검토 필요 사유(생산팀→영업 확인요청)
    # v0.84.0 출고일 명시 수정 — 값이 오면 해당 완료시각을 이 날짜로 설정(실수 재기록 방지용).
    insert_shipped_at: Optional[date] = None
    production_shipped_at: Optional[date] = None
    # v0.84.0 인서트 해당없음(N/A) — 인서트 공정 없는 건
    insert_not_applicable: Optional[bool] = None


class ProductionRequestApprove(BaseModel):
    """생산 요청서 승인 스키마"""
    approved_by: Optional[int] = Field(None, description="승인자 ID")
    remarks: Optional[str] = Field(None, description="승인 비고")


class ProductionRequestReject(BaseModel):
    """생산 요청서 반려 스키마"""
    rejection_reason: str = Field(..., min_length=1, description="반려 사유")


class ProductionRequestHold(BaseModel):
    """생산 요청서 보류 스키마"""
    remarks: Optional[str] = Field(None, description="보류 사유")


# ==================== 응답 스키마 ====================

class PartSimple(BaseModel):
    """부품 간단 정보"""
    id: int
    part_number: Optional[str] = None
    part_number_display: Optional[str] = None
    part_name: Optional[str] = None
    part_name_en: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerSimple(BaseModel):
    """고객사 간단 정보"""
    id: int
    partner_name: Optional[str] = None
    partner_code: Optional[str] = None

    class Config:
        from_attributes = True


class WorkOrderSimple(BaseModel):
    """작업지시서 간단 정보"""
    id: int
    wo_number: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ProductionRequestItemResponse에서 PartSimple 참조 업데이트
ProductionRequestItemResponse.model_rebuild()


class ProductionRequestResponse(BaseModel):
    """생산 요청서 응답 스키마 (v0.22.0 다중 제품 지원)"""
    id: int
    request_number: str
    customer_id: Optional[int] = None
    customer_order_no: Optional[str] = None

    # [DEPRECATED] 단일 제품 필드 - 호환성용 (첫번째 제품)
    product_part_id: Optional[int] = None
    requested_quantity: Optional[Decimal] = None

    due_date: Optional[date] = None
    status: str
    is_draft: bool = False
    priority: int
    pi_number: Optional[str] = None
    payment_status: Optional[str] = None
    country: Optional[str] = None
    production_period: Optional[str] = None
    shipping_mark: Optional[str] = None
    consignee: Optional[str] = None
    destination: Optional[str] = None
    prepared_by_name: Optional[str] = None
    remarks: Optional[str] = None

    # 진행 체크박스
    insert_shipped: bool = False
    insert_not_applicable: bool = False
    production_shipped: bool = False
    needs_review: bool = False
    insert_shipped_at: Optional[datetime] = None
    production_shipped_at: Optional[datetime] = None
    review_note: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    packing_list: Optional[List[PackingBox]] = None
    box_plan: Optional[List[BoxPlanBox]] = None

    requested_by: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 관계 데이터
    customer: Optional[CustomerSimple] = None
    product_part: Optional[PartSimple] = None  # deprecated - 첫번째 제품
    work_orders: Optional[List[WorkOrderSimple]] = None

    # v0.22.0: 다중 제품
    items: Optional[List[ProductionRequestItemResponse]] = None
    item_count: Optional[int] = None

    # v0.22.0: 첨부파일
    attachment_files: Optional[List[AttachmentFile]] = None

    # v0.69.0: 생산 시작 단계 자료
    manager_memo: Optional[str] = None
    process_checks: Optional[List[dict]] = None

    class Config:
        from_attributes = True


class ProductionNotesUpdate(BaseModel):
    """생산 시작 단계 자료 저장 — 총괄자 메모 / 공정 확인표.

    상태 워크플로우와 독립적으로 IN_PROGRESS 등에서도 저장 가능(update 가드 우회).
    """
    manager_memo: Optional[str] = None
    process_checks: Optional[List[dict]] = None


class ProductionRequestListItem(BaseModel):
    """생산 요청서 목록 아이템 (v0.22.0 다중 제품 지원)"""
    id: int
    request_number: str
    customer_id: Optional[int] = None

    # [DEPRECATED] 단일 제품 필드 - 호환성용 (첫번째 제품)
    product_part_id: Optional[int] = None
    requested_quantity: Optional[Decimal] = None

    due_date: Optional[date] = None
    status: str
    is_draft: bool = False
    priority: int
    pi_number: Optional[str] = None
    payment_status: Optional[str] = None
    prepared_by_name: Optional[str] = None  # 영업 담당자 (작성자명)
    requested_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # 진행 체크박스
    insert_shipped: bool = False
    insert_not_applicable: bool = False
    production_shipped: bool = False
    needs_review: bool = False
    insert_shipped_at: Optional[datetime] = None
    production_shipped_at: Optional[datetime] = None
    review_note: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    packing_list: Optional[List[PackingBox]] = None
    # v0.90.0 분할선적 박스계획 존재 여부(배지용) — 전체 계획은 상세 조회에서
    has_box_plan: bool = False

    customer: Optional[CustomerSimple] = None
    product_part: Optional[PartSimple] = None  # deprecated - 첫번째 제품
    work_order_count: int = 0

    # v0.22.0: 다중 제품 지원
    item_count: int = 0
    items: Optional[List[ProductionRequestItemResponse]] = None

    # v0.74.0: 첨부(도면/사진) — 영업 현황에서 사진 확인용
    attachment_files: Optional[List[AttachmentFile]] = None

    class Config:
        from_attributes = True


class ProductionRequestPaginatedResponse(BaseModel):
    """생산 요청서 페이지네이션 응답"""
    items: List[ProductionRequestListItem]
    total: int
    skip: int
    limit: int
    has_more: bool
