"""
영업 문서 Pydantic 스키마
Quotation / PI / CI API 요청/응답
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class DocumentType(str, Enum):
    QUOTATION = "QUOTATION"
    PI = "PI"
    CI = "CI"
    INVOICE = "INVOICE"  # PI와 동일 양식, 제목만 'INVOICE' (PI에서 전환 발행)


class DocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


# ==================== 품목 스키마 ====================

class SalesDocumentItemCreate(BaseModel):
    """품목 생성.

    *_text 필드는 TBD 등 비숫자 표시 오버라이드용. 값이 들어 있으면 PDF/엑셀이
    숫자 대신 그 문자열을 표시하고 합계에서 제외된다. 숫자 필드는 계산 호환을
    위해 0을 저장한다.
    """
    line_no: int = Field(..., ge=1, description="라인 번호")
    product_code: str = Field(..., max_length=100, description="오더코드")
    description: Optional[str] = Field(None, description="제품 설명")
    quantity: Decimal = Field(..., ge=0, description="수량 (TBD면 0)")
    quantity_text: Optional[str] = Field(None, max_length=40, description="수량 표시 오버라이드 (예: 'TBD')")
    uom: str = Field("pc", max_length=10, description="단위")
    unit_price: Decimal = Field(..., ge=0, description="단가 (TBD면 0)")
    unit_price_text: Optional[str] = Field(None, max_length=40, description="단가 표시 오버라이드 (예: 'TBD')")
    amount: Decimal = Field(..., ge=0, description="금액 (TBD면 0)")
    amount_text: Optional[str] = Field(None, max_length=40, description="금액 표시 오버라이드 (예: 'TBD')")
    currency: str = Field("USD", max_length=10, description="통화")
    line_remarks: Optional[str] = Field(None, description="항목 비고")


class SalesDocumentItemResponse(BaseModel):
    """품목 응답"""
    id: int
    document_id: int
    line_no: int
    product_code: str
    description: Optional[str] = None
    quantity: Decimal
    quantity_text: Optional[str] = None
    uom: str
    unit_price: Decimal
    unit_price_text: Optional[str] = None
    amount: Decimal
    amount_text: Optional[str] = None
    currency: str
    line_remarks: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 고객사 간략 정보 ====================

class CustomerBrief(BaseModel):
    """고객사 간략 정보 (문서 목록용)"""
    id: int
    partner_code: str
    partner_name: str
    partner_name_en: Optional[str] = None
    short_code: Optional[str] = None
    country_code: Optional[str] = None  # ISO 3166-1 (KR / US / CN ...) — PDF 언어 필터링용
    country_name: Optional[str] = None
    trade_type: Optional[str] = None  # DOMESTIC / EXPORT

    model_config = ConfigDict(from_attributes=True)


# ==================== 문서 스키마 ====================

class SalesDocumentCreate(BaseModel):
    """문서 생성"""
    document_type: DocumentType = Field(..., description="문서 유형")
    document_date: date = Field(..., description="문서 날짜")
    customer_id: int = Field(..., description="고객사 ID")
    customer_contact_id: Optional[int] = Field(None, description="고객사 담당자 ID(미지정 시 기본 담당자)")

    # 이전 문서 참조 (Q→PI→CI)
    source_document_id: Optional[int] = Field(None, description="원본 문서 ID")

    # 작성자
    prepared_by: Optional[str] = Field(None, max_length=100)
    prepared_email: Optional[str] = Field(None, max_length=200)

    # 고객 PO
    customer_po_number: Optional[str] = Field(None, max_length=100)
    customer_po_date: Optional[date] = None
    po_attachment_files: Optional[List[dict]] = Field(None, description="PO 첨부파일 목록")
    shipping_invoice_files: Optional[List[dict]] = Field(None, description="운송장 첨부파일 목록 (CI)")

    # 영업활동 연결 (v0.31.0)
    sales_activity_id: Optional[int] = Field(None, description="연결된 영업활동 ID")

    # Terms
    payment_terms: Optional[str] = Field(None, max_length=500)
    delivery_terms: Optional[str] = Field(None, max_length=200)
    incoterms: Optional[str] = Field(None, max_length=10, description="인코텀즈(EXW/FCA/CPT/CIP/CFR/CIF/DAP/DDP)")
    freight_per_box: Optional[Decimal] = Field(None, ge=0, description="박스당 운임(분할선적)")
    show_customer_tax_id: Optional[bool] = Field(None, description="거래처 VAT/TAX ID(사업자등록번호) 문서 표기")
    show_statement_of_origin: Optional[bool] = Field(None, description="CI 원산지 신고문(Statement of Origin) 표기")
    hs_code: Optional[str] = Field(None, max_length=100)
    country_of_origin: str = Field("Republic of Korea", max_length=100)
    valid_until: Optional[str] = Field(None, max_length=200)

    # Bank
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_address: Optional[str] = Field(None, max_length=500)
    swift_code: Optional[str] = Field(None, max_length=20)
    account_name: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=50)

    # Ship To (수령자)
    ship_to_address_id: Optional[int] = Field(None, description="선택된 거래처 배송지 ID(있으면 이 값 우선)")
    ship_to_name: Optional[str] = Field(None, max_length=200)
    ship_to_address: Optional[str] = None
    ship_to_contact: Optional[str] = Field(None, max_length=200)
    ship_to_phone: Optional[str] = Field(None, max_length=50)
    ship_to_email: Optional[str] = Field(None, max_length=200)

    # CI 전용
    ship_from: Optional[str] = Field(None, max_length=200)
    destination: Optional[str] = Field(None, max_length=200)
    transportation: Optional[str] = Field(None, max_length=100)
    shipment_date: Optional[date] = None

    # CI Package
    packaging_boxes: Optional[int] = None
    packaging_dimensions: Optional[str] = Field(None, max_length=100)
    packaging_gross_weight: Optional[Decimal] = None
    packaging_net_weight: Optional[Decimal] = None
    packing_list: Optional[List[dict]] = None  # 박스별 packing list (생산 승계)

    # 통화
    currency: str = Field("USD", max_length=10)

    # v0.71.0 할인/배송비 (NULL=미적용, 값 있으면 총액 반영)
    discount_amount: Optional[Decimal] = Field(None, ge=0, description="할인 금액 (총액에서 차감)")
    discount_reason: Optional[str] = Field(None, max_length=300, description="할인 사유 (견적서 기록용)")
    shipping_fee: Optional[Decimal] = Field(None, ge=0, description="배송비 (총액에 가산)")

    # MOQ 견적 여부
    is_moq: bool = Field(False, description="MOQ 가격표 견적 여부")
    is_quote_only: bool = Field(False, description="견적 대용 PI(매출/미수 집계 제외)")

    # 비고
    remarks: Optional[str] = None

    # 품목
    items: List[SalesDocumentItemCreate] = Field(default_factory=list, description="품목 목록")


class SalesDocumentUpdate(BaseModel):
    """문서 수정"""
    document_date: Optional[date] = None
    customer_contact_id: Optional[int] = Field(None, description="고객사 담당자 ID")
    prepared_by: Optional[str] = Field(None, max_length=100)
    prepared_email: Optional[str] = Field(None, max_length=200)
    customer_po_number: Optional[str] = Field(None, max_length=100)
    customer_po_date: Optional[date] = None
    po_attachment_files: Optional[List[dict]] = None
    shipping_invoice_files: Optional[List[dict]] = None
    payment_terms: Optional[str] = Field(None, max_length=500)
    delivery_terms: Optional[str] = Field(None, max_length=200)
    incoterms: Optional[str] = Field(None, max_length=10, description="인코텀즈(EXW/FCA/CPT/CIP/CFR/CIF/DAP/DDP)")
    freight_per_box: Optional[Decimal] = Field(None, ge=0, description="박스당 운임(분할선적)")
    show_customer_tax_id: Optional[bool] = Field(None, description="거래처 VAT/TAX ID(사업자등록번호) 문서 표기")
    show_statement_of_origin: Optional[bool] = Field(None, description="CI 원산지 신고문(Statement of Origin) 표기")
    hs_code: Optional[str] = Field(None, max_length=100)
    country_of_origin: Optional[str] = Field(None, max_length=100)
    valid_until: Optional[str] = Field(None, max_length=200)
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_address: Optional[str] = Field(None, max_length=500)
    swift_code: Optional[str] = Field(None, max_length=20)
    account_name: Optional[str] = Field(None, max_length=200)
    account_number: Optional[str] = Field(None, max_length=50)
    ship_to_address_id: Optional[int] = None
    ship_to_name: Optional[str] = Field(None, max_length=200)
    ship_to_address: Optional[str] = None
    ship_to_contact: Optional[str] = Field(None, max_length=200)
    ship_to_phone: Optional[str] = Field(None, max_length=50)
    ship_to_email: Optional[str] = Field(None, max_length=200)
    ship_from: Optional[str] = Field(None, max_length=200)
    destination: Optional[str] = Field(None, max_length=200)
    transportation: Optional[str] = Field(None, max_length=100)
    shipment_date: Optional[date] = None
    packaging_boxes: Optional[int] = None
    packaging_dimensions: Optional[str] = Field(None, max_length=100)
    packaging_gross_weight: Optional[Decimal] = None
    packaging_net_weight: Optional[Decimal] = None
    packing_list: Optional[List[dict]] = None  # 박스별 packing list (생산 승계)
    currency: Optional[str] = Field(None, max_length=10)
    discount_amount: Optional[Decimal] = Field(None, ge=0, description="할인 금액 (총액에서 차감, null=미적용)")
    discount_reason: Optional[str] = Field(None, max_length=300, description="할인 사유 (견적서 기록용)")
    shipping_fee: Optional[Decimal] = Field(None, ge=0, description="배송비 (총액에 가산, null=미적용)")
    is_moq: Optional[bool] = None
    is_quote_only: Optional[bool] = None
    remarks: Optional[str] = None

    # v0.24.0 Phase 3: 수금
    payment_status: Optional[str] = Field(None, description="입금 상태 (UNPAID/PARTIAL/PAID)")
    payment_condition: Optional[str] = Field(None, max_length=200, description="결제 조건 상세")
    paid_amount: Optional[Decimal] = Field(None, ge=0, description="입금 확인 금액")
    paid_date: Optional[date] = Field(None, description="입금 확인일")
    payment_remarks: Optional[str] = Field(None, description="입금 메모")
    management_no: Optional[str] = Field(None, max_length=20, description="관리번호")

    # 품목 전체 교체
    items: Optional[List[SalesDocumentItemCreate]] = None


class SalesDocumentResponse(BaseModel):
    """문서 응답"""
    id: int
    document_type: str
    document_number: str
    document_date: date
    source_document_id: Optional[int] = None
    sales_activity_id: Optional[int] = None
    customer_id: int
    customer_contact_id: Optional[int] = None
    prepared_by: Optional[str] = None
    prepared_email: Optional[str] = None
    customer_po_number: Optional[str] = None
    customer_po_date: Optional[date] = None
    po_attachment_files: Optional[List[dict]] = None
    shipping_invoice_files: Optional[List[dict]] = None
    sales_activity_id: Optional[int] = None
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    incoterms: Optional[str] = None
    freight_per_box: Optional[Decimal] = None
    show_customer_tax_id: Optional[bool] = None
    show_statement_of_origin: Optional[bool] = None
    hs_code: Optional[str] = None
    country_of_origin: Optional[str] = None
    valid_until: Optional[str] = None
    bank_name: Optional[str] = None
    bank_address: Optional[str] = None
    swift_code: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    ship_to_address_id: Optional[int] = None
    ship_to_name: Optional[str] = None
    ship_to_address: Optional[str] = None
    ship_to_contact: Optional[str] = None
    ship_to_phone: Optional[str] = None
    ship_to_email: Optional[str] = None
    ship_from: Optional[str] = None
    destination: Optional[str] = None
    transportation: Optional[str] = None
    shipment_date: Optional[date] = None
    packaging_boxes: Optional[int] = None
    packaging_dimensions: Optional[str] = None
    packaging_gross_weight: Optional[Decimal] = None
    packaging_net_weight: Optional[Decimal] = None
    packing_list: Optional[List[dict]] = None  # 박스별 packing list (생산 승계)
    total_amount: Decimal
    currency: str
    discount_amount: Optional[Decimal] = None
    discount_reason: Optional[str] = None
    shipping_fee: Optional[Decimal] = None
    is_moq: bool = False
    is_quote_only: bool = False
    status: str
    payment_status: Optional[str] = None
    payment_condition: Optional[str] = None
    paid_amount: Optional[Decimal] = None
    paid_date: Optional[date] = None
    payment_remarks: Optional[str] = None
    management_no: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # 조인 정보
    customer: Optional[CustomerBrief] = None
    source_document: Optional["SalesDocumentBrief"] = None
    items: List[SalesDocumentItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SalesDocumentBrief(BaseModel):
    """문서 간략 정보 (참조용)"""
    id: int
    document_type: str
    document_number: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class SalesDocumentListItem(BaseModel):
    """문서 목록 아이템"""
    id: int
    document_type: str
    document_number: str
    document_date: date
    customer_id: int
    total_amount: Decimal
    currency: str
    status: str
    customer_po_number: Optional[str] = None
    source_document_id: Optional[int] = None
    sales_activity_id: Optional[int] = None
    payment_status: Optional[str] = None
    paid_amount: Optional[Decimal] = None
    shipment_date: Optional[date] = None
    is_moq: bool = False
    is_quote_only: bool = False
    version: int = 1
    is_latest: bool = True
    management_no: Optional[str] = None
    created_at: datetime

    customer: Optional[CustomerBrief] = None

    # v0.31.0: 대표 제품 표시 (목록에서 한눈에 식별)
    representative_product: Optional[str] = None  # 첫 품목의 product_code
    item_count: Optional[int] = None  # 총 품목 수

    # PI 생산 진행 집계 (집계 A: 병목 기준) — {pr_total, stage, counts{prod,ship,deliv}} 또는 None
    production_progress: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class SalesDocumentListResponse(BaseModel):
    """문서 목록 페이지네이션 응답"""
    items: List[SalesDocumentListItem]
    total: int
    skip: int
    limit: int


class PaymentUpdateRequest(BaseModel):
    """입금 상태 변경 요청"""
    payment_status: str = Field(..., description="입금 상태 (UNPAID/PARTIAL/PAID)")
    paid_amount: Optional[Decimal] = Field(None, ge=0, description="입금 확인 금액")
    paid_date: Optional[date] = Field(None, description="입금 확인일")
    payment_remarks: Optional[str] = Field(None, description="입금 메모")


class PoNumberUpdateRequest(BaseModel):
    """고객 PO 번호 정정 요청.

    고객사가 잘못 준 PO 번호를 바로잡는 용도. 이미 발행된 문서도 새 버전을
    만들지 않고 제자리에서 고친다(문서번호·상태·금액 불변).
    """
    customer_po_number: Optional[str] = Field(None, max_length=100, description="고객 PO 번호(빈값=지움)")
    customer_po_date: Optional[date] = Field(None, description="고객 PO 날짜")
    cascade: bool = Field(True, description="같은 PO 를 승계한 후속 문서(CI 등)도 함께 정정")


class PoNumberUpdateResponse(BaseModel):
    """PO 번호 정정 결과"""
    document: SalesDocumentResponse
    updated_count: int = Field(..., description="정정된 문서 수(버전·후속 문서 포함)")


class CollectionSummary(BaseModel):
    """수금 현황 요약"""
    total_documents: int = 0
    total_amount: Decimal = Decimal("0")
    paid_amount: Decimal = Decimal("0")
    unpaid_amount: Decimal = Decimal("0")
    unpaid_count: int = 0
    partial_count: int = 0
    paid_count: int = 0


class ConvertToNextRequest(BaseModel):
    """Q→PI 또는 PI→CI 전환 요청"""
    customer_po_number: Optional[str] = Field(None, description="고객 PO 번호 (PI 전환 시)")
    customer_po_date: Optional[date] = Field(None, description="고객 PO 날짜")
    po_attachment_files: Optional[List[dict]] = Field(None, description="PO 첨부파일 목록")
    is_quote_only: bool = Field(False, description="견적 대용 PI로 전환(매출/미수 집계 제외, PI 전환 시만 적용)")
    document_date: Optional[date] = Field(None, description="생성 문서 날짜(미지정 시 오늘). CI는 이 날짜를 출고/매출 인식일로 사용")
    target_type: Optional[str] = Field(None, description="전환 대상 문서 유형(미지정 시 기본 체인). PI→CI 또는 PI→INVOICE")


class ConvertMultipleRequest(BaseModel):
    """다중 문서 전환 요청 (N:M, v0.32.0)"""
    source_ids: List[int] = Field(..., min_length=1, description="소스 문서 ID 목록")
    customer_po_number: Optional[str] = Field(None, description="고객 PO 번호")
    customer_po_date: Optional[date] = Field(None, description="고객 PO 날짜")
    po_attachment_files: Optional[List[dict]] = Field(None, description="PO 첨부파일 목록")
    document_date: Optional[date] = Field(None, description="생성 문서 날짜(미지정 시 오늘)")
    target_type: Optional[str] = Field(None, description="전환 대상 문서 유형(PI→CI 또는 PI→INVOICE)")
