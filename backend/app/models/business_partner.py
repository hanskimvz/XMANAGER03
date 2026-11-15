"""
거래처 테이블 모델
공급업체와 고객사를 통합 관리합니다.
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class BusinessPartner(Base):
    """
    거래처 (Business Partner)
    공급업체와 고객사를 통합 관리합니다.
    한 업체가 공급업체이면서 동시에 고객사일 수 있습니다.
    """
    __tablename__ = "business_partner"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 기본 정보
    partner_code = Column(String(50), unique=True, nullable=False, index=True, comment="거래처 코드")
    partner_name = Column(String(200), nullable=False, comment="거래처명")
    partner_name_en = Column(String(200), comment="영문 거래처명")
    business_number = Column(String(20), comment="사업자등록번호")
    representative = Column(String(100), comment="대표자명")
    business_type = Column(String(100), comment="업태")
    business_item = Column(String(100), comment="종목")

    # 거래처 유형 (복수 선택 가능)
    is_supplier = Column(Boolean, default=False, comment="공급업체 여부")
    is_customer = Column(Boolean, default=False, comment="고객사 여부")

    # v0.26.0: 거래 유형 (국내/해외 구분)
    trade_type = Column(String(10), default="EXPORT", comment="거래유형 (DOMESTIC: 국내, EXPORT: 해외)")

    # v0.23.0: 국가/지역 정보 (매출 분석용)
    country_code = Column(String(3), comment="국가코드 (ISO 3166-1: KR, US, CN, EE 등)")
    country_name = Column(String(100), comment="국가명")
    continent = Column(String(20), comment="대륙 (ASIA, EUROPE, NORTH_AMERICA, SOUTH_AMERICA, OCEANIA, AFRICA)")

    # v0.23.0: 고객 분류 정보
    application_field = Column(String(500), comment="응용분야 (FTTH, 스마트시티, 방산, 통신 등)")
    customer_type = Column(String(20), comment="고객유형 (OEM, SI, DISTRIBUTOR)")
    business_start_year = Column(Integer, comment="거래시작년도")

    # 주소
    address = Column(String(500), comment="주소")
    address_detail = Column(String(200), comment="상세주소")
    postal_code = Column(String(10), comment="우편번호")

    # 연락처 정보
    tel = Column(String(50), comment="전화번호")
    fax = Column(String(50), comment="팩스번호")
    email = Column(String(200), comment="이메일")
    website = Column(String(200), comment="웹사이트")

    # 담당자 정보
    manager_name = Column(String(100), comment="담당자명")
    manager_position = Column(String(50), comment="담당자 직책")
    manager_tel = Column(String(50), comment="담당자 전화")
    manager_mobile = Column(String(50), comment="담당자 휴대폰")
    manager_email = Column(String(200), comment="담당자 이메일")

    # 공급업체용 필드
    payment_terms = Column(String(200), comment="결제 조건")
    delivery_terms = Column(String(200), comment="납품 조건")
    lead_time_days = Column(Integer, comment="리드타임(일)")

    # 고객사용 필드
    credit_limit = Column(Numeric(15, 2), comment="신용한도")
    discount_rate = Column(Numeric(5, 2), comment="할인율(%)")
    sales_rep = Column(String(100), comment="영업담당자")

    # 공통 평가 필드
    credit_rating = Column(String(10), comment="신용등급")
    grade = Column(String(10), comment="거래처 등급")

    # 은행 정보
    bank_name = Column(String(100), comment="은행명")
    bank_account = Column(String(50), comment="계좌번호")
    bank_holder = Column(String(100), comment="예금주")
    swift_code = Column(String(20), comment="SWIFT 코드")
    bank_address = Column(String(500), comment="은행 주소")

    # v0.24.0: 영업 문서 생성용 필드
    short_code = Column(String(5), comment="업체 약어 코드 (Q/PI/CI 번호 생성용, 예: BI, IH, MA)")
    hs_code = Column(String(100), comment="HS Code (기본값, 문서 생성 시 사용 — 복수 가능, 쉼표 구분)")
    show_statement_of_origin = Column(Boolean, default=False, nullable=False, server_default="false",
                                      comment="CI 원산지 신고문 표기 기본값 (이 거래처는 신고문 포함)")
    default_margin_rate = Column(Numeric(5, 2), comment="기본 마진율(%) - 견적 가격 산정용")
    # v0.78.0: 생산요청/문서 기본값 — 고객별 SHIPPING MARK / CONSIGNEE
    default_shipping_mark = Column(Text, comment="기본 SHIPPING MARK (생산요청 자동 채움)")
    default_consignee = Column(Text, comment="기본 CONSIGNEE(수하인) (생산요청 자동 채움)")
    default_destination = Column(Text, comment="기본 DESTINATION(도착지) (생산요청 자동 채움)")

    # 비고
    remark = Column(Text, comment="비고")

    # 첨부 파일 (사업자등록증, 계약서 등)
    document_files = Column(JSON, default=list, comment="첨부 문서 파일 목록")

    # v0.81.0 파일 허브: Nextcloud 거래처 루트 폴더(최초 생성 시 저장, 이후 불변 — 거래처명 변경에도 링크 유지)
    nextcloud_folder = Column(String(500), nullable=True, comment="Nextcloud 거래처 루트 폴더 상대경로")

    # 상태
    is_active = Column(Boolean, default=True, comment="활성 여부")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")
