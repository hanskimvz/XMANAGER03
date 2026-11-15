"""견적서 PDF 렌더용 데이터 모델 (Phase 1)

기존 SalesDocument(DB)와 별도 PDF 전용 표현체.
SalesDocument → QuotationPdfData 매핑은 services/pdf/mapper.py 참조.

product_code / description 필드는 강조 마크업 입력 허용:
  [[텍스트]]   핵심 강조 (빨간 굵게)
  {{텍스트}}   보조 강조 (노란 하이라이트)
  __텍스트__   사양 강조 (빨간 밑줄)
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Currency(str, Enum):
    KRW = "KRW"
    USD = "USD"
    EUR = "EUR"
    CNY = "CNY"  # 중국 위안
    JPY = "JPY"  # 일본 엔
    GBP = "GBP"  # 영국 파운드


class Language(str, Enum):
    KO = "ko"
    EN = "en"


class Incoterms(str, Enum):
    EXW = "EXW"
    FCA = "FCA"
    CPT = "CPT"
    CIP = "CIP"
    DAP = "DAP"
    DPU = "DPU"
    DDP = "DDP"
    FAS = "FAS"
    FOB = "FOB"
    CFR = "CFR"
    CIF = "CIF"


class CompanyInfo(BaseModel):
    """발행사(엑스빔테크) 정보 — 한·영 양면 표기

    국내 양식의 회사 박스(상호·대표이사·업종·업태·전화·팩스)와
    영문 양식의 헤더(회사명·주소·전화·팩스·이메일) 양쪽을 커버.
    """
    name_ko: str
    name_en: str
    representative_ko: Optional[str] = None
    representative_en: Optional[str] = None
    address_ko: Optional[str] = None
    address_en: Optional[str] = None
    business_type_ko: Optional[str] = None  # 업종 (예: 제조업 외)
    business_item_ko: Optional[str] = None  # 업태 (예: 연구개발 외)
    business_number: Optional[str] = None
    tel: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class CustomerInfo(BaseModel):
    """수신처 (BUYER) 정보"""
    name: str
    name_en: Optional[str] = None
    contact_person: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    tax_id: Optional[str] = None  # 거래처 VAT/TAX ID(사업자등록번호) — show_customer_tax_id 시에만 채움


class ShipToInfo(BaseModel):
    """선적지(SHIP TO) 정보 — 영문 양식 전용"""
    same_as_buyer: bool = True
    name: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class BankInfo(BaseModel):
    """송금 계좌 정보"""
    bank_name: Optional[str] = None
    bank_address: Optional[str] = None
    swift_code: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None


class PriceTier(BaseModel):
    """MOQ 견적의 수량 구간별 단가 (1행 1품목 내부에 다단 스택 렌더링).

    *_text 필드가 채워지면 PDF는 숫자 대신 그 문자열을 표시 (예: 'TBD')하고
    합계에서 해당 행/구간을 제외한다.
    """
    quantity: Decimal = Field(..., ge=0)
    quantity_text: Optional[str] = None
    uom: str = "EA"
    unit_price: Decimal = Field(..., ge=0)
    unit_price_text: Optional[str] = None
    amount: Decimal = Field(..., ge=0)
    amount_text: Optional[str] = None


class QuotationLineItem(BaseModel):
    """품목 — part_number/description은 강조 마크업 입력 허용.

    *_text가 채워진 행/구간은 PDF가 그 문자열을 표시하고 합계에서 제외.
    """
    line_no: int = Field(..., ge=1)
    part_number: str
    description: Optional[str] = None
    quantity: Decimal = Field(..., ge=0)
    quantity_text: Optional[str] = None
    uom: str = "EA"
    unit_price: Decimal = Field(..., ge=0)
    unit_price_text: Optional[str] = None
    amount: Decimal = Field(..., ge=0)
    amount_text: Optional[str] = None
    line_remarks: Optional[str] = None
    # MOQ 모드: 같은 품목의 수량 구간별 단가 묶음 (None이면 단일 행 일반 모드)
    price_tiers: Optional[List[PriceTier]] = None


class QuotationTerms(BaseModel):
    """거래 조건"""
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    incoterms: Optional[Incoterms] = None
    valid_until: Optional[str] = None
    country_of_origin: Optional[str] = None
    hs_code: Optional[str] = None
    remarks: Optional[str] = None
    # CI(Commercial Invoice) 전용 선적 정보
    ship_from: Optional[str] = None
    destination: Optional[str] = None
    transportation: Optional[str] = None
    shipment_date: Optional[str] = None
    # CI 원산지 신고문(Statement of Origin) — 표기 선택 시에만 채워짐
    # {text, place, date, coo_title, sales_title}
    statement_of_origin: Optional[dict] = None


class PackageLine(BaseModel):
    """CI Package Details 박스 라인 (packing list 1줄)"""
    box_type: Optional[str] = None             # 박스 종류/식별
    quantity: Optional[int] = None             # 동일 박스 개수
    gross_weight: Optional[Decimal] = None     # 총중량 kg (박스당)
    net_weight: Optional[Decimal] = None       # 순중량 kg (박스당)
    dimensions: Optional[str] = None           # 치수 (L x W x H, cm)


class PackageDetails(BaseModel):
    """CI 포장 명세 (Package Details) — 요약값 + 박스별 라인"""
    boxes: Optional[int] = None                # 총 박스 수
    dimensions: Optional[str] = None           # 치수 (단일 박스형 요약)
    gross_weight: Optional[Decimal] = None     # 총중량 (kg)
    net_weight: Optional[Decimal] = None       # 순중량 (kg)
    total_quantity: Optional[Decimal] = None   # 총 수량 (품목 합계)
    lines: Optional[List[PackageLine]] = None  # 박스별 라인 (packing list)


class QuotationPdfData(BaseModel):
    """견적서/PI PDF 1건의 모든 렌더 데이터.

    document_type 으로 Q/PI/CI 구분.
    """
    language: Language = Language.KO
    document_type: Literal["QUOTATION", "PI", "CI", "INVOICE"] = "QUOTATION"

    # 문서 메타
    document_number: str
    document_date: date
    version: int = 1
    po_number: Optional[str] = None  # PI 전용: 고객이 보낸 PO 번호

    # 발행사 / 고객사 / 선적지
    company: CompanyInfo
    customer: CustomerInfo
    ship_to: ShipToInfo = Field(default_factory=ShipToInfo)

    # 품목
    items: List[QuotationLineItem]

    # MOQ(수량 구간별 단가) 모드 여부 — 헤더를 "Quantity" 대신 "MOQ"로 표기
    is_moq: bool = False

    # 혼합 견적 지원용 — 한 문서 안에 단일/MOQ 품목이 섞여 있을 때 헤더 라벨 조정
    has_multi_tier: bool = False    # 2개 이상 tier를 가진 품목 존재 (MOQ 행)
    has_single_tier_in_moq: bool = False  # MOQ 문서이지만 단일 tier 품목도 존재

    # TBD 등 텍스트 오버라이드 항목이 하나라도 포함되어 있으면 True
    # 템플릿이 "* TBD items not included in total" 각주를 자동 표시
    has_tbd: bool = False

    # 통화 및 합계
    currency: Currency = Currency.USD
    subtotal: Decimal = Field(..., ge=0)
    discount_amount: Decimal = Field(Decimal("0"), ge=0)  # 할인 (총액에서 차감)
    discount_reason: Optional[str] = None                 # 할인 사유 (견적서 기록)
    shipping_fee: Decimal = Field(Decimal("0"), ge=0)     # 배송비 (총액에 가산)
    vat_rate: Decimal = Field(Decimal("0"), ge=0)
    vat_amount: Decimal = Field(Decimal("0"), ge=0)
    total: Decimal = Field(..., ge=0)
    vat_excluded: bool = False  # 국내 양식의 "부가세별도" 표기

    # 거래조건
    terms: QuotationTerms = Field(default_factory=QuotationTerms)

    # CI 전용: 포장 명세 / 연결 PI·PO 정보
    package: Optional[PackageDetails] = None
    pi_number: Optional[str] = None   # 연결된 PI 번호
    pi_date: Optional[str] = None     # 연결된 PI 일자
    po_date: Optional[str] = None     # 고객 PO 일자

    # 송금 계좌 (해외 견적용)
    bank: Optional[BankInfo] = None

    # 서명/직인
    prepared_by: Optional[str] = None
    prepared_email: Optional[str] = None
    stamp_omitted: bool = False  # 국내 양식의 "직인생략" 표시


def default_company_info() -> CompanyInfo:
    """엑스빔테크(주) 기본 정보 — 견적서 샘플 PDF에서 추출.
    Phase 4 이후 settings/DB로 이전 예정.
    """
    return CompanyInfo(
        name_ko="엑스빔테크㈜",
        name_en="X-Beam Tech Co.,Ltd.",
        representative_ko="김 행 정",
        address_ko="서울시 금천구 가산디지털1로 205, 304호",
        address_en="#304-306, 205, Gasan digital 1-ro, Geumcheon-gu, Seoul, 08501, Republic of Korea",
        business_type_ko="제조업 외",
        business_item_ko="연구개발 외",
        tel="02-864-7280",
        fax="02-864-7281",
        email="sales@xbeamtech.co.kr",
    )
