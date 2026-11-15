"""
Inventory Service (v0.5.0)
재고 관련 비즈니스 로직을 처리합니다.

Repository Pattern을 통해 데이터 접근 로직과 분리됩니다.

v0.5.0: 재고관리 기능 추가
- 재고 조회/생성/수정/삭제
- 재고 조정 (입고/출고/조정)
- 재고 상태 자동 계산
- 거래 이력 관리
"""

from typing import Optional, List, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.repositories.inventory_repository import InventoryRepository, InventoryTransactionRepository
from app.repositories.inventory_lot_repository import InventoryLotRepository
from app.models.inventory import Inventory, InventoryTransaction
from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryAdjust,
    InventoryStatus,
    TransactionType,
)
from app.schemas.inventory_lot import InventoryLotCreate
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException,
)


class InventoryService:
    """
    재고 서비스

    재고 관련 비즈니스 로직을 캡슐화합니다.
    - 재고 CRUD
    - 재고 조정 (입고/출고/조정)
    - 상태 자동 계산
    - 거래 이력 생성
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = InventoryRepository(db)
        self.transaction_repository = InventoryTransactionRepository(db)
        self.lot_repository = InventoryLotRepository(db)

    # ==================== 조회 ====================

    def get(self, id: int) -> Optional[Inventory]:
        """ID로 재고 조회"""
        return self.repository.get_by_id_with_part(id)

    def get_or_raise(self, id: int) -> Inventory:
        """ID로 재고 조회 (없으면 예외)"""
        inventory = self.repository.get_by_id_with_part(id)
        if not inventory:
            raise NotFoundException("재고", id)
        return inventory

    def get_by_part_id(self, part_id: int) -> Optional[Inventory]:
        """부품 ID로 재고 조회"""
        return self.repository.get_by_part_id_with_part(part_id)

    def get_by_part_id_or_raise(self, part_id: int) -> Inventory:
        """부품 ID로 재고 조회 (없으면 예외)"""
        inventory = self.repository.get_by_part_id_with_part(part_id)
        if not inventory:
            raise NotFoundException("재고 (부품 ID)", part_id)
        return inventory

    def search_inventory(
        self,
        keyword: Optional[str] = None,
        status: Optional[InventoryStatus] = None,
        low_stock_only: bool = False,
        product_line_id: Optional[int] = None,
        part_group_id: Optional[int] = None,
        level_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "updated_at",
        order_desc: bool = True
    ) -> List[Inventory]:
        """재고 검색"""
        return self.repository.search_inventory(
            keyword=keyword,
            status=status,
            low_stock_only=low_stock_only,
            product_line_id=product_line_id,
            part_group_id=part_group_id,
            level_id=level_id,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    def search_inventory_with_count(
        self,
        keyword: Optional[str] = None,
        status: Optional[InventoryStatus] = None,
        low_stock_only: bool = False,
        product_line_id: Optional[int] = None,
        part_group_id: Optional[int] = None,
        level_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "updated_at",
        order_desc: bool = True
    ) -> Tuple[List[Inventory], int]:
        """재고 검색 + 총 개수"""
        return self.repository.search_inventory_with_count(
            keyword=keyword,
            status=status,
            low_stock_only=low_stock_only,
            product_line_id=product_line_id,
            part_group_id=part_group_id,
            level_id=level_id,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    def get_low_stock(self, limit: int = 100) -> List[Inventory]:
        """부족 재고 목록 조회"""
        return self.repository.get_low_stock(limit)

    def get_out_of_stock(self, limit: int = 100) -> List[Inventory]:
        """재고 없음 목록 조회"""
        return self.repository.get_out_of_stock(limit)

    # ==================== 생성 ====================

    def create_inventory(self, inventory_in: InventoryCreate) -> Inventory:
        """
        재고 생성

        Args:
            inventory_in: 재고 생성 데이터

        Returns:
            생성된 재고
        """
        # 이미 해당 부품에 재고가 있는지 확인
        if self.repository.exists_by_part_id(inventory_in.part_id):
            raise BusinessRuleException(f"부품 ID {inventory_in.part_id}에 대한 재고가 이미 존재합니다.")

        # 재고 생성
        inventory_data = inventory_in.model_dump()
        inventory_data["status"] = self._calculate_status(
            Decimal(inventory_data.get("quantity_on_hand", 0)),
            inventory_data.get("reorder_point")
        )

        inventory = self.repository.create_from_dict(inventory_data)

        # 초기 거래 이력 생성 (수량이 0보다 크면)
        if inventory.quantity_on_hand > 0:
            self._create_transaction(
                inventory=inventory,
                transaction_type=TransactionType.ADJUST,
                quantity=inventory.quantity_on_hand,
                quantity_before=Decimal(0),
                quantity_after=inventory.quantity_on_hand,
                reason="초기 재고 등록"
            )

        return self.repository.get_by_id_with_part(inventory.id)

    def create_inventory_for_part(self, part_id: int) -> Inventory:
        """
        부품에 대한 재고 자동 생성 (부품 생성 시 호출)

        Args:
            part_id: 부품 ID

        Returns:
            생성된 재고
        """
        # 이미 존재하면 기존 재고 반환
        existing = self.repository.get_by_part_id(part_id)
        if existing:
            return existing

        # 재고 생성 (초기 수량 0)
        inventory = Inventory(
            part_id=part_id,
            quantity_on_hand=Decimal(0),
            status=InventoryStatus.OUT_OF_STOCK.value,
            is_active=True
        )
        self.db.add(inventory)
        self.db.commit()
        self.db.refresh(inventory)

        return inventory

    def initialize_inventory_for_all_parts(self) -> dict:
        """
        모든 기존 부품에 대해 재고 레코드 일괄 생성

        재고가 없는 부품에 대해서만 새로 생성합니다.

        Returns:
            {"created": 생성된 수, "skipped": 이미 존재하여 건너뛴 수}
        """
        from app.models.parts import Part

        # 재고가 없는 부품 조회
        subquery = self.db.query(Inventory.part_id).subquery()
        parts_without_inventory = self.db.query(Part).filter(
            Part.is_active == True,
            ~Part.id.in_(subquery)
        ).all()

        created_count = 0
        for part in parts_without_inventory:
            inventory = Inventory(
                part_id=part.id,
                quantity_on_hand=Decimal(0),
                status=InventoryStatus.OUT_OF_STOCK.value,
                is_active=True
            )
            self.db.add(inventory)
            created_count += 1

        self.db.commit()

        # 이미 재고가 있는 부품 수
        skipped_count = self.db.query(Part).filter(
            Part.is_active == True,
            Part.id.in_(subquery)
        ).count()

        return {
            "created": created_count,
            "skipped": skipped_count,
            "total_parts": created_count + skipped_count
        }

    # ==================== 수정 ====================

    def update_inventory(self, inventory_id: int, inventory_in: InventoryUpdate) -> Inventory:
        """
        재고 정보 수정 (재주문점, 단가 등 - 수량 제외)

        Args:
            inventory_id: 재고 ID
            inventory_in: 수정 데이터

        Returns:
            수정된 재고
        """
        inventory = self.get_or_raise(inventory_id)

        update_data = inventory_in.model_dump(exclude_unset=True)

        # 재주문점이 변경되면 상태 재계산
        if "reorder_point" in update_data:
            update_data["status"] = self._calculate_status(
                inventory.quantity_on_hand,
                update_data.get("reorder_point")
            )

        self.repository.update_from_dict(inventory, update_data)

        return self.repository.get_by_id_with_part(inventory_id)

    # ==================== 재고 조정 ====================

    def adjust_inventory(self, inventory_id: int, adjust: InventoryAdjust) -> Inventory:
        """
        재고 조정 (입고/출고/조정)

        Args:
            inventory_id: 재고 ID
            adjust: 조정 데이터

        Returns:
            조정된 재고
        """
        inventory = self.get_or_raise(inventory_id)

        quantity_before = inventory.quantity_on_hand

        # 수량 계산
        if adjust.transaction_type == TransactionType.IN:
            # 입고: 수량 증가
            new_quantity = quantity_before + adjust.quantity
        elif adjust.transaction_type == TransactionType.OUT:
            # 출고: 수량 감소
            new_quantity = quantity_before - adjust.quantity
            if new_quantity < 0:
                raise ValidationException(
                    f"출고 수량({adjust.quantity})이 현재고({quantity_before})보다 많습니다."
                )
        elif adjust.transaction_type == TransactionType.ADJUST:
            # 조정: 수량 직접 설정
            new_quantity = adjust.quantity
        elif adjust.transaction_type == TransactionType.RETURN:
            # 반품: 수량 증가
            new_quantity = quantity_before + adjust.quantity
        elif adjust.transaction_type == TransactionType.COUNT:
            # 실사: 수량 직접 설정 + 실사일 업데이트
            new_quantity = adjust.quantity
            inventory.last_count_date = datetime.now()
        else:
            raise ValidationException(f"지원하지 않는 거래 유형: {adjust.transaction_type}")

        # 거래 이력 생성
        self._create_transaction(
            inventory=inventory,
            transaction_type=adjust.transaction_type,
            quantity=adjust.quantity,
            quantity_before=quantity_before,
            quantity_after=new_quantity,
            reason=adjust.reason,
            reference_type=adjust.reference_type,
            reference_id=adjust.reference_id,
            remarks=adjust.remarks
        )

        # 재고 업데이트
        inventory.quantity_on_hand = new_quantity
        inventory.status = self._calculate_status(new_quantity, inventory.reorder_point)
        inventory.updated_at = datetime.now()

        # 입고 시 로트 생성 옵션 처리
        if adjust.transaction_type == TransactionType.IN and adjust.create_lot:
            # 로트 번호 생성 (비워두면 자동 생성)
            lot_number = adjust.lot_number
            if not lot_number:
                lot_number = self.lot_repository.generate_lot_number(inventory.part_id)

            # 로트 생성
            lot_data = InventoryLotCreate(
                part_id=inventory.part_id,
                lot_number=lot_number,
                quantity_received=adjust.quantity,
                received_date=datetime.now(),
                unit_cost=adjust.unit_cost,
                remarks=adjust.remarks or f"수동 입고: {adjust.reason or ''}"
            )
            self.lot_repository.create(lot_data)

        self.db.commit()
        self.db.refresh(inventory)

        return self.repository.get_by_id_with_part(inventory_id)

    # ==================== 삭제 ====================

    def delete_inventory(self, inventory_id: int) -> bool:
        """
        재고 삭제

        Args:
            inventory_id: 재고 ID

        Returns:
            삭제 성공 여부
        """
        inventory = self.get_or_raise(inventory_id)
        return self.repository.delete(inventory)

    def soft_delete_inventory(self, inventory_id: int) -> Inventory:
        """
        재고 비활성화 (소프트 삭제)

        Args:
            inventory_id: 재고 ID

        Returns:
            비활성화된 재고
        """
        inventory = self.get_or_raise(inventory_id)
        inventory.is_active = False
        self.db.commit()
        self.db.refresh(inventory)
        return inventory

    # ==================== 거래 이력 ====================

    def get_transactions(
        self,
        inventory_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[InventoryTransaction], int]:
        """재고 ID로 거래 이력 조회"""
        return self.transaction_repository.get_by_inventory_id_with_count(
            inventory_id=inventory_id,
            skip=skip,
            limit=limit
        )

    def get_transactions_by_part(
        self,
        part_id: int,
        transaction_type: Optional[TransactionType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[InventoryTransaction], int]:
        """부품 ID로 거래 이력 조회"""
        return self.transaction_repository.get_by_part_id_with_count(
            part_id=part_id,
            transaction_type=transaction_type,
            skip=skip,
            limit=limit
        )

    # ==================== 내부 메서드 ====================

    def _calculate_status(
        self,
        quantity_on_hand: Decimal,
        reorder_point: Optional[Decimal]
    ) -> str:
        """
        재고 상태 자동 계산

        Args:
            quantity_on_hand: 현재고
            reorder_point: 재주문점

        Returns:
            상태 문자열
        """
        if quantity_on_hand <= 0:
            return InventoryStatus.OUT_OF_STOCK.value
        elif reorder_point and quantity_on_hand < reorder_point:
            return InventoryStatus.LOW.value
        else:
            return InventoryStatus.NORMAL.value

    def _create_transaction(
        self,
        inventory: Inventory,
        transaction_type: TransactionType,
        quantity: Decimal,
        quantity_before: Decimal,
        quantity_after: Decimal,
        reason: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        remarks: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> InventoryTransaction:
        """거래 이력 생성 (내부용)"""
        transaction = InventoryTransaction(
            inventory_id=inventory.id,
            part_id=inventory.part_id,
            transaction_type=transaction_type.value,
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            remarks=remarks,
            created_by=created_by
        )
        self.db.add(transaction)
        return transaction

    # ==================== 거래 파일 첨부 (v0.6.0) ====================

    def get_transaction(self, transaction_id: int) -> Optional[InventoryTransaction]:
        """거래 이력 단건 조회"""
        return self.transaction_repository.get_by_id(transaction_id)

    def get_transaction_or_raise(self, transaction_id: int) -> InventoryTransaction:
        """거래 이력 단건 조회 (없으면 예외)"""
        transaction = self.transaction_repository.get_by_id(transaction_id)
        if not transaction:
            raise NotFoundException("재고 거래", transaction_id)
        return transaction

    def add_transaction_document(self, transaction_id: int, file_info: dict) -> InventoryTransaction:
        """
        거래 이력에 파일 첨부

        Args:
            transaction_id: 거래 ID
            file_info: 파일 정보 (file_name, file_path, file_size 등)

        Returns:
            수정된 거래 이력
        """
        transaction = self.get_transaction_or_raise(transaction_id)

        files = transaction.document_files or []
        files.append(file_info)
        transaction.document_files = files
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def remove_transaction_document(self, transaction_id: int, file_index: int) -> InventoryTransaction:
        """
        거래 이력 파일 삭제

        Args:
            transaction_id: 거래 ID
            file_index: 파일 인덱스

        Returns:
            수정된 거래 이력
        """
        transaction = self.get_transaction_or_raise(transaction_id)

        files = transaction.document_files or []
        if file_index < 0 or file_index >= len(files):
            raise ValidationException(f"유효하지 않은 파일 인덱스: {file_index}")

        files.pop(file_index)
        transaction.document_files = files
        self.db.commit()
        self.db.refresh(transaction)

        return transaction
