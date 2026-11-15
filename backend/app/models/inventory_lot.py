"""
재고 로트 (Inventory Lot) 모델
입고분별 재고 추적 및 FIFO 출고를 지원합니다.

v0.7.0: 로트 추적 기능 추가
- InventoryLot: 입고분별 재고 관리
- WorkOrderItemIssue: 작업지시서 항목별 로트 출고 기록
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, ForeignKey, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class InventoryLot(Base):
    """
    재고 로트 (Inventory Lot)
    입고분별 재고를 추적하여 FIFO(선입선출) 출고를 지원합니다.

    상태(status):
    - ACTIVE: 활성 (잔량 있음)
    - DEPLETED: 소진 (잔량 0)
    - EXPIRED: 만료 (유효기간 경과)
    """
    __tablename__ = "inventory_lot"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 부품 참조 (필수)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True, comment="부품 ID")

    # 로트 식별
    lot_number = Column(String(50), nullable=False, comment="로트/배치 번호")

    # 수량
    quantity_received = Column(Numeric(15, 3), nullable=False, comment="입고 수량")
    quantity_on_hand = Column(Numeric(15, 3), nullable=False, default=0, comment="현재 잔량")
    quantity_issued = Column(Numeric(15, 3), default=0, comment="출고된 수량")

    # 입고 정보
    received_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="입고일시")
    purchase_order_id = Column(Integer, ForeignKey("purchase_order.id", ondelete="SET NULL"), comment="발주서 ID")
    supplier_id = Column(Integer, ForeignKey("business_partner.id", ondelete="SET NULL"), comment="공급업체 ID")

    # 보관 위치 (확장용)
    warehouse_location_id = Column(Integer, ForeignKey("warehouse_location.id", ondelete="SET NULL"), comment="보관위치 ID")

    # 추가 정보
    expiry_date = Column(Date, comment="유효기간")
    supplier_lot_number = Column(String(50), comment="공급업체 로트번호")
    unit_cost = Column(Numeric(15, 2), comment="입고 단가")

    # 상태
    status = Column(String(20), default="ACTIVE", index=True, comment="상태 (ACTIVE/DEPLETED/EXPIRED)")

    # 비고
    remarks = Column(Text, comment="비고")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

    # Unique 제약
    __table_args__ = (
        UniqueConstraint('part_id', 'lot_number', name='uq_inventory_lot_part_lot'),
        Index('ix_inventory_lot_part_date', 'part_id', 'received_date'),
        Index('ix_inventory_lot_status', 'part_id', 'status'),
    )

    # Relationships
    part = relationship("Part")
    purchase_order = relationship("PurchaseOrder")
    supplier = relationship("BusinessPartner")
    warehouse_location = relationship("WarehouseLocation")
    issue_records = relationship("WorkOrderItemIssue", back_populates="lot")

    def __repr__(self):
        return f"<InventoryLot(id={self.id}, lot_number={self.lot_number}, on_hand={self.quantity_on_hand})>"


class WorkOrderItemIssue(Base):
    """
    작업지시서 항목 출고 기록 (Work Order Item Issue)
    작업지시서 항목별로 어느 로트에서 얼마나 출고했는지 기록합니다.
    """
    __tablename__ = "work_order_item_issue"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 작업지시서 항목 참조
    work_order_item_id = Column(Integer, ForeignKey("work_order_item.id", ondelete="CASCADE"), nullable=False, index=True, comment="작업지시서 항목 ID")

    # 로트 참조
    lot_id = Column(Integer, ForeignKey("inventory_lot.id", ondelete="SET NULL"), comment="로트 ID")
    lot_number = Column(String(50), comment="로트번호 (참조용)")

    # 출고 수량
    quantity = Column(Numeric(15, 3), nullable=False, comment="출고 수량")
    issue_date = Column(DateTime(timezone=True), server_default=func.now(), comment="출고일시")

    # 반납 정보
    returned_quantity = Column(Numeric(15, 3), default=0, comment="반납 수량")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

    # Relationships
    work_order_item = relationship("WorkOrderItem", back_populates="issue_records")
    lot = relationship("InventoryLot", back_populates="issue_records")

    def __repr__(self):
        return f"<WorkOrderItemIssue(id={self.id}, item_id={self.work_order_item_id}, qty={self.quantity})>"
