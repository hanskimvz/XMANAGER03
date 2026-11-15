"""
작업지시서 (Work Order) 모델
BOM 기반 생산 작업 지시 및 부품 출고를 관리합니다.

v0.6.0: 입출고 관리 기능 추가
- WorkOrder: 작업지시서 헤더
- WorkOrderItem: 작업지시서 항목 (BOM 전개)

v0.19.0: 다중 제품 지원
- WorkOrderProduct: 작업지시서별 제품 목록 (1:N)
- WorkOrderItem이 WorkOrderProduct를 참조
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class WorkOrder(Base):
    """
    작업지시서 (Work Order)
    완제품/반제품 생산을 위한 작업 지시 정보

    상태(status) - 7단계:
    - RECEIVED: 접수 (주문 접수 완료)
    - APPROVED: 승인 (작업 승인)
    - ISSUED: 부품출고 (구성부품 출고 완료)
    - IN_PROGRESS: 작업중 (생산 진행)
    - INSPECTION: 검사 (품질 검사)
    - PACKED: 포장완료
    - SHIPPED: 출하완료 (고객에게 인도)
    - CANCELLED: 취소

    v0.19.0: 다중 제품 지원
    - product_part_id, order_quantity 대신 products 관계 사용
    - 기존 단일 제품 필드는 호환성을 위해 유지 (nullable)
    """
    __tablename__ = "work_order"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 작업지시서 번호 (자동채번: WO-YYYYMMDD-001)
    wo_number = Column(String(20), unique=True, nullable=False, index=True, comment="작업지시서번호")

    # [DEPRECATED v0.19.0] 완제품 - 다중 제품 지원으로 products 관계 사용
    # 기존 데이터 호환성을 위해 유지 (nullable로 변경)
    product_part_id = Column(Integer, ForeignKey("parts.id"), nullable=True, index=True, comment="완제품 부품 ID (deprecated)")

    # 생산 요청서 연결 (v0.20.0) - nullable: 자체 생산 등은 요청서 없이 생성 가능
    production_request_id = Column(Integer, ForeignKey("production_request.id"), nullable=True, index=True, comment="생산 요청서 ID")

    # 작업 유형 (v0.20.0)
    # CUSTOMER_ORDER: 고객 주문 기반
    # STOCK_REPLENISH: 재고 확보용
    # SAMPLE: 샘플/시제품
    # INTERNAL: 내부 생산
    order_type = Column(String(20), default="CUSTOMER_ORDER", comment="작업 유형")

    # v0.24.0: 주문 세부 유형 (공정 분기용)
    # ASSEMBLED: 완제품 조립 (기본값)
    # KIT: 키트 주문 (조립 없이 부품 상태로 출하)
    order_subtype = Column(String(20), default="ASSEMBLED", comment="주문 세부유형 (ASSEMBLED/KIT)")

    # 고객사 정보 (선택)
    customer_id = Column(Integer, ForeignKey("business_partner.id"), comment="고객사 ID")
    customer_order_no = Column(String(50), comment="고객 주문번호")

    # [DEPRECATED v0.19.0] 수량 - 다중 제품 지원으로 products 관계 사용
    # 기존 데이터 호환성을 위해 유지
    order_quantity = Column(Numeric(15, 3), nullable=True, comment="지시 수량 (deprecated)")
    completed_quantity = Column(Numeric(15, 3), default=0, comment="완료 수량")
    defective_quantity = Column(Numeric(15, 3), default=0, comment="불량 수량")

    # 상태 (7단계)
    status = Column(String(20), default="RECEIVED", index=True, comment="상태")

    # 단계별 예정일/완료일

    # 1. 접수
    received_date = Column(DateTime(timezone=True), server_default=func.now(), comment="접수일시")

    # 2. 승인
    approved_date = Column(DateTime(timezone=True), comment="승인일시")
    approved_by = Column(Integer, comment="승인자 ID")

    # 3. 부품출고
    issue_scheduled_date = Column(Date, comment="부품출고 예정일")
    issue_completed_date = Column(DateTime(timezone=True), comment="부품출고 완료일시")

    # 4. 작업
    production_scheduled_date = Column(Date, comment="작업 예정일")
    production_start_date = Column(DateTime(timezone=True), comment="작업 시작일시")
    production_end_date = Column(DateTime(timezone=True), comment="작업 완료일시")

    # 5. 검사
    inspection_scheduled_date = Column(Date, comment="검사 예정일")
    inspection_completed_date = Column(DateTime(timezone=True), comment="검사 완료일시")

    # 6. 포장
    packing_scheduled_date = Column(Date, comment="포장 예정일")
    packing_completed_date = Column(DateTime(timezone=True), comment="포장 완료일시")

    # v0.24.0: 포장 상세 정보 (CI Package Details / 운송비 산정용)
    packaging_boxes = Column(Integer, comment="포장 박스 수")
    packaging_dimensions = Column(String(100), comment="박스 치수 (LxWxH cm)")
    packaging_gross_weight = Column(Numeric(10, 2), comment="총중량 (kg)")
    packaging_net_weight = Column(Numeric(10, 2), comment="순중량 (kg)")

    # 7. 출하
    shipping_scheduled_date = Column(Date, comment="출하 예정일")
    shipping_completed_date = Column(DateTime(timezone=True), comment="출하 완료일시")

    # 우선순위: 0(보통), 1(높음), 2(긴급)
    priority = Column(Integer, default=0, comment="우선순위")

    # 비고
    remarks = Column(Text, comment="비고")

    # 파일 첨부 (JSON 배열)
    document_files = Column(JSON, default=list, comment="첨부파일")

    # 원본 요청서 수정 알림 플래그 (v0.21.0)
    source_request_modified = Column(Boolean, default=False, comment="원본 요청서 수정됨")

    # v0.31.0: 작업지시 체인 (선행/후속 관계)
    parent_wo_id = Column(Integer, ForeignKey("work_order.id"), nullable=True, index=True, comment="상위 WO ID (이 WO의 산출물이 투입되는 WO)")
    target_part_id = Column(Integer, ForeignKey("parts.id"), nullable=True, comment="이 WO에서 만들려는 부품 ID (완제품이 아닌 경우)")

    # 감사 필드
    created_by = Column(Integer, comment="생성자 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_by = Column(Integer, comment="수정자 ID")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

    # Relationships
    production_request = relationship("ProductionRequest", back_populates="work_orders")  # v0.20.0
    product_part = relationship("Part", foreign_keys=[product_part_id])  # [DEPRECATED] 호환성용
    target_part = relationship("Part", foreign_keys=[target_part_id])  # v0.31.0
    customer = relationship("BusinessPartner", foreign_keys=[customer_id])
    items = relationship("WorkOrderItem", back_populates="work_order", cascade="all, delete-orphan")
    products = relationship("WorkOrderProduct", back_populates="work_order", cascade="all, delete-orphan")  # v0.19.0
    tasks = relationship("WorkOrderTask", back_populates="work_order", cascade="all, delete-orphan",
                         order_by="WorkOrderTask.sort_order")  # v0.29.0
    # v0.31.0: 작업지시 체인
    parent_wo = relationship("WorkOrder", remote_side="WorkOrder.id", foreign_keys=[parent_wo_id], back_populates="child_work_orders")
    child_work_orders = relationship("WorkOrder", foreign_keys="WorkOrder.parent_wo_id", back_populates="parent_wo")

    def __repr__(self):
        return f"<WorkOrder(id={self.id}, wo_number={self.wo_number}, status={self.status})>"


class WorkOrderProduct(Base):
    """
    작업지시서 제품 (v0.19.0)
    하나의 작업지시서에 여러 제품(완제품/반제품)을 지정할 수 있습니다.

    각 제품별로:
    - 지시 수량, 완료 수량, 불량 수량 관리
    - BOM 전개 시 해당 제품의 하위 부품이 WorkOrderItem으로 생성
    """
    __tablename__ = "work_order_product"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 작업지시서 참조
    work_order_id = Column(Integer, ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="작업지시서 ID")

    # 제품 (완제품/반제품)
    product_part_id = Column(Integer, ForeignKey("parts.id"), nullable=False, index=True, comment="제품 부품 ID")

    # 수량
    order_quantity = Column(Numeric(15, 3), nullable=False, comment="지시 수량")
    completed_quantity = Column(Numeric(15, 3), default=0, comment="완료 수량")
    defective_quantity = Column(Numeric(15, 3), default=0, comment="불량 수량")

    # 정렬 순서
    sort_order = Column(Integer, default=0, comment="정렬순서")

    # 비고
    line_remarks = Column(Text, comment="항목 비고")

    # Relationships
    work_order = relationship("WorkOrder", back_populates="products")
    product_part = relationship("Part")
    items = relationship("WorkOrderItem", back_populates="work_order_product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkOrderProduct(id={self.id}, product_part_id={self.product_part_id}, qty={self.order_quantity})>"


class WorkOrderItem(Base):
    """
    작업지시서 항목 (Work Order Item)
    BOM 전개를 통해 자동 생성된 구성 부품 목록

    v0.19.0: work_order_product_id 추가 - 어느 제품의 BOM에서 전개되었는지 추적
    """
    __tablename__ = "work_order_item"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 작업지시서 참조
    work_order_id = Column(Integer, ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False, index=True, comment="작업지시서 ID")

    # 작업지시서 제품 참조 (v0.19.0)
    work_order_product_id = Column(Integer, ForeignKey("work_order_product.id", ondelete="CASCADE"), nullable=True, index=True, comment="작업지시서 제품 ID")

    # 부품 참조
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False, index=True, comment="부품 ID")

    # BOM 참조 (선택 - BOM 전개 시 연결)
    bom_id = Column(Integer, ForeignKey("bom.id"), comment="BOM ID")

    # 수량
    required_quantity = Column(Numeric(15, 3), nullable=False, comment="필요 수량")
    issued_quantity = Column(Numeric(15, 3), default=0, comment="출고 수량")
    additional_quantity = Column(Numeric(15, 3), default=0, comment="추가 출고 (불량 대응)")
    returned_quantity = Column(Numeric(15, 3), default=0, comment="반납 수량")

    # 단위
    unit_id = Column(Integer, ForeignKey("unit.id"), comment="단위 ID")

    # BOM 레벨 (1: 직접 하위, 2: 2단계 하위, ...)
    bom_level = Column(Integer, default=1, comment="BOM 레벨")

    # 비고
    line_remarks = Column(Text, comment="항목 비고")

    # 정렬 순서
    sort_order = Column(Integer, default=0, comment="정렬순서")

    # Relationships
    work_order = relationship("WorkOrder", back_populates="items")
    work_order_product = relationship("WorkOrderProduct", back_populates="items")  # v0.19.0
    part = relationship("Part")
    bom = relationship("BOM")
    unit = relationship("Unit")
    issue_records = relationship("WorkOrderItemIssue", back_populates="work_order_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkOrderItem(id={self.id}, part_id={self.part_id}, required={self.required_quantity})>"
