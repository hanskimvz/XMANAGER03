"""
Inventory Lot Service (v0.7.0)
로트 관리 및 FIFO 출고 관련 비즈니스 로직

주요 기능:
- 로트 CRUD
- FIFO 출고 제안
- 생산 가용수량 체크
"""

from typing import Optional, List, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.inventory_lot_repository import InventoryLotRepository
from app.models.inventory_lot import InventoryLot, WorkOrderItemIssue
from app.models.inventory import Inventory
from app.models.bom import BOM
from app.models.parts import Part
from app.schemas.inventory_lot import (
    InventoryLotCreate,
    InventoryLotUpdate,
    FIFOSuggestionResponse,
    ProductionAvailabilityResponse,
    BOMItemAvailability,
    LimitingPart,
    PaginatedLotResponse,
)
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException,
)


class InventoryLotService:
    """
    재고 로트 서비스

    로트 관리 및 FIFO 출고 관련 비즈니스 로직을 캡슐화합니다.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = InventoryLotRepository(db)

    # ==================== CRUD ====================

    def create_lot(self, data: InventoryLotCreate) -> InventoryLot:
        """로트 생성"""
        # 중복 로트번호 체크
        existing = self.repository.get_by_lot_number(data.part_id, data.lot_number)
        if existing:
            raise BusinessRuleException(f"동일한 로트번호가 이미 존재합니다: {data.lot_number}")

        lot = self.repository.create(data)
        self.db.commit()
        return lot

    def get_lot(self, lot_id: int) -> Optional[InventoryLot]:
        """로트 조회"""
        return self.repository.get_by_id(lot_id)

    def get_lot_or_raise(self, lot_id: int) -> InventoryLot:
        """로트 조회 (없으면 예외)"""
        lot = self.repository.get_by_id(lot_id)
        if not lot:
            raise NotFoundException("로트", lot_id)
        return lot

    def update_lot(self, lot_id: int, data: InventoryLotUpdate) -> InventoryLot:
        """로트 수정"""
        lot = self.repository.update(lot_id, data)
        if not lot:
            raise NotFoundException("로트", lot_id)
        self.db.commit()
        return lot

    def delete_lot(self, lot_id: int) -> bool:
        """로트 삭제 (소진된 로트만)"""
        success = self.repository.delete(lot_id)
        if not success:
            raise BusinessRuleException("잔량이 있는 로트는 삭제할 수 없습니다.")
        self.db.commit()
        return True

    # ==================== 조회 ====================

    def get_lots_by_part(
        self,
        part_id: int,
        include_depleted: bool = False
    ) -> List[InventoryLot]:
        """부품별 로트 목록 조회"""
        return self.repository.get_by_part_id(part_id, include_depleted)

    def get_lots_paginated(
        self,
        part_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> PaginatedLotResponse:
        """로트 목록 조회 (페이지네이션)"""
        items, total = self.repository.get_all(
            part_id=part_id,
            status=status,
            skip=skip,
            limit=limit
        )

        return PaginatedLotResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + len(items) < total
        )

    # ==================== FIFO 출고 ====================

    def get_fifo_suggestion(
        self,
        part_id: int,
        quantity: Decimal
    ) -> FIFOSuggestionResponse:
        """
        FIFO 출고 제안 조회

        Args:
            part_id: 부품 ID
            quantity: 필요 수량

        Returns:
            FIFO 출고 제안 응답
        """
        lots, is_sufficient = self.repository.get_fifo_lots(part_id, quantity)
        total_available = self.repository.get_available_quantity(part_id)

        shortage = max(Decimal(0), quantity - total_available)

        return FIFOSuggestionResponse(
            part_id=part_id,
            requested_quantity=quantity,
            is_sufficient=is_sufficient,
            total_available=total_available,
            shortage=shortage,
            lots=lots
        )

    def issue_from_lots(
        self,
        work_order_item_id: int,
        lot_selections: List[dict]
    ) -> List[WorkOrderItemIssue]:
        """
        로트에서 출고 처리

        Args:
            work_order_item_id: 작업지시서 항목 ID
            lot_selections: [{"lot_id": 1, "quantity": 100}, ...]

        Returns:
            출고 기록 목록
        """
        issue_records = []

        for selection in lot_selections:
            lot_id = selection["lot_id"]
            quantity = Decimal(str(selection["quantity"]))

            record, error = self.repository.issue_from_lot(
                lot_id=lot_id,
                quantity=quantity,
                work_order_item_id=work_order_item_id
            )

            if error:
                raise ValidationException(error)

            issue_records.append(record)

        self.db.commit()
        return issue_records

    def issue_with_fifo(
        self,
        work_order_item_id: int,
        part_id: int,
        quantity: Decimal
    ) -> List[WorkOrderItemIssue]:
        """
        FIFO 방식으로 자동 출고

        Args:
            work_order_item_id: 작업지시서 항목 ID
            part_id: 부품 ID
            quantity: 출고 수량

        Returns:
            출고 기록 목록 (로트가 없으면 빈 리스트)
        """
        # FIFO 순서로 로트 조회
        lots, is_sufficient = self.repository.get_fifo_lots(part_id, quantity)

        # 로트가 없는 경우 (기존 재고는 로트 없이 관리됨)
        if not lots:
            return []

        if not is_sufficient:
            available = self.repository.get_available_quantity(part_id)
            raise ValidationException(
                f"로트 재고가 부족합니다. 필요: {quantity}, 가용: {available}"
            )

        # 로트 선택 리스트로 변환
        lot_selections = [
            {"lot_id": lot.lot_id, "quantity": lot.suggested_quantity}
            for lot in lots
        ]

        return self.issue_from_lots(work_order_item_id, lot_selections)

    def return_to_lot(
        self,
        issue_id: int,
        quantity: Decimal
    ) -> bool:
        """로트로 반납"""
        success, error = self.repository.return_to_lot(issue_id, quantity)
        if not success:
            raise ValidationException(error)
        self.db.commit()
        return True

    # ==================== 생산 가용수량 체크 ====================

    def check_production_availability(
        self,
        product_part_id: int,
        quantity: Decimal
    ) -> ProductionAvailabilityResponse:
        """
        BOM 기준 생산 가용수량 체크

        Args:
            product_part_id: 완제품 부품 ID
            quantity: 생산 수량

        Returns:
            생산 가용수량 응답
        """
        # BOM 전개
        bom_items = self._expand_bom(product_part_id, quantity)

        if not bom_items:
            return ProductionAvailabilityResponse(
                product_part_id=product_part_id,
                requested_quantity=quantity,
                can_produce=int(quantity),  # BOM 없으면 그냥 생산 가능
                limiting_parts=[],
                items=[]
            )

        # 각 BOM 항목별 가용수량 체크
        item_availabilities = []
        min_can_produce = float('inf')
        limiting_parts = []

        for item in bom_items:
            part_id = item["part_id"]
            required_quantity = item["required_quantity"]
            required_per_unit = item["required_per_unit"]

            # 가용 재고 조회
            available = self.repository.get_available_quantity(part_id)
            shortage = max(Decimal(0), required_quantity - available)

            # 상태 결정
            if available <= 0:
                status = "OUT_OF_STOCK"
            elif available < required_quantity:
                status = "INSUFFICIENT"
            else:
                status = "SUFFICIENT"

            item_availabilities.append(BOMItemAvailability(
                part_id=part_id,
                part_number=item["part_number"],
                part_name=item["part_name"],
                required_per_unit=required_per_unit,
                required_quantity=required_quantity,
                available_quantity=available,
                shortage=shortage,
                status=status
            ))

            # 생산 가능 수량 계산
            if required_per_unit > 0:
                can_make = int(available / required_per_unit)

                if can_make < min_can_produce:
                    min_can_produce = can_make
                    limiting_parts = [LimitingPart(
                        part_id=part_id,
                        part_number=item["part_number"],
                        part_name=item["part_name"],
                        required_per_unit=required_per_unit,
                        available_quantity=available,
                        can_produce=can_make
                    )]
                elif can_make == min_can_produce:
                    limiting_parts.append(LimitingPart(
                        part_id=part_id,
                        part_number=item["part_number"],
                        part_name=item["part_name"],
                        required_per_unit=required_per_unit,
                        available_quantity=available,
                        can_produce=can_make
                    ))

        return ProductionAvailabilityResponse(
            product_part_id=product_part_id,
            requested_quantity=quantity,
            can_produce=min_can_produce if min_can_produce != float('inf') else 0,
            limiting_parts=limiting_parts,
            items=item_availabilities
        )

    def _expand_bom(
        self,
        product_part_id: int,
        quantity: Decimal,
        level: int = 1
    ) -> List[dict]:
        """
        BOM 전개 (1레벨만)

        Args:
            product_part_id: 상위 부품 ID
            quantity: 수량
            level: BOM 레벨

        Returns:
            전개된 BOM 항목 목록
        """
        # 직접 하위 BOM 조회
        bom_items = self.db.query(BOM).filter(
            BOM.parent_part_id == product_part_id,
            BOM.is_active == True
        ).all()

        result = []
        for bom in bom_items:
            child_part = self.db.query(Part).filter(Part.id == bom.child_part_id).first()
            if not child_part:
                continue

            required_per_unit = bom.quantity
            required_quantity = required_per_unit * quantity

            result.append({
                "part_id": child_part.id,
                "part_number": child_part.part_number_display or child_part.part_number,
                "part_name": child_part.part_name,
                "required_per_unit": required_per_unit,
                "required_quantity": required_quantity,
                "bom_level": level
            })

        return result

    # ==================== 로트번호 생성 ====================

    def generate_lot_number(
        self,
        part_id: int,
        po_number: Optional[str] = None,
        item_seq: int = 1
    ) -> str:
        """로트번호 자동 생성"""
        return self.repository.generate_lot_number(part_id, po_number, item_seq)

    # ==================== 출고 기록 조회 ====================

    def get_issue_records(
        self,
        work_order_item_id: int
    ) -> List[WorkOrderItemIssue]:
        """작업지시서 항목별 출고 기록 조회"""
        return self.repository.get_issue_records_by_item(work_order_item_id)

    # ==================== 누락 로트 자동 생성 ====================

    def generate_missing_lots(self) -> dict:
        """
        로트가 없는 재고에 대해 임의의 로트를 자동 생성합니다.

        재고 수량이 0보다 큰 부품 중 로트가 없는 부품에 대해:
        - 로트번호: INIT-YYYYMMDD-{순번}
        - 입고일: 현재일시
        - 수량: 해당 재고의 현재고 수량

        Returns:
            {
                "created_count": 생성된 로트 수,
                "skipped_count": 이미 로트가 있는 부품 수,
                "details": [{"part_id": ..., "lot_number": ..., "quantity": ...}, ...]
            }
        """
        from sqlalchemy import func, and_
        from sqlalchemy.orm import aliased

        # 재고가 있는 부품 목록 조회 (quantity_on_hand > 0)
        inventories = self.db.query(Inventory).filter(
            Inventory.quantity_on_hand > 0,
            Inventory.is_active == True
        ).all()

        today_str = datetime.now().strftime("%Y%m%d")
        created_count = 0
        skipped_count = 0
        details = []

        for inv in inventories:
            # 해당 부품에 활성 로트가 있는지 확인
            existing_lots = self.db.query(InventoryLot).filter(
                InventoryLot.part_id == inv.part_id,
                InventoryLot.status == "ACTIVE"
            ).count()

            if existing_lots > 0:
                skipped_count += 1
                continue

            # 로트번호 생성: INIT-YYYYMMDD-{순번}
            # 같은 날짜에 생성된 INIT 로트 개수 확인
            init_lot_count = self.db.query(InventoryLot).filter(
                InventoryLot.lot_number.like(f"INIT-{today_str}-%")
            ).count()

            lot_number = f"INIT-{today_str}-{str(init_lot_count + created_count + 1).zfill(4)}"

            # 부품 정보 조회
            part = self.db.query(Part).filter(Part.id == inv.part_id).first()

            # 로트 생성
            new_lot = InventoryLot(
                part_id=inv.part_id,
                lot_number=lot_number,
                quantity_received=inv.quantity_on_hand,
                quantity_on_hand=inv.quantity_on_hand,
                quantity_issued=Decimal(0),
                received_date=datetime.now(),
                unit_cost=inv.unit_cost,
                status="ACTIVE",
                remarks=f"초기 재고 로트 (자동생성) - 부품: {part.part_number if part else inv.part_id}"
            )

            self.db.add(new_lot)
            created_count += 1
            details.append({
                "part_id": inv.part_id,
                "part_number": part.part_number_display or part.part_number if part else str(inv.part_id),
                "part_name": part.part_name if part else "",
                "lot_number": lot_number,
                "quantity": float(inv.quantity_on_hand)
            })

        self.db.commit()

        return {
            "created_count": created_count,
            "skipped_count": skipped_count,
            "details": details
        }
