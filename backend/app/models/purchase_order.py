"""
발주서 (Purchase Order) 모델
공급업체로부터 부품을 발주하고 입고 처리를 관리합니다.

v0.6.0: 입출고 관리 기능 추가
- PurchaseOrder: 발주서 헤더
- PurchaseOrderItem: 발주서 항목
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PurchaseOrder(Base):
    """
    발주서 (Purchase Order)
    공급업체에 대한 부품 발주 정보

    상태(status):
    - DRAFT: 작성중
    - ORDERED: 주문완료 (발주 확정)
    - CONFIRMED: 납기확정 (공급업체 확인)
    - RECEIVED: 입고완료 (물품 수령)
    - COMPLETED: 결재완료 (프로세스 종료)
    - CANCELLED: 취소
    """
    __tablename__ = "purchase_order"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 발주서 번호 (자동채번: PO-YYYYMMDD-001)
    po_number = Column(String(20), unique=True, nullable=False, index=True, comment="발주서번호")

    # 공급업체 정보
    supplier_id = Column(Integer, ForeignKey("business_partner.id"), nullable=False, index=True, comment="공급업체 ID")

    # 날짜 정보
    order_date = Column(Date, nullable=False, comment="발주일")
    expected_delivery_date = Column(Date, comment="예상 납기일")
    actual_delivery_date = Column(Date, comment="실제 입고일")

    # 금액 정보
    total_amount = Column(Numeric(15, 2), default=0, comment="총 금액")
    currency = Column(String(10), default="KRW", comment="통화")
    tax_amount = Column(Numeric(15, 2), default=0, comment="세금")
    discount_amount = Column(Numeric(15, 2), default=0, comment="할인금액")

    # v0.73.0 이 발주건으로 생성한 구매기안서(전자결재) id — 역방향 링크·중복생성 방지
    linked_approval_id = Column(Integer, nullable=True, comment="발주→구매기안 역방향 생성 링크")
    # v0.98.0 기안서에서 파생된 발주서(구매기안 승인 자동생성) — 항목(수량/단가/부품) 수정 잠금 기준
    source_approval_id = Column(Integer, nullable=True, index=True, comment="이 발주서를 생성한 구매기안서 ID(파생 발주)")
    # v0.98.0 발주서 발송(공급업체에 발송 완료) 여부·시각
    sent_at = Column(DateTime(timezone=True), nullable=True, comment="발주서 발송 완료 시각")
    sent_by = Column(Integer, nullable=True, comment="발송 처리자 user id")
    # v0.99.0 대금 지급 = 지출결의(집행)로 연동. 연결된 지출결의서 id(대기/완료 판별)
    disbursement_id = Column(Integer, nullable=True, index=True, comment="연결된 지출결의서(approval) id")

    # 상태
    status = Column(String(20), default="DRAFT", index=True, comment="상태")

    # 결제 여부 (상태와 별도 관리)
    is_paid = Column(Boolean, default=False, comment="결제 완료 여부")
    paid_date = Column(Date, comment="결제일")
    paid_amount = Column(Numeric(15, 2), comment="결제 금액")

    # 조건
    payment_terms = Column(String(200), comment="결제 조건")
    delivery_terms = Column(String(200), comment="납품 조건")
    remarks = Column(Text, comment="비고")

    # 파일 첨부 (JSON 배열)
    document_files = Column(JSON, default=list, comment="첨부파일")

    # 감사 필드
    created_by = Column(Integer, comment="생성자 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_by = Column(Integer, comment="수정자 ID")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

    # Relationships
    supplier = relationship("BusinessPartner", foreign_keys=[supplier_id])
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PurchaseOrder(id={self.id}, po_number={self.po_number}, status={self.status})>"


class PurchaseOrderItem(Base):
    """
    발주서 항목 (Purchase Order Item)
    발주서에 포함된 개별 부품 정보
    """
    __tablename__ = "purchase_order_item"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 발주서 참조
    purchase_order_id = Column(Integer, ForeignKey("purchase_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="발주서 ID")

    # 부품 참조 — v0.91.0 BOM 미등록(자유입력) 품목 지원: part_id 없으면 custom_product_* 사용
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True, index=True, comment="부품 ID (BOM 등록 품목)")
    custom_product_code = Column(String(100), nullable=True, comment="BOM 미등록 품목 품번(자유입력)")
    custom_product_name = Column(String(200), nullable=True, comment="BOM 미등록 품목 품명(자유입력)")

    # 수량
    ordered_quantity = Column(Numeric(15, 3), nullable=False, comment="발주 수량")
    received_quantity = Column(Numeric(15, 3), default=0, comment="입고 수량")
    defective_quantity = Column(Numeric(15, 3), default=0, comment="불량 수량")

    # 금액
    unit_price = Column(Numeric(15, 2), nullable=False, comment="단가")
    line_total = Column(Numeric(15, 2), comment="항목 금액")

    # 단위
    unit_id = Column(Integer, ForeignKey("unit.id"), comment="단위 ID")

    # 비고
    line_remarks = Column(Text, comment="항목 비고")

    # 정렬 순서
    sort_order = Column(Integer, default=0, comment="정렬순서")

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    part = relationship("Part")
    unit = relationship("Unit")

    def __repr__(self):
        return f"<PurchaseOrderItem(id={self.id}, part_id={self.part_id}, qty={self.ordered_quantity})>"
