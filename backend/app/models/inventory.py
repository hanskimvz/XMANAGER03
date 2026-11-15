"""
재고(Inventory) 모델
재고 현황 및 거래 이력을 관리합니다.

v0.5.0: 재고관리 기능 추가
- Inventory: 부품별 재고 현황
- InventoryTransaction: 재고 거래 기록 (입고/출고/조정)
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Inventory(Base):
    """
    재고 현황 (Inventory)
    부품별 현재 재고 수량 및 관리 정보

    상태(status):
    - NORMAL: 정상 (재고 >= 재주문점)
    - LOW: 부족 (0 < 재고 < 재주문점)
    - OUT_OF_STOCK: 재고없음 (재고 = 0)
    - EXCESS: 과잉 (추후 확장용)
    """
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 부품 참조 (필수)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True, comment="부품 ID")

    # 기본 수량
    quantity_on_hand = Column(Numeric(15, 3), nullable=False, default=0, comment="현재고")

    # 확장 수량 (추후 사용)
    quantity_reserved = Column(Numeric(15, 3), default=0, comment="예약수량")
    quantity_available = Column(Numeric(15, 3), default=0, comment="가용수량")

    # 재주문 관리
    reorder_point = Column(Numeric(15, 3), comment="재주문점")
    reorder_qty = Column(Numeric(15, 3), comment="재주문량")

    # 보관위치 (확장용)
    warehouse_location_id = Column(Integer, ForeignKey("warehouse_location.id"), comment="보관위치 ID")

    # 단가 정보
    unit_cost = Column(Numeric(15, 2), comment="단가")

    # 상태
    status = Column(String(20), default="OUT_OF_STOCK", comment="상태 (NORMAL/LOW/EXCESS/OUT_OF_STOCK)")
    last_count_date = Column(DateTime(timezone=True), comment="마지막 실사일")

    # FIFO 설정
    fifo_enabled = Column(Boolean, default=True, comment="선입선출 적용 여부")

    # 비고
    remarks = Column(Text, comment="비고")

    # 활성화 상태
    is_active = Column(Boolean, default=True, comment="사용여부")

    # 감사
    created_by = Column(Integer, comment="생성자 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_by = Column(Integer, comment="수정자 ID")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

    # Relationships
    part = relationship("Part", back_populates="inventory")
    warehouse_location = relationship("WarehouseLocation")
    transactions = relationship("InventoryTransaction", back_populates="inventory", cascade="all, delete-orphan")
    lots = relationship("InventoryLot", primaryjoin="Inventory.part_id==InventoryLot.part_id", foreign_keys="InventoryLot.part_id", viewonly=True)


class InventoryTransaction(Base):
    """
    재고 거래 기록 (Inventory Transaction)
    모든 재고 변동 이력을 기록합니다.

    거래유형(transaction_type):
    - IN: 입고
    - OUT: 출고
    - ADJUST: 조정 (수량 직접 설정)
    - RETURN: 반품
    - COUNT: 실사
    """
    __tablename__ = "inventory_transaction"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 재고 및 부품 참조
    inventory_id = Column(Integer, ForeignKey("inventory.id", ondelete="SET NULL"), comment="재고 ID")
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True, comment="부품 ID")

    # 거래 정보
    transaction_type = Column(String(20), nullable=False, index=True, comment="거래유형 (IN/OUT/ADJUST/RETURN/COUNT)")
    quantity = Column(Numeric(15, 3), nullable=False, comment="변동수량")
    quantity_before = Column(Numeric(15, 3), comment="변동전 수량")
    quantity_after = Column(Numeric(15, 3), comment="변동후 수량")

    # 참조 정보
    reference_type = Column(String(50), comment="참조유형 (PO/MO/SO/MANUAL)")
    reference_id = Column(String(50), comment="참조문서번호")

    # 로트 추적 (v0.7.0 추가)
    lot_id = Column(Integer, ForeignKey("inventory_lot.id", ondelete="SET NULL"), comment="로트 ID")
    lot_number = Column(String(50), comment="로트번호")

    # 상세 정보
    reason = Column(Text, comment="사유")
    remarks = Column(Text, comment="비고")

    # 파일 첨부 (JSON 배열) - v0.6.0 추가
    document_files = Column(JSON, default=list, comment="첨부파일")

    # 감사
    transaction_date = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="거래일시")
    created_by = Column(Integer, comment="생성자 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

    # Relationships
    inventory = relationship("Inventory", back_populates="transactions")
    part = relationship("Part")
    lot = relationship("InventoryLot")
