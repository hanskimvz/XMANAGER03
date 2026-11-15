"""
부품 마스터 스키마
API 요청/응답을 위한 Pydantic 스키마를 정의합니다.

v0.10.0: 품번 구조 변경 (부품코드 관리기준서 적용)
- 품번 구조: [대분류]-[소분류]-[품목코드]-[재질]-[후처리]
- 예시: HB1-DCP-00001-A6-NK
- 분류 필드 추가: development_type_id, part_type_ids (다중선택), drawing_type_id
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# ==================== 부품 마스터 (Parts) v0.10.0 ====================

class PartBase(BaseModel):
    """부품 기본 스키마 (v0.10.0)"""
    # 기본 정보
    # v0.22.0: part_name을 Optional로 변경 (엑셀 업로드 시 description에서 자동 생성)
    part_name: Optional[str] = Field(None, max_length=200, description="부품명 (미입력 시 description에서 자동 생성)")
    part_name_en: Optional[str] = Field(None, max_length=200, description="영문 부품명")
    description: Optional[str] = Field(None, description="설명")

    # ========================================
    # 품번 구성요소 (v0.11.0 신규)
    # ========================================
    product_line_id: Optional[int] = Field(None, description="대분류/제품라인 ID (HB01, BI03 등)")
    part_group_id: Optional[int] = Field(None, description="소분류/품목군 ID (DCP, PLP 등)")
    item_code_prefix: Optional[str] = Field(None, max_length=3, description="품목코드 앞 3자리 (사용자 입력)")
    # item_code 뒤 2자리는 자동 생성됨

    # ========================================
    # 분류 속성 (검색/필터용, v0.10.0 신규)
    # ========================================
    development_type_id: Optional[int] = Field(None, description="개발구분 ID (D, S, M 등)")
    part_type_ids: Optional[List[int]] = Field(None, description="부품유형 ID 목록 (다중선택)")
    drawing_type_id: Optional[int] = Field(None, description="도면여부 ID (D, S, N)")

    # ========================================
    # Legacy 분류 코드 (하위 호환성)
    # ========================================
    major_category_id: Optional[int] = Field(None, description="[Legacy] 대분류 ID")
    middle_category_id: Optional[int] = Field(None, description="[Legacy] 중분류 ID")
    minor_category_id: Optional[int] = Field(None, description="[Legacy] 소분류 ID")
    sub_category_id: Optional[int] = Field(None, description="[Legacy] 세분류 ID")
    item_code_id: Optional[int] = Field(None, description="[Legacy] 품목코드 ID")

    # ========================================
    # 공통 속성
    # ========================================
    material_id: Optional[int] = Field(None, description="재질 ID")
    treatment_id: Optional[int] = Field(None, description="후처리 ID")
    level_id: Optional[int] = Field(None, description="레벨 ID (품번 구성요소, v0.20.0)")

    # 조달 정보
    procurement_type_id: Optional[int] = Field(None, description="조달구분 ID")

    # 규격 정보
    specification: Optional[str] = Field(None, max_length=500, description="규격")
    unit_id: Optional[int] = Field(None, description="단위 ID")

    # 버전 관리
    version: str = Field(default="A0", max_length=10, description="버전")
    revision: int = Field(default=0, description="리비전 번호")
    revision_note: Optional[str] = Field(None, description="리비전 노트")

    # 가격 정보 (v0.18.0 원가관리)
    unit_price: Optional[Decimal] = Field(default=0, description="[Legacy] 단가")
    currency: str = Field(default="KRW", max_length=10, description="기본 통화")
    price_updated_at: Optional[datetime] = Field(None, description="단가 갱신일")

    # 기준단가
    standard_price: Optional[Decimal] = Field(default=0, description="기준단가 (수동 입력)")
    standard_price_currency: str = Field(default="KRW", max_length=10, description="기준단가 통화")

    # BOM 기반 원가 (v0.18.0)
    cost_type: str = Field(default="MANUAL", max_length=20, description="원가유형 (MANUAL/BOM/PROCESS)")
    material_cost: Optional[Decimal] = Field(default=0, description="재료비")
    material_cost_currency: str = Field(default="KRW", max_length=10, description="재료비 통화")
    labor_cost: Optional[Decimal] = Field(default=0, description="가공비/노무비")
    labor_cost_currency: str = Field(default="KRW", max_length=10, description="가공비 통화")
    overhead_cost: Optional[Decimal] = Field(default=0, description="경비")
    overhead_cost_currency: str = Field(default="KRW", max_length=10, description="경비 통화")

    # 조달 정보
    supplier_id: Optional[int] = Field(None, description="주 공급업체 ID")
    lead_time_days: Optional[int] = Field(None, description="리드타임 (일)")
    min_order_qty: int = Field(default=1, description="최소 주문 수량")

    # 첨부파일
    file_name: Optional[str] = Field(None, max_length=500, description="도면 파일명")
    drawing_file: Optional[str] = Field(None, max_length=500, description="도면 파일 경로")
    photo_file: Optional[str] = Field(None, max_length=500, description="사진 파일 경로")
    document_files: Optional[List[Dict[str, Any]]] = Field(None, description="기타 문서 (JSON 배열)")

    # 승인 상태
    approval_status: str = Field(default="DRAFT", max_length=20, description="승인상태")
    approved_by: Optional[int] = Field(None, description="승인자 ID")
    approved_at: Optional[datetime] = Field(None, description="승인일시")

    # 상태
    status: str = Field(default="ACTIVE", max_length=20, description="상태")
    is_active: bool = Field(default=True, description="사용여부")

    # v0.79.0: 전속(독점) 공급 계약 (opt-in)
    is_protected: bool = Field(default=False, description="전속계약 여부 (특정 고객 전용)")
    protected_customer_id: Optional[int] = Field(None, description="전속 고객 ID")
    protection_note: Optional[str] = Field(None, description="전속계약 비고")

    # 비고
    remark: Optional[str] = Field(None, description="비고")


class PartCreate(PartBase):
    """
    부품 생성 스키마 (v0.20.0 - 직접 입력 모드 추가)

    두 가지 모드 지원:
    1. 품번규칙 A 모드: product_line_id, part_group_id, item_code_prefix, level_id 필수
    2. 직접 입력 모드: part_number 직접 입력

    품번규칙 A 모드 예시: HB01-DCP-001-01-A6-NK-R
    직접 입력 모드 예시: COTS-SO-S31-06-NB-NN
    """
    # 직접 입력 모드 (v0.19.2)
    part_number: Optional[str] = Field(None, max_length=30, description="품번 직접 입력 (직접 입력 모드)")
    part_number_display: Optional[str] = Field(None, max_length=35, description="품번 표시용 (하이픈 포함)")

    # 품번 구성요소 - 품번규칙 A 모드에서 필수 (직접 입력 모드에서는 Optional)
    product_line_id: Optional[int] = Field(None, description="대분류/제품라인 ID")
    part_group_id: Optional[int] = Field(None, description="소분류/품목군 ID")
    item_code_prefix: Optional[str] = Field(None, min_length=3, max_length=3, description="품목코드 앞 3자리")
    item_code_suffix: Optional[str] = Field(None, min_length=2, max_length=2, description="품목코드 뒤 2자리 (직접 입력, 비워두면 자동생성)")
    level_id: Optional[int] = Field(None, description="레벨 ID")


class PartUpdate(BaseModel):
    """부품 수정 스키마 (v0.19.1)"""
    # 품번 직접 수정 (v0.12.0)
    # 품번을 직접 수정하면 분류 속성 변경 시에도 품번이 유지됨
    part_number: Optional[str] = Field(None, max_length=25, description="품번 (직접 수정)")
    part_number_display: Optional[str] = Field(None, max_length=30, description="품번 표시용 (하이픈 포함)")

    # 품번규칙 A 모드 (v0.19.1)
    regenerate_part_number: bool = Field(default=False, description="품번 재생성 여부 (품번규칙 A 모드)")
    item_code_prefix: Optional[str] = Field(None, max_length=3, description="품목코드 앞 3자리 (품번규칙 A 모드)")
    item_code_suffix: Optional[str] = Field(None, min_length=2, max_length=2, description="품목코드 뒤 2자리 (직접 입력)")

    # 기본 정보
    part_name: Optional[str] = Field(None, max_length=200)
    part_name_en: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None

    # 신규 분류 코드 (v0.10.0)
    product_line_id: Optional[int] = None
    part_group_id: Optional[int] = None
    development_type_id: Optional[int] = None
    part_type_ids: Optional[List[int]] = None
    drawing_type_id: Optional[int] = None

    # Legacy 분류 코드 (하위 호환성)
    major_category_id: Optional[int] = None
    middle_category_id: Optional[int] = None
    minor_category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    item_code_id: Optional[int] = None

    # 공통 속성
    material_id: Optional[int] = None
    treatment_id: Optional[int] = None
    level_id: Optional[int] = None

    # 조달 정보
    procurement_type_id: Optional[int] = None

    # 규격 정보
    specification: Optional[str] = Field(None, max_length=500)
    unit_id: Optional[int] = None

    # 버전 관리
    version: Optional[str] = Field(None, max_length=10)
    revision: Optional[int] = None
    revision_note: Optional[str] = None

    # 가격 정보 (v0.18.0)
    unit_price: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=10)
    price_updated_at: Optional[datetime] = None
    standard_price: Optional[Decimal] = None
    standard_price_currency: Optional[str] = Field(None, max_length=10)

    # BOM 기반 원가 (v0.18.0)
    cost_type: Optional[str] = Field(None, max_length=20)
    material_cost: Optional[Decimal] = None
    material_cost_currency: Optional[str] = Field(None, max_length=10)
    labor_cost: Optional[Decimal] = None
    labor_cost_currency: Optional[str] = Field(None, max_length=10)
    overhead_cost: Optional[Decimal] = None
    overhead_cost_currency: Optional[str] = Field(None, max_length=10)

    # 조달 정보
    supplier_id: Optional[int] = None
    lead_time_days: Optional[int] = None
    min_order_qty: Optional[int] = None

    # 첨부파일
    file_name: Optional[str] = Field(None, max_length=500)
    drawing_file: Optional[str] = Field(None, max_length=500)
    photo_file: Optional[str] = Field(None, max_length=500)
    document_files: Optional[List[Dict[str, Any]]] = None

    # 승인 상태
    approval_status: Optional[str] = Field(None, max_length=20)
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None

    # 상태
    status: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None

    # v0.79.0: 전속 계약
    is_protected: Optional[bool] = None
    protected_customer_id: Optional[int] = None
    protection_note: Optional[str] = None

    # 비고
    remark: Optional[str] = None


class CodeMasterInfo(BaseModel):
    """코드 마스터 정보 (관계 데이터용)"""
    id: int
    code: str
    name_ko: str
    name_en: Optional[str] = None

    class Config:
        from_attributes = True


class ProtectedCustomerBrief(BaseModel):
    """전속 고객 간단 정보 (배지 표시용)"""
    id: int
    partner_name: Optional[str] = None

    class Config:
        from_attributes = True


class PartResponse(PartBase):
    """부품 응답 스키마 (v0.12.0)"""
    id: int
    part_uid: Optional[str] = None  # 고유 ID (PT-XXXXXXXX, 바코드용, 변경불가)
    part_number: str
    part_number_display: Optional[str] = None  # 표시용 품번 (하이픈 포함)
    item_code: Optional[str] = None  # 품목코드 5자리
    is_classified: bool = True  # 미분류(False)=코드·레벨 미부여 잠정 부품
    version: Optional[str] = None  # 버전 (기존 데이터 호환)

    # 관계 데이터 (v0.10.0)
    product_line: Optional[CodeMasterInfo] = None
    part_group: Optional[CodeMasterInfo] = None
    development_type: Optional[CodeMasterInfo] = None
    drawing_type: Optional[CodeMasterInfo] = None
    part_types: Optional[List[CodeMasterInfo]] = None

    # 공통 관계 데이터
    material: Optional[CodeMasterInfo] = None
    treatment: Optional[CodeMasterInfo] = None
    level: Optional[CodeMasterInfo] = None

    # 원가 정보 (v0.18.0)
    inventory_avg_price: Optional[Decimal] = None
    inventory_avg_price_currency: Optional[str] = None
    latest_price: Optional[Decimal] = None
    latest_price_currency: Optional[str] = None
    latest_price_date: Optional[datetime] = None

    # 계산된 원가 (v0.18.0)
    calculated_cost: Optional[Decimal] = None
    calculated_cost_currency: Optional[str] = None
    cost_calculated_at: Optional[datetime] = None

    # 감사 정보
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None

    # v0.79.0: 전속 고객(관계)
    protected_customer: Optional[ProtectedCustomerBrief] = None

    class Config:
        from_attributes = True


class PartListResponse(BaseModel):
    """부품 목록 응답 스키마 (간략 버전, v0.12.0)"""
    id: int
    part_uid: Optional[str] = None  # 고유 ID (PT-XXXXXXXX, 바코드용)
    part_number: str
    part_number_display: Optional[str] = None  # 표시용 품번 (하이픈 포함)
    part_name: str
    part_name_en: Optional[str] = None
    description: Optional[str] = None  # 설명
    item_code: Optional[str] = None  # 품목코드 5자리
    specification: Optional[str] = None
    version: Optional[str] = None  # 버전 (기존 데이터 호환)
    status: Optional[str] = None  # 상태 (기존 데이터 호환)
    is_active: bool = True
    is_classified: bool = True  # BOM 개편: 미분류(False)=코드·레벨 미부여 잠정 부품
    created_at: datetime

    # v0.79.0: 전속 계약 (배지/경고용)
    is_protected: bool = False
    protected_customer_id: Optional[int] = None
    protection_note: Optional[str] = None
    protected_customer: Optional[ProtectedCustomerBrief] = None

    # 관계 데이터 (v0.10.0)
    product_line: Optional[CodeMasterInfo] = None
    part_group: Optional[CodeMasterInfo] = None
    material: Optional[CodeMasterInfo] = None
    level: Optional[CodeMasterInfo] = None

    class Config:
        from_attributes = True


class PartSearchParams(BaseModel):
    """부품 검색 파라미터 (v0.10.0)"""
    keyword: Optional[str] = Field(None, description="검색 키워드 (품번, 부품명)")

    # 신규 분류 필터 (v0.10.0)
    product_line_id: Optional[int] = Field(None, description="대분류/제품라인 필터")
    part_group_id: Optional[int] = Field(None, description="소분류/품목군 필터")
    development_type_id: Optional[int] = Field(None, description="개발구분 필터")
    part_type_id: Optional[int] = Field(None, description="부품유형 필터")
    drawing_type_id: Optional[int] = Field(None, description="도면여부 필터")

    # Legacy 분류 필터 (하위 호환성)
    major_category_id: Optional[int] = Field(None, description="[Legacy] 대분류 필터")
    middle_category_id: Optional[int] = Field(None, description="[Legacy] 중분류 필터")
    minor_category_id: Optional[int] = Field(None, description="[Legacy] 소분류 필터")

    # 공통 필터
    level_id: Optional[int] = Field(None, description="레벨 필터")
    material_id: Optional[int] = Field(None, description="재질 필터")
    status: Optional[str] = Field(None, description="상태 필터")
    is_active: Optional[bool] = Field(None, description="사용여부 필터")

    # 페이지네이션
    skip: int = Field(default=0, ge=0, description="건너뛸 개수")
    limit: int = Field(default=100, ge=1, le=1000, description="조회 개수")
    order_by: Optional[str] = Field(default="created_at", description="정렬 기준 컬럼")
    order_desc: bool = Field(default=True, description="내림차순 정렬 여부")


class PartPaginatedResponse(BaseModel):
    """부품 목록 페이지네이션 응답 스키마"""
    items: List[PartListResponse] = Field(description="부품 목록")
    total: int = Field(description="총 개수")
    skip: int = Field(description="건너뛴 개수")
    limit: int = Field(description="조회 개수")
    has_more: bool = Field(description="추가 데이터 존재 여부")


# ==================== 조합/키트 (Assembly/Kit) 스키마 ====================

class AssemblyCreate(BaseModel):
    """
    조합/키트 생성 스키마

    자유형식 코드를 사용하여 조합(Assembly), 키트(Kit), 서브조합(Sub-Assembly) 등을 등록합니다.
    품번은 사용자가 직접 입력하며, 대분류/소분류/품목코드는 선택사항입니다.

    코드 예시:
    - CONNECTOR-KIT-001 (커넥터 키트)
    - HB01-ASY-PLUG-001 (플러그 조합)
    - SUB-OPTICAL-001 (광학 서브조합)
    """
    # 품번 (필수 - 사용자 직접 입력)
    part_number: str = Field(..., min_length=3, max_length=25, description="품번 (자유형식, 필수)")

    # 기본 정보
    part_name: str = Field(..., max_length=200, description="조합/키트명 (필수)")
    part_name_en: Optional[str] = Field(None, max_length=200, description="영문명")
    description: Optional[str] = Field(None, description="설명")

    # 레벨 (필수 - K:키트, S:서브어셈블리, P:패키지, F:완제품 등)
    level_id: int = Field(..., description="레벨 ID (K:키트, S:서브어셈블리, P:패키지, F:완제품)")

    # 분류 (선택 - 기존 부품과 연계 시 사용)
    product_line_id: Optional[int] = Field(None, description="대분류/제품라인 ID (선택)")
    part_group_id: Optional[int] = Field(None, description="소분류/품목군 ID (선택)")

    # 분류 속성 (선택)
    development_type_id: Optional[int] = Field(None, description="개발구분 ID")
    part_type_ids: Optional[List[int]] = Field(None, description="부품유형 ID 목록")
    drawing_type_id: Optional[int] = Field(None, description="도면여부 ID")

    # 규격 정보
    specification: Optional[str] = Field(None, max_length=500, description="규격")
    unit_id: Optional[int] = Field(None, description="단위 ID")

    # 가격 정보
    unit_price: Optional[Decimal] = Field(default=0, description="단가")
    currency: str = Field(default="KRW", max_length=10, description="통화")

    # 상태
    status: str = Field(default="ACTIVE", max_length=20, description="상태")
    is_active: bool = Field(default=True, description="사용여부")

    # 비고
    remark: Optional[str] = Field(None, description="비고")


class PartAttachmentResponse(BaseModel):
    """부품 첨부파일 응답 (v0.96.0)"""
    id: int
    part_id: int
    kind: str
    filename: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    uploaded_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
