"""
부품 마스터 테이블 모델
부품 정보를 관리합니다.

v0.10.0: 품번 구조 변경 (부품코드 관리기준서 적용)
- 품번 구조: [대분류]-[소분류]-[품목코드]-[재질]-[후처리]
- 예시: HB1-DCP-00001-A6-NK
- 레벨은 품번에서 제외, 별도 속성으로 관리
- 분류 필드 추가: development_type, part_types(M:N), drawing_type
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.code_master import part_part_type


class Part(Base):
    """
    부품 마스터 (Parts)
    모든 부품의 기본 정보를 관리합니다.

    품번 구조 (v0.10.0):
    - product_line_id: 대분류/제품라인 (HB1, BI3, TF1 등)
    - part_group_id: 소분류/품목군 (DCP, PLP, OCP 등)
    - item_code: 품목코드 5자리 (00001~99999)
    - material_id: 재질 (A6, S4 등)
    - treatment_id: 후처리 (NK, NN 등)
    """
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 고유 ID (v0.12.0) - 바코드/QR용, 변경 불가
    # 예: PT-3F7A2B1C (품번+생성시간 해시)
    part_uid = Column(String(12), unique=True, nullable=True, index=True, comment="고유 ID (PT-XXXXXXXX, 바코드용, 변경불가)")

    # 품번 (자동생성) - v0.10.0 구조
    # 예: HB1DCP00001A6NK (시스템용), HB1-DCP-00001-A6-NK (표시용)
    # v0.12.0: 품번 직접 수정 가능
    part_number = Column(String(100), unique=True, nullable=False, index=True, comment="품번 (시스템용, 수정가능)")
    part_number_display = Column(String(100), comment="품번 (표시용, 하이픈 포함)")
    # v0.96.0 미분류 부품: 코드·레벨 없이 이름만으로 등록(잠정 품번=UID). 나중에 '분류/채번'으로 승격
    is_classified = Column(Boolean, nullable=False, default=True, server_default="true", index=True,
                           comment="정식 분류(코드·레벨 부여) 여부. False=미분류(잠정)")

    # 기본 정보
    part_name = Column(String(200), nullable=False, comment="부품명")
    part_name_en = Column(String(200), comment="영문 부품명")
    description = Column(Text, comment="설명")

    # ========================================
    # 품번 구성요소 (v0.10.0 신규)
    # ========================================
    # 대분류/제품라인 (필수)
    product_line_id = Column(Integer, ForeignKey("product_line.id"), nullable=True, comment="대분류/제품라인 ID")
    # 소분류/품목군 (필수)
    part_group_id = Column(Integer, ForeignKey("part_group.id"), nullable=True, comment="소분류/품목군 ID")
    # 품목코드 5자리 (필수) - 동일 대분류+소분류 내에서 자동채번
    item_code = Column(String(5), nullable=True, comment="품목코드 (5자리)")

    # ========================================
    # 분류 속성 (검색/필터용, v0.10.0 신규)
    # ========================================
    # 개발구분 (분류1) - 단일선택
    development_type_id = Column(Integer, ForeignKey("development_type.id"), nullable=True, comment="개발구분 ID")
    # 부품유형 (분류2) - 다중선택: part_types relationship으로 처리
    # 도면여부 (분류3) - 단일선택
    drawing_type_id = Column(Integer, ForeignKey("drawing_type.id"), nullable=True, comment="도면여부 ID")

    # ========================================
    # Legacy 분류 코드 (하위 호환성, nullable로 변경)
    # ========================================
    major_category_id = Column(Integer, ForeignKey("major_category.id"), nullable=True, comment="[Legacy] 대분류 ID")
    middle_category_id = Column(Integer, ForeignKey("middle_category.id"), nullable=True, comment="[Legacy] 중분류 ID")
    minor_category_id = Column(Integer, ForeignKey("minor_category.id"), nullable=True, comment="[Legacy] 소분류 ID")
    sub_category_id = Column(Integer, ForeignKey("sub_category.id"), nullable=True, comment="[Legacy] 세분류 ID")
    item_code_id = Column(Integer, ForeignKey("item_code.id"), nullable=True, comment="[Legacy] 품목코드 ID")

    # ========================================
    # 공통 속성 (유지)
    # ========================================
    material_id = Column(Integer, ForeignKey("material.id"), nullable=True, comment="재질 ID")
    treatment_id = Column(Integer, ForeignKey("treatment.id"), nullable=True, comment="후처리 ID")
    level_id = Column(Integer, ForeignKey("level.id"), nullable=True, comment="레벨 ID (BOM용, 품번 미포함)")

    # 조달 정보
    procurement_type_id = Column(Integer, ForeignKey("procurement_type.id"), comment="조달구분 ID")

    # 규격 정보
    specification = Column(String(500), comment="규격 (AN016, SER-20 등)")
    unit_id = Column(Integer, ForeignKey("unit.id"), comment="단위 ID")

    # 버전 관리
    version = Column(String(10), default="A0", comment="버전")
    revision = Column(Integer, default=0, comment="리비전 번호")
    revision_note = Column(Text, comment="리비전 노트")

    # ========================================
    # 가격 정보 (v0.18.0 원가관리)
    # ========================================
    # 기존 필드 (하위 호환성)
    unit_price = Column(Numeric(15, 2), default=0, comment="[Legacy] 단가 - standard_price 사용 권장")
    currency = Column(String(10), default="KRW", comment="기본 통화 (KRW)")
    price_updated_at = Column(DateTime(timezone=True), comment="단가 최종 갱신일")

    # 기준단가 (Standard Price) - 사용자가 직접 입력하는 목표/기준 단가
    standard_price = Column(Numeric(15, 4), default=0, comment="기준단가 (수동 입력)")
    standard_price_currency = Column(String(10), default="KRW", comment="기준단가 통화")

    # 재고단가 (Inventory Average Price) - 이동평균법으로 계산
    # 입고 시: (기존재고금액 + 신규입고금액) / 총수량
    inventory_avg_price = Column(Numeric(15, 4), default=0, comment="재고단가 (이동평균)")
    inventory_avg_price_currency = Column(String(10), default="KRW", comment="재고단가 통화")

    # 최근단가 (Latest Price) - 가장 최근 입고 단가
    latest_price = Column(Numeric(15, 4), default=0, comment="최근단가 (최종 입고가)")
    latest_price_currency = Column(String(10), default="KRW", comment="최근단가 통화")
    latest_price_date = Column(DateTime(timezone=True), comment="최근단가 갱신일")
    latest_price_supplier_id = Column(Integer, ForeignKey("supplier.id"), comment="최근단가 공급업체 ID")

    # 평균단가 (Average Price) - 기간/건수별 계산 (API에서 동적 계산)
    # DB에는 캐시용으로만 저장 (주기적 배치로 갱신)
    avg_price_30d = Column(Numeric(15, 4), default=0, comment="평균단가 (최근 30일)")
    avg_price_90d = Column(Numeric(15, 4), default=0, comment="평균단가 (최근 90일)")
    avg_price_last5 = Column(Numeric(15, 4), default=0, comment="평균단가 (최근 5건)")
    avg_price_last10 = Column(Numeric(15, 4), default=0, comment="평균단가 (최근 10건)")

    # ========================================
    # BOM 기반 원가 계산 (v0.18.0)
    # ========================================
    # 원가 유형: MANUAL(단품-수동입력), BOM(조립품-하위품목 합산), PROCESS(공정비용)
    cost_type = Column(String(20), default="MANUAL", comment="원가유형 (MANUAL/BOM/PROCESS)")

    # 재료비 (Material Cost) - 단품: 직접입력, 조립품: BOM 합산
    material_cost = Column(Numeric(15, 4), default=0, comment="재료비")
    material_cost_currency = Column(String(10), default="KRW", comment="재료비 통화")

    # 가공비/노무비 (Labor Cost) - 공정 비용
    labor_cost = Column(Numeric(15, 4), default=0, comment="가공비/노무비")
    labor_cost_currency = Column(String(10), default="KRW", comment="가공비 통화")

    # 경비 (Overhead Cost) - 기타 간접비용
    overhead_cost = Column(Numeric(15, 4), default=0, comment="경비")
    overhead_cost_currency = Column(String(10), default="KRW", comment="경비 통화")

    # 계산된 원가 (Calculated Cost) - BOM 합산 결과 캐시
    # 단품: standard_price 사용, 조립품: material_cost + labor_cost + overhead_cost
    calculated_cost = Column(Numeric(15, 4), default=0, comment="계산된 원가 (캐시)")
    calculated_cost_currency = Column(String(10), default="KRW", comment="계산된 원가 통화")
    cost_calculated_at = Column(DateTime(timezone=True), comment="원가 계산일시")

    # 조달 정보
    supplier_id = Column(Integer, ForeignKey("supplier.id"), comment="주 공급업체 ID")
    lead_time_days = Column(Integer, comment="리드타임 (일)")
    min_order_qty = Column(Integer, default=1, comment="최소 주문 수량")

    # 대체품 그룹 (나중에 추가)
    # alt_part_group_id = Column(Integer, ForeignKey("alt_part_group.id"), comment="대체품 그룹 ID")

    # 첨부파일
    file_name = Column(String(500), comment="도면 파일명")
    drawing_file = Column(String(500), comment="도면 파일 경로")
    photo_file = Column(String(500), comment="사진 파일 경로")
    document_files = Column(JSON, comment="기타 문서 (JSON)")

    # 승인 상태
    approval_status = Column(String(20), default="DRAFT", comment="승인상태 (DRAFT/PENDING/APPROVED/REJECTED)")
    approved_by = Column(Integer, comment="승인자 ID")
    approved_at = Column(DateTime(timezone=True), comment="승인일시")

    # 상태
    status = Column(String(20), default="ACTIVE", comment="상태 (ACTIVE/INACTIVE/OBSOLETE)")
    is_active = Column(Boolean, default=True, comment="사용여부")
    is_stub = Column(Boolean, default=False, nullable=False, comment="자동 생성된 임시 부품 여부 (PI→생산요청 자동 등록)")

    # v0.79.0: 전속(독점) 공급 계약 — opt-in. 지정 시 해당 고객 외 견적/생산요청 경고·차단
    is_protected = Column(Boolean, default=False, nullable=False, server_default="false", comment="전속계약 여부 (특정 고객 전용)")
    protected_customer_id = Column(Integer, ForeignKey("business_partner.id"), nullable=True, comment="전속 고객 ID")
    protection_note = Column(Text, comment="전속계약 비고")

    # 감사
    created_by = Column(Integer, comment="생성자 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_by = Column(Integer, comment="수정자 ID")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")

    # 비고
    remark = Column(Text, comment="비고")

    # ========================================
    # Relationships (관계 설정)
    # ========================================

    # 전속 고객 (v0.79.0)
    protected_customer = relationship("BusinessPartner", foreign_keys=[protected_customer_id])

    # 신규 코드 테이블 관계 (v0.10.0)
    product_line = relationship("ProductLine")
    part_group = relationship("PartGroup")
    development_type = relationship("DevelopmentType")
    drawing_type = relationship("DrawingType")
    # 부품유형 (다중선택, M:N 관계)
    part_types = relationship("PartType", secondary=part_part_type, backref="parts")

    # Legacy 코드 테이블 관계 (하위 호환성)
    major_category = relationship("MajorCategory")
    middle_category = relationship("MiddleCategory")
    minor_category = relationship("MinorCategory")
    sub_category = relationship("SubCategory")
    item_code_rel = relationship("ItemCode")  # item_code 컬럼과 충돌 방지

    # 공통 관계
    material = relationship("Material")
    treatment = relationship("Treatment")
    level = relationship("Level")
    procurement_type = relationship("ProcurementType")
    unit = relationship("Unit")
    supplier = relationship("Supplier", foreign_keys=[supplier_id])

    # BOM 관계 (이 부품이 상위품인 경우 - 하위품 목록)
    bom_children = relationship("BOM", foreign_keys="BOM.parent_part_id", back_populates="parent_part", cascade="all, delete-orphan")
    # BOM 관계 (이 부품이 하위품인 경우 - 상위품 목록)
    bom_parents = relationship("BOM", foreign_keys="BOM.child_part_id", back_populates="child_part", cascade="all, delete-orphan")

    # 재고 관계 (v0.5.0)
    inventory = relationship("Inventory", back_populates="part", uselist=False, cascade="all, delete-orphan")

    # 첨부파일 (v0.96.0)
    attachments = relationship("PartAttachment", foreign_keys="PartAttachment.part_id", cascade="all, delete-orphan")


class PartAttachment(Base):
    """부품 첨부파일 (v0.96.0) — 도면/스펙시트/사진/기타 다중 첨부.

    도면은 '부품'의 속성(BOM 연결이 아님) — 같은 부품이 여러 BOM에 쓰여도 첨부는 공유.
    """
    __tablename__ = "part_attachment"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True, comment="부품 ID")
    kind = Column(String(20), nullable=False, default="OTHER", comment="종류: DRAWING(도면)/SPEC(스펙시트)/PHOTO(사진)/OTHER(기타)")
    filename = Column(String(300), nullable=False, comment="원본 파일명")
    filepath = Column(String(500), nullable=False, comment="저장 경로(상대)")
    mime_type = Column(String(120), nullable=True, comment="MIME")
    size = Column(Integer, nullable=True, comment="바이트")
    uploaded_by = Column(Integer, nullable=True, comment="업로더 user id")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="업로드 시각")

    part = relationship("Part", foreign_keys=[part_id])
