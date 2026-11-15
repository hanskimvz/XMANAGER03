"""
거래처 관리 Pydantic 스키마
공급업체와 고객사를 통합 관리합니다.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class BusinessPartnerBase(BaseModel):
    """거래처 기본 스키마"""

    partner_code: str = Field(..., min_length=1, max_length=10, pattern=r'^[A-Za-z0-9]{1,10}$', description="거래처 코드 (알파벳 2자리)")
    partner_name: str = Field(..., min_length=1, max_length=200, description="거래처명")
    partner_name_en: Optional[str] = Field(None, max_length=200, description="영문 거래처명")
    business_number: Optional[str] = Field(None, max_length=20, description="사업자등록번호")
    representative: Optional[str] = Field(None, max_length=100, description="대표자명")
    business_type: Optional[str] = Field(None, max_length=100, description="업태")
    business_item: Optional[str] = Field(None, max_length=100, description="종목")

    # 거래처 유형
    is_supplier: bool = Field(False, description="공급업체 여부")
    is_customer: bool = Field(False, description="고객사 여부")
    trade_type: Optional[str] = Field("EXPORT", description="거래유형 (DOMESTIC: 국내, EXPORT: 해외)")

    # v0.23.0: 국가/지역 정보
    country_code: Optional[str] = Field(None, max_length=3, description="국가코드 (ISO 3166-1: KR, US, CN 등)")
    country_name: Optional[str] = Field(None, max_length=100, description="국가명")
    continent: Optional[str] = Field(None, max_length=20, description="대륙 (ASIA, EUROPE, NORTH_AMERICA 등)")

    # v0.23.0: 고객 분류 정보
    application_field: Optional[str] = Field(None, max_length=500, description="응용분야 (FTTH, 스마트시티 등)")
    customer_type: Optional[str] = Field(None, max_length=20, description="고객유형 (OEM, SI, DISTRIBUTOR)")
    business_start_year: Optional[int] = Field(None, ge=1900, le=2100, description="거래시작년도")

    # 주소
    address: Optional[str] = Field(None, max_length=500, description="주소")
    address_detail: Optional[str] = Field(None, max_length=200, description="상세주소")
    postal_code: Optional[str] = Field(None, max_length=10, description="우편번호")

    # 연락처
    tel: Optional[str] = Field(None, max_length=50, description="전화번호")
    fax: Optional[str] = Field(None, max_length=50, description="팩스번호")
    email: Optional[str] = Field(None, max_length=200, description="이메일")
    website: Optional[str] = Field(None, max_length=200, description="웹사이트")

    # 담당자 정보
    manager_name: Optional[str] = Field(None, max_length=100, description="담당자명")
    manager_position: Optional[str] = Field(None, max_length=50, description="담당자 직책")
    manager_tel: Optional[str] = Field(None, max_length=50, description="담당자 전화")
    manager_mobile: Optional[str] = Field(None, max_length=50, description="담당자 휴대폰")
    manager_email: Optional[str] = Field(None, max_length=200, description="담당자 이메일")

    # 공급업체용 필드
    payment_terms: Optional[str] = Field(None, max_length=200, description="결제 조건")
    delivery_terms: Optional[str] = Field(None, max_length=200, description="납품 조건")
    lead_time_days: Optional[int] = Field(None, ge=0, description="리드타임(일)")

    # 고객사용 필드
    credit_limit: Optional[Decimal] = Field(None, ge=0, description="신용한도")
    discount_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="할인율(%)")
    sales_rep: Optional[str] = Field(None, max_length=100, description="영업담당자")

    # 공통 평가 필드
    credit_rating: Optional[str] = Field(None, max_length=10, description="신용등급")
    grade: Optional[str] = Field(None, max_length=10, description="거래처 등급")

    # 은행 정보
    bank_name: Optional[str] = Field(None, max_length=100, description="은행명")
    bank_account: Optional[str] = Field(None, max_length=50, description="계좌번호")
    bank_holder: Optional[str] = Field(None, max_length=100, description="예금주")
    swift_code: Optional[str] = Field(None, max_length=20, description="SWIFT 코드")
    bank_address: Optional[str] = Field(None, max_length=500, description="은행 주소")

    # v0.24.0: 영업 문서 생성용 필드
    short_code: Optional[str] = Field(None, max_length=5, description="업체 약어 코드 (Q/PI/CI 번호용, 예: BI, IH)")
    hs_code: Optional[str] = Field(None, max_length=100, description="HS Code")
    show_statement_of_origin: Optional[bool] = Field(None, description="CI 원산지 신고문 표기 기본값")
    default_margin_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="기본 마진율(%)")
    # v0.78.0: 생산요청/문서 기본값
    default_shipping_mark: Optional[str] = Field(None, description="기본 SHIPPING MARK")
    default_consignee: Optional[str] = Field(None, description="기본 CONSIGNEE(수하인)")
    default_destination: Optional[str] = Field(None, description="기본 DESTINATION(도착지)")

    # 상태
    is_active: bool = Field(True, description="활성 여부")
    remark: Optional[str] = Field(None, description="비고")


class BusinessPartnerCreate(BusinessPartnerBase):
    """거래처 생성 스키마"""
    pass


class BusinessPartnerUpdate(BaseModel):
    """거래처 수정 스키마 (모든 필드 선택적)"""

    partner_code: Optional[str] = Field(None, min_length=1, max_length=10, pattern=r'^[A-Za-z0-9]{1,10}$')
    partner_name: Optional[str] = Field(None, min_length=1, max_length=200)
    partner_name_en: Optional[str] = Field(None, max_length=200)
    business_number: Optional[str] = Field(None, max_length=20)
    representative: Optional[str] = Field(None, max_length=100)
    business_type: Optional[str] = Field(None, max_length=100)
    business_item: Optional[str] = Field(None, max_length=100)

    is_supplier: Optional[bool] = None
    is_customer: Optional[bool] = None
    trade_type: Optional[str] = None

    # v0.23.0: 국가/지역 정보
    country_code: Optional[str] = Field(None, max_length=3)
    country_name: Optional[str] = Field(None, max_length=100)
    continent: Optional[str] = Field(None, max_length=20)

    # v0.23.0: 고객 분류 정보
    application_field: Optional[str] = Field(None, max_length=500)
    customer_type: Optional[str] = Field(None, max_length=20)
    business_start_year: Optional[int] = Field(None, ge=1900, le=2100)

    address: Optional[str] = Field(None, max_length=500)
    address_detail: Optional[str] = Field(None, max_length=200)
    postal_code: Optional[str] = Field(None, max_length=10)

    tel: Optional[str] = Field(None, max_length=50)
    fax: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=200)
    website: Optional[str] = Field(None, max_length=200)

    manager_name: Optional[str] = Field(None, max_length=100)
    manager_position: Optional[str] = Field(None, max_length=50)
    manager_tel: Optional[str] = Field(None, max_length=50)
    manager_mobile: Optional[str] = Field(None, max_length=50)
    manager_email: Optional[str] = Field(None, max_length=200)

    payment_terms: Optional[str] = Field(None, max_length=200)
    delivery_terms: Optional[str] = Field(None, max_length=200)
    lead_time_days: Optional[int] = Field(None, ge=0)

    credit_limit: Optional[Decimal] = Field(None, ge=0)
    discount_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    sales_rep: Optional[str] = Field(None, max_length=100)

    credit_rating: Optional[str] = Field(None, max_length=10)
    grade: Optional[str] = Field(None, max_length=10)

    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=50)
    bank_holder: Optional[str] = Field(None, max_length=100)
    swift_code: Optional[str] = Field(None, max_length=20)
    bank_address: Optional[str] = Field(None, max_length=500)

    # v0.24.0
    short_code: Optional[str] = Field(None, max_length=5)
    hs_code: Optional[str] = Field(None, max_length=100)
    show_statement_of_origin: Optional[bool] = Field(None, description="CI 원산지 신고문 표기 기본값")
    default_margin_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    # v0.78.0
    default_shipping_mark: Optional[str] = None
    default_consignee: Optional[str] = None
    default_destination: Optional[str] = None

    is_active: Optional[bool] = None
    remark: Optional[str] = None


class BusinessPartnerResponse(BusinessPartnerBase):
    """거래처 응답 스키마"""

    id: int
    document_files: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="첨부 문서 파일 목록")
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BusinessPartnerListItem(BaseModel):
    """거래처 목록 아이템 (간소화된 정보)"""

    id: int
    partner_code: str
    partner_name: str
    partner_name_en: Optional[str] = None
    is_supplier: bool
    is_customer: bool
    trade_type: Optional[str] = None
    # v0.23.0: 국가/고객 분류
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    continent: Optional[str] = None
    customer_type: Optional[str] = None
    tel: Optional[str] = None
    manager_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessPartnerSearchParams(BaseModel):
    """거래처 검색 파라미터"""

    keyword: Optional[str] = Field(None, description="검색 키워드 (코드, 거래처명)")
    is_supplier: Optional[bool] = Field(None, description="공급업체 필터")
    is_customer: Optional[bool] = Field(None, description="고객사 필터")
    is_active: Optional[bool] = Field(None, description="활성 여부 필터")
    skip: int = Field(0, ge=0, description="건너뛸 레코드 수")
    limit: int = Field(100, ge=1, le=1000, description="최대 레코드 수")


class BusinessPartnerPaginatedResponse(BaseModel):
    """거래처 목록 페이지네이션 응답 스키마"""
    items: List[BusinessPartnerListItem] = Field(description="거래처 목록")
    total: int = Field(description="총 개수")
    skip: int = Field(description="건너뛴 개수")
    limit: int = Field(description="조회 개수")
    has_more: bool = Field(description="추가 데이터 존재 여부")
