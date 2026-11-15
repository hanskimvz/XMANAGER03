"""
영업 문서 (Sales Document) 모델
Quotation(Q), Proforma Invoice(PI), Commercial Invoice(CI) 통합 관리

v0.24.0: 초기 구현

문서 흐름: Q(견적) → PI(수주확인) → CI(출하)
번호 체계: Q-xx날짜, PI-xx날짜, CI-xx날짜 (xx = 업체 short_code)
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SalesDocumentLink(Base):
    """
    영업 문서 N:M 연결 (v0.32.0)
    Q↔PI, PI↔CI 간 다대다 관계를 지원합니다.
    """
    __tablename__ = "sales_document_link"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sales_document.id", ondelete="CASCADE"), nullable=False, index=True, comment="소스 문서 ID (Q/PI)")
    target_id = Column(Integer, ForeignKey("sales_document.id", ondelete="CASCADE"), nullable=False, index=True, comment="대상 문서 ID (PI/CI)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source = relationship("SalesDocument", foreign_keys=[source_id], backref="forward_links")
    target = relationship("SalesDocument", foreign_keys=[target_id], backref="source_links")


class SalesDocument(Base):
    """
    영업 문서 (Quotation / PI / CI)

    document_type:
    - QUOTATION: 견적서
    - PI: Proforma Invoice
    - CI: Commercial Invoice

    status:
    - DRAFT: 작성중
    - SENT: 발송완료
    - CONFIRMED: 확정 (고객 PO 수령)
    - CANCELLED: 취소
    """
    __tablename__ = "sales_document"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 문서 유형 및 번호
    document_type = Column(String(20), nullable=False, index=True, comment="문서 유형 (QUOTATION/PI/CI)")
    document_number = Column(String(50), unique=True, nullable=False, index=True, comment="문서 번호 (Q-BI260306)")
    document_date = Column(Date, nullable=False, comment="문서 날짜")

    # 버전 관리 (v0.32.0)
    version = Column(Integer, nullable=False, default=1, server_default="1", comment="버전 번호")
    is_latest = Column(Boolean, nullable=False, default=True, server_default="true", index=True, comment="최신 버전 여부")
    version_group = Column(String(50), nullable=True, index=True, comment="버전 그룹 (최초 문서번호)")

    # MOQ 견적 여부 (v0.32.0)
    is_moq = Column(Boolean, nullable=False, default=False, server_default="false", comment="MOQ 가격표 견적 여부")
    # 견적 대용 PI (v0.53.0): PI를 견적서 대용으로 발행한 경우 — 매출/미수 집계에서 제외(허수 방지)
    is_quote_only = Column(Boolean, nullable=False, default=False, server_default="false", comment="견적 대용 PI(매출/미수 집계 제외)")

    # 이전 문서 참조 (Q→PI→CI 체인)
    source_document_id = Column(Integer, ForeignKey("sales_document.id"), nullable=True, comment="원본 문서 ID (Q→PI→CI)")

    # 영업활동 참조 (v0.31.0)
    sales_activity_id = Column(Integer, ForeignKey("sales_activity.id"), nullable=True, index=True, comment="연결된 영업활동 ID")

    # 고객사 정보
    customer_id = Column(Integer, ForeignKey("business_partner.id"), nullable=False, index=True, comment="고객사 ID")
    # 고객사 담당자(선택, v0.52.0): 문서별로 담당자 지정. NULL이면 거래처 기본 담당자(manager_name) 폴백.
    customer_contact_id = Column(Integer, ForeignKey("business_partner_contact.id", ondelete="SET NULL"),
                                 nullable=True, index=True, comment="고객사 담당자 ID(business_partner_contact)")

    # 작성자 정보
    prepared_by = Column(String(100), comment="작성자명")
    prepared_email = Column(String(200), comment="작성자 이메일")

    # v0.92.0 거래처 VAT/TAX ID(사업자등록번호) 문서 표기 여부 — 해외 업체가 자사 VAT 기재 요청 시 사용
    show_customer_tax_id = Column(Boolean, default=False, nullable=False, server_default="false",
                                  comment="거래처 사업자등록번호(VAT/TAX ID)를 문서에 표기")

    # v0.95.0 원산지 신고문(Statement of Origin) CI 표기 여부 — 고객사에 따라 선택
    show_statement_of_origin = Column(Boolean, default=False, nullable=False, server_default="false",
                                      comment="CI에 원산지 신고문(Statement of Origin) 블록 표기")

    # 고객 PO 정보 (PI/CI에서 사용)
    customer_po_number = Column(String(100), comment="고객 PO 번호")
    customer_po_date = Column(Date, comment="고객 PO 날짜")
    po_attachment_files = Column(JSONB, nullable=True, comment="PO 첨부파일 목록 [{filename, filepath, size}]")
    shipping_invoice_files = Column(JSONB, nullable=True, comment="운송장 첨부파일 목록 [{filename, filepath, size, mime_type, uploaded_at}]")
    # v0.81.0 파일 허브: Nextcloud 주문 폴더(최초 생성 시 저장, 이후 불변 — PI번호 변경에도 링크 유지)
    nextcloud_folder = Column(String(500), nullable=True, comment="Nextcloud 주문 폴더 상대경로")

    # Terms & Conditions (거래처에서 자동 로드, 문서별 수정 가능)
    payment_terms = Column(String(500), comment="결제 조건")
    delivery_terms = Column(String(200), comment="납품 조건 (EXW Seoul 등)")
    # v0.89.0 인코텀즈(드롭다운) + 박스당 운임(분할선적). CPT 등 운임부담 조건에서 freight 입력
    incoterms = Column(String(10), nullable=True, comment="인코텀즈 (EXW/FCA/CPT/CIP/CFR/CIF/DAP/DDP)")
    freight_per_box = Column(Numeric(15, 2), nullable=True, comment="박스당 운임(분할선적) — 박스 CI마다 배송비로 가산")
    hs_code = Column(String(100), comment="HS Code (복수 가능, 쉼표 구분 — 예: 커넥터+조립체)")
    country_of_origin = Column(String(100), default="Republic of Korea", comment="원산지")
    valid_until = Column(String(200), comment="견적 유효기간")

    # Bank Details (거래처에서 자동 로드)
    bank_name = Column(String(200), comment="은행명")
    bank_address = Column(String(500), comment="은행 주소")
    swift_code = Column(String(20), comment="SWIFT 코드")
    account_name = Column(String(200), comment="예금주")
    account_number = Column(String(50), comment="계좌번호")

    # SHIP TO / CONSIGNEE (제품 수령자 — Buyer와 다를 수 있음. 미입력 시 Same as Buyer)
    # v0.58.0: 거래처에 저장된 배송지 선택(FK). NULL이면 직접입력(ship_to_*) 또는 Same as Buyer.
    ship_to_address_id = Column(Integer, ForeignKey("business_partner_shipping_address.id", ondelete="SET NULL"),
                                nullable=True, index=True, comment="선택된 거래처 배송지 ID")
    ship_to_name = Column(String(200), comment="수취인(회사/이름)")
    ship_to_address = Column(Text, comment="배송 주소")
    ship_to_contact = Column(String(200), comment="수취 담당자명")
    ship_to_phone = Column(String(50), comment="수취 담당자 전화")
    ship_to_email = Column(String(200), comment="수취 담당자 이메일")

    # CI 전용 필드
    ship_from = Column(String(200), comment="선적지 (Seoul, Korea)")
    destination = Column(String(200), comment="도착지")
    transportation = Column(String(100), comment="운송 방법 (By Air 등)")
    shipment_date = Column(Date, comment="선적일")

    # CI Package Details (요약값 — packing_list가 있으면 그로부터 산출)
    packaging_boxes = Column(Integer, comment="포장 박스 수")
    packaging_dimensions = Column(String(100), comment="박스 치수 (LxWxH cm)")
    packaging_gross_weight = Column(Numeric(10, 2), comment="총중량 (kg)")
    packaging_net_weight = Column(Numeric(10, 2), comment="순중량 (kg)")
    # v0.77.0 박스별 packing list (생산 출고 명세 승계) [{box_type, quantity, gross_weight, net_weight, length, width, height, remarks}]
    packing_list = Column(JSONB, comment="박스별 packing list (JSON)")

    # 합계
    total_amount = Column(Numeric(15, 2), default=0, comment="총 금액")
    currency = Column(String(10), default="USD", comment="통화")

    # v0.71.0 할인/배송비 (체크 시 입력 → 총액에 반영). NULL = 미적용
    discount_amount = Column(Numeric(15, 2), nullable=True, comment="할인 금액 (있으면 총액에서 차감)")
    discount_reason = Column(String(300), nullable=True, comment="할인 사유 (견적서 기록용)")
    shipping_fee = Column(Numeric(15, 2), nullable=True, comment="배송비 (있으면 총액에 가산)")

    # 상태
    status = Column(String(20), default="DRAFT", index=True, comment="상태 (DRAFT/SENT/CONFIRMED/CANCELLED)")

    # v0.24.0 Phase 3: 수금 관리 (PI 문서에서 주로 사용)
    # payment_status: UNPAID(미입금) / PARTIAL(부분입금) / PAID(완납)
    payment_status = Column(String(20), default="UNPAID", comment="입금 상태")
    payment_condition = Column(String(200), comment="결제 조건 상세 (100% 선입금, 30% 선입금 70% 선적전 등)")
    paid_amount = Column(Numeric(15, 2), default=0, comment="입금 확인 금액")
    paid_date = Column(Date, comment="입금 확인일")
    payment_remarks = Column(Text, comment="입금 메모")

    # 관리번호 (26-001 형태, 연도-순번)
    management_no = Column(String(20), index=True, comment="관리번호 (연도-순번)")

    # 비고
    remarks = Column(Text, comment="비고")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

    # Relationships
    customer = relationship("BusinessPartner", foreign_keys=[customer_id])
    customer_contact = relationship("BusinessPartnerContact", foreign_keys=[customer_contact_id])
    shipping_address = relationship("BusinessPartnerShippingAddress", foreign_keys=[ship_to_address_id])
    source_document = relationship("SalesDocument", remote_side=[id], foreign_keys=[source_document_id])
    items = relationship("SalesDocumentItem", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SalesDocument(type={self.document_type}, number={self.document_number}, status={self.status})>"


class SalesDocumentItem(Base):
    """
    영업 문서 품목
    Q/PI/CI에 포함되는 제품 라인 아이템
    """
    __tablename__ = "sales_document_item"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 문서 참조
    document_id = Column(Integer, ForeignKey("sales_document.id", ondelete="CASCADE"), nullable=False, index=True, comment="문서 ID")

    # 라인 번호
    line_no = Column(Integer, nullable=False, comment="라인 번호")

    # 제품 정보
    product_code = Column(String(100), nullable=False, comment="오더코드 (HXB13-PSD-B-O4-S1-D55)")
    description = Column(Text, comment="제품 설명 (자동 조합 또는 수동 입력)")

    # 수량/가격
    quantity = Column(Numeric(15, 3), nullable=False, comment="수량 (실제 계산용; TBD면 0 저장)")
    quantity_text = Column(String(40), nullable=True, comment="수량 표시 오버라이드 (예: 'TBD'). 비어있으면 quantity 값을 포맷팅하여 표시")
    uom = Column(String(10), default="pc", comment="단위 (pc, set 등)")
    unit_price = Column(Numeric(15, 2), nullable=False, comment="단가 (실제 계산용; TBD면 0 저장)")
    unit_price_text = Column(String(40), nullable=True, comment="단가 표시 오버라이드 (예: 'TBD')")
    amount = Column(Numeric(15, 2), nullable=False, comment="금액 (수량 × 단가; TBD면 0)")
    amount_text = Column(String(40), nullable=True, comment="금액 표시 오버라이드 (예: 'TBD')")
    currency = Column(String(10), default="USD", comment="통화")

    # 비고
    line_remarks = Column(Text, comment="항목 비고")

    # 정렬
    sort_order = Column(Integer, default=0, comment="정렬순서")

    # Relationships
    document = relationship("SalesDocument", back_populates="items")

    def __repr__(self):
        return f"<SalesDocumentItem(line={self.line_no}, code={self.product_code}, qty={self.quantity})>"
