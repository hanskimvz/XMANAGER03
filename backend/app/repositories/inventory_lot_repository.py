"""
재고 로트 리포지토리 (v0.7.0)
로트 CRUD 및 FIFO 조회 로직
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session, joinedload

from app.models.inventory_lot import InventoryLot, WorkOrderItemIssue
from app.models.inventory import Inventory, InventoryTransaction
from app.schemas.inventory_lot import (
    InventoryLotCreate,
    InventoryLotUpdate,
    FIFOLotSuggestion,
)


class InventoryLotRepository:
    """재고 로트 리포지토리"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== CRUD ====================

    def create(self, data: InventoryLotCreate) -> InventoryLot:
        """로트 생성"""
        lot = InventoryLot(
            part_id=data.part_id,
            lot_number=data.lot_number,
            quantity_received=data.quantity_received,
            quantity_on_hand=data.quantity_received,  # 초기에는 입고량 = 잔량
            quantity_issued=Decimal(0),
            received_date=data.received_date or datetime.now(),
            purchase_order_id=data.purchase_order_id,
            supplier_id=data.supplier_id,
            warehouse_location_id=data.warehouse_location_id,
            expiry_date=data.expiry_date,
            supplier_lot_number=data.supplier_lot_number,
            unit_cost=data.unit_cost,
            remarks=data.remarks,
            status="ACTIVE"
        )
        self.db.add(lot)
        self.db.flush()
        return lot

    def get_by_id(self, lot_id: int) -> Optional[InventoryLot]:
        """ID로 로트 조회"""
        return self.db.query(InventoryLot).options(
            joinedload(InventoryLot.part),
            joinedload(InventoryLot.supplier),
            joinedload(InventoryLot.purchase_order)
        ).filter(InventoryLot.id == lot_id).first()

    def get_by_part_id(self, part_id: int, include_depleted: bool = False) -> List[InventoryLot]:
        """부품별 로트 목록 조회 (공급업체 정보 포함)"""
        query = self.db.query(InventoryLot).options(
            joinedload(InventoryLot.supplier)
        ).filter(
            InventoryLot.part_id == part_id
        )

        if not include_depleted:
            query = query.filter(InventoryLot.status == "ACTIVE")

        return query.order_by(InventoryLot.received_date.asc()).all()

    def get_by_lot_number(self, part_id: int, lot_number: str) -> Optional[InventoryLot]:
        """부품 + 로트번호로 조회"""
        return self.db.query(InventoryLot).filter(
            and_(
                InventoryLot.part_id == part_id,
                InventoryLot.lot_number == lot_number
            )
        ).first()

    def update(self, lot_id: int, data: InventoryLotUpdate) -> Optional[InventoryLot]:
        """로트 수정"""
        lot = self.get_by_id(lot_id)
        if not lot:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lot, field, value)

        lot.updated_at = datetime.now()
        self.db.flush()
        return lot

    def delete(self, lot_id: int) -> bool:
        """로트 삭제 (소진된 로트만 가능)"""
        lot = self.get_by_id(lot_id)
        if not lot or lot.quantity_on_hand > 0:
            return False

        self.db.delete(lot)
        self.db.flush()
        return True

    # ==================== FIFO 로직 ====================

    def get_fifo_lots(
        self,
        part_id: int,
        quantity: Decimal
    ) -> Tuple[List[FIFOLotSuggestion], bool]:
        """
        FIFO 순서로 출고할 로트 목록 계산

        Args:
            part_id: 부품 ID
            quantity: 필요 수량

        Returns:
            (로트 목록, 충분 여부)
        """
        # 활성 로트를 입고일 순으로 조회 (FIFO), 공급업체 정보 포함
        lots = self.db.query(InventoryLot).options(
            joinedload(InventoryLot.supplier)
        ).filter(
            and_(
                InventoryLot.part_id == part_id,
                InventoryLot.quantity_on_hand > 0,
                InventoryLot.status == "ACTIVE"
            )
        ).order_by(InventoryLot.received_date.asc()).all()

        result = []
        remaining = quantity

        for lot in lots:
            if remaining <= 0:
                break

            issue_qty = min(lot.quantity_on_hand, remaining)
            supplier_name = lot.supplier.partner_name if lot.supplier else None
            result.append(FIFOLotSuggestion(
                lot_id=lot.id,
                lot_number=lot.lot_number,
                received_date=lot.received_date,
                available_quantity=lot.quantity_on_hand,
                suggested_quantity=issue_qty,
                expiry_date=lot.expiry_date,
                unit_cost=lot.unit_cost,
                supplier_name=supplier_name
            ))
            remaining -= issue_qty

        is_sufficient = remaining <= 0
        return result, is_sufficient

    def get_available_quantity(self, part_id: int) -> Decimal:
        """부품별 전체 가용 수량 조회"""
        result = self.db.query(InventoryLot).filter(
            and_(
                InventoryLot.part_id == part_id,
                InventoryLot.status == "ACTIVE"
            )
        ).with_entities(
            func.sum(InventoryLot.quantity_on_hand)
        ).scalar()

        return Decimal(result) if result else Decimal(0)

    # ==================== 출고 처리 ====================

    def issue_from_lot(
        self,
        lot_id: int,
        quantity: Decimal,
        work_order_item_id: int
    ) -> Tuple[Optional[WorkOrderItemIssue], str]:
        """
        로트에서 출고 처리

        Args:
            lot_id: 로트 ID
            quantity: 출고 수량
            work_order_item_id: 작업지시서 항목 ID

        Returns:
            (출고 기록, 에러 메시지)
        """
        lot = self.get_by_id(lot_id)
        if not lot:
            return None, "로트를 찾을 수 없습니다."

        if lot.quantity_on_hand < quantity:
            return None, f"로트 잔량({lot.quantity_on_hand})이 출고 수량({quantity})보다 적습니다."

        # 로트 수량 차감
        lot.quantity_on_hand -= quantity
        lot.quantity_issued += quantity

        # 소진 시 상태 변경
        if lot.quantity_on_hand <= 0:
            lot.status = "DEPLETED"

        lot.updated_at = datetime.now()

        # 출고 기록 생성
        issue_record = WorkOrderItemIssue(
            work_order_item_id=work_order_item_id,
            lot_id=lot_id,
            lot_number=lot.lot_number,
            quantity=quantity,
            issue_date=datetime.now(),
            returned_quantity=Decimal(0)
        )
        self.db.add(issue_record)
        self.db.flush()

        return issue_record, ""

    def return_to_lot(
        self,
        issue_id: int,
        quantity: Decimal
    ) -> Tuple[bool, str]:
        """
        로트로 반납 처리

        Args:
            issue_id: 출고 기록 ID
            quantity: 반납 수량

        Returns:
            (성공 여부, 에러 메시지)
        """
        issue_record = self.db.query(WorkOrderItemIssue).filter(
            WorkOrderItemIssue.id == issue_id
        ).first()

        if not issue_record:
            return False, "출고 기록을 찾을 수 없습니다."

        max_returnable = issue_record.quantity - issue_record.returned_quantity
        if quantity > max_returnable:
            return False, f"반납 가능 수량({max_returnable})을 초과했습니다."

        # 로트에 반납
        if issue_record.lot_id:
            lot = self.get_by_id(issue_record.lot_id)
            if lot:
                lot.quantity_on_hand += quantity
                lot.quantity_issued -= quantity
                if lot.status == "DEPLETED":
                    lot.status = "ACTIVE"
                lot.updated_at = datetime.now()

        # 출고 기록 업데이트
        issue_record.returned_quantity += quantity

        self.db.flush()
        return True, ""

    # ==================== 로트번호 생성 ====================

    def generate_lot_number(
        self,
        part_id: int,
        po_number: Optional[str] = None,
        item_seq: int = 1
    ) -> str:
        """
        로트번호 자동 생성

        형식: LOT-{YYYYMMDD}-{seq} 또는 PO-{po_number}-{item_seq}
        """
        if po_number:
            # 발주서 기반 로트번호
            return f"PO-{po_number}-{item_seq:02d}"
        else:
            # 날짜 기반 로트번호
            today = datetime.now().strftime("%Y%m%d")
            prefix = f"LOT-{today}"

            # 오늘 생성된 로트 개수 조회
            count = self.db.query(InventoryLot).filter(
                InventoryLot.lot_number.like(f"{prefix}-%")
            ).count()

            return f"{prefix}-{count + 1:03d}"

    # ==================== 조회 (페이지네이션) ====================

    def get_all(
        self,
        part_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[InventoryLot], int]:
        """로트 목록 조회 (페이지네이션)"""
        query = self.db.query(InventoryLot)

        if part_id:
            query = query.filter(InventoryLot.part_id == part_id)

        if status:
            query = query.filter(InventoryLot.status == status)

        total = query.count()
        items = query.order_by(
            InventoryLot.received_date.desc()
        ).offset(skip).limit(limit).all()

        return items, total

    def get_issue_records_by_item(
        self,
        work_order_item_id: int
    ) -> List[WorkOrderItemIssue]:
        """작업지시서 항목별 출고 기록 조회"""
        return self.db.query(WorkOrderItemIssue).options(
            joinedload(WorkOrderItemIssue.lot)
        ).filter(
            WorkOrderItemIssue.work_order_item_id == work_order_item_id
        ).order_by(WorkOrderItemIssue.issue_date.asc()).all()
