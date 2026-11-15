"""
Inventory Repository
재고 관련 데이터 접근 로직을 캡슐화합니다.

v0.5.0: 재고관리 기능 추가
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, asc

from app.repositories.base import BaseRepository, build_keyword_filter
from app.models.inventory import Inventory, InventoryTransaction
from app.models.parts import Part
from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryTransactionCreate,
    InventoryStatus,
    TransactionType
)


class InventoryRepository(BaseRepository[Inventory, InventoryCreate, InventoryUpdate]):
    """
    재고 Repository

    재고 관련 데이터베이스 접근 로직을 제공합니다.
    """

    def __init__(self, db: Session):
        super().__init__(db, Inventory)

    # ==================== 조회 ====================

    def get_by_id_with_part(self, id: int) -> Optional[Inventory]:
        """ID로 재고 조회 (부품 정보 포함)"""
        return self.db.query(Inventory).options(
            joinedload(Inventory.part)
        ).filter(Inventory.id == id).first()

    def get_by_part_id(self, part_id: int) -> Optional[Inventory]:
        """부품 ID로 재고 조회"""
        return self.db.query(Inventory).filter(
            Inventory.part_id == part_id
        ).first()

    def get_by_part_id_with_part(self, part_id: int) -> Optional[Inventory]:
        """부품 ID로 재고 조회 (부품 정보 포함)"""
        return self.db.query(Inventory).options(
            joinedload(Inventory.part)
        ).filter(Inventory.part_id == part_id).first()

    def exists_by_part_id(self, part_id: int) -> bool:
        """부품 ID로 재고 존재 여부 확인"""
        return self.db.query(Inventory).filter(
            Inventory.part_id == part_id
        ).count() > 0

    # ==================== 검색 ====================

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
        """
        재고 검색

        Args:
            keyword: 검색 키워드 (품번, 부품명)
            status: 상태 필터
            low_stock_only: 부족 재고만 조회
            product_line_id: 대분류(제품라인) ID 필터
            part_group_id: 소분류(품목군) ID 필터
            level_id: 레벨 ID 필터
            skip: 건너뛸 개수
            limit: 조회 개수
            order_by: 정렬 기준
            order_desc: 내림차순 여부
        """
        query = self.db.query(Inventory).options(
            joinedload(Inventory.part)
        ).join(Part)

        # 키워드 검색 (부품 테이블 참조)
        if keyword:
            columns = [Part.part_number, Part.part_number_display, Part.part_name, Part.part_name_en]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 상태 필터
        if status:
            query = query.filter(Inventory.status == status.value)

        # 부족 재고만
        if low_stock_only:
            query = query.filter(
                Inventory.status.in_([InventoryStatus.LOW.value, InventoryStatus.OUT_OF_STOCK.value])
            )

        # 대분류 필터
        if product_line_id:
            query = query.filter(Part.product_line_id == product_line_id)

        # 소분류 필터
        if part_group_id:
            query = query.filter(Part.part_group_id == part_group_id)

        # 레벨 필터
        if level_id:
            query = query.filter(Part.level_id == level_id)

        # 활성화된 재고만
        query = query.filter(Inventory.is_active == True)

        # 정렬
        if order_by == "part_number":
            order_column = Part.part_number
        elif order_by == "part_name":
            order_column = Part.part_name
        elif hasattr(Inventory, order_by):
            order_column = getattr(Inventory, order_by)
        else:
            order_column = Inventory.updated_at

        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        return query.offset(skip).limit(limit).all()

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
        """재고 검색 + 총 개수 반환"""
        query = self.db.query(Inventory).options(
            joinedload(Inventory.part)
        ).join(Part)

        # 키워드 검색
        if keyword:
            columns = [Part.part_number, Part.part_number_display, Part.part_name, Part.part_name_en]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 상태 필터
        if status:
            query = query.filter(Inventory.status == status.value)

        # 부족 재고만
        if low_stock_only:
            query = query.filter(
                Inventory.status.in_([InventoryStatus.LOW.value, InventoryStatus.OUT_OF_STOCK.value])
            )

        # 대분류 필터
        if product_line_id:
            query = query.filter(Part.product_line_id == product_line_id)

        # 소분류 필터
        if part_group_id:
            query = query.filter(Part.part_group_id == part_group_id)

        # 레벨 필터
        if level_id:
            query = query.filter(Part.level_id == level_id)

        # 활성화된 재고만
        query = query.filter(Inventory.is_active == True)

        # 총 개수
        total = query.count()

        # 정렬
        if order_by == "part_number":
            order_column = Part.part_number
        elif order_by == "part_name":
            order_column = Part.part_name
        elif hasattr(Inventory, order_by):
            order_column = getattr(Inventory, order_by)
        else:
            order_column = Inventory.updated_at

        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        items = query.offset(skip).limit(limit).all()

        return items, total

    # ==================== 특수 조회 ====================

    def get_low_stock(self, limit: int = 100) -> List[Inventory]:
        """부족 재고 목록 조회"""
        return self.db.query(Inventory).options(
            joinedload(Inventory.part)
        ).filter(
            Inventory.is_active == True,
            Inventory.status.in_([InventoryStatus.LOW.value, InventoryStatus.OUT_OF_STOCK.value])
        ).order_by(Inventory.quantity_on_hand.asc()).limit(limit).all()

    def get_out_of_stock(self, limit: int = 100) -> List[Inventory]:
        """재고 없음 목록 조회"""
        return self.db.query(Inventory).options(
            joinedload(Inventory.part)
        ).filter(
            Inventory.is_active == True,
            Inventory.status == InventoryStatus.OUT_OF_STOCK.value
        ).order_by(Inventory.updated_at.desc()).limit(limit).all()


class InventoryTransactionRepository(BaseRepository[InventoryTransaction, InventoryTransactionCreate, InventoryTransactionCreate]):
    """
    재고 거래 Repository

    재고 거래 기록 관련 데이터베이스 접근 로직을 제공합니다.
    """

    def __init__(self, db: Session):
        super().__init__(db, InventoryTransaction)

    # ==================== 조회 ====================

    def get_by_id_with_part(self, id: int) -> Optional[InventoryTransaction]:
        """ID로 거래 조회 (부품 정보 포함)"""
        return self.db.query(InventoryTransaction).options(
            joinedload(InventoryTransaction.part)
        ).filter(InventoryTransaction.id == id).first()

    def get_by_inventory_id(
        self,
        inventory_id: int,
        skip: int = 0,
        limit: int = 50,
        order_desc: bool = True
    ) -> List[InventoryTransaction]:
        """재고 ID로 거래 이력 조회"""
        query = self.db.query(InventoryTransaction).options(
            joinedload(InventoryTransaction.part)
        ).filter(
            InventoryTransaction.inventory_id == inventory_id
        )

        order_column = InventoryTransaction.transaction_date
        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        return query.offset(skip).limit(limit).all()

    def get_by_inventory_id_with_count(
        self,
        inventory_id: int,
        skip: int = 0,
        limit: int = 50,
        order_desc: bool = True
    ) -> Tuple[List[InventoryTransaction], int]:
        """재고 ID로 거래 이력 조회 + 총 개수"""
        query = self.db.query(InventoryTransaction).options(
            joinedload(InventoryTransaction.part)
        ).filter(
            InventoryTransaction.inventory_id == inventory_id
        )

        total = query.count()

        order_column = InventoryTransaction.transaction_date
        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        items = query.offset(skip).limit(limit).all()

        return items, total

    def get_by_part_id(
        self,
        part_id: int,
        skip: int = 0,
        limit: int = 50,
        order_desc: bool = True
    ) -> List[InventoryTransaction]:
        """부품 ID로 거래 이력 조회"""
        query = self.db.query(InventoryTransaction).options(
            joinedload(InventoryTransaction.part)
        ).filter(
            InventoryTransaction.part_id == part_id
        )

        order_column = InventoryTransaction.transaction_date
        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        return query.offset(skip).limit(limit).all()

    def get_by_part_id_with_count(
        self,
        part_id: int,
        transaction_type: Optional[TransactionType] = None,
        skip: int = 0,
        limit: int = 50,
        order_desc: bool = True
    ) -> Tuple[List[InventoryTransaction], int]:
        """부품 ID로 거래 이력 조회 + 총 개수"""
        query = self.db.query(InventoryTransaction).options(
            joinedload(InventoryTransaction.part)
        ).filter(
            InventoryTransaction.part_id == part_id
        )

        if transaction_type:
            query = query.filter(InventoryTransaction.transaction_type == transaction_type.value)

        total = query.count()

        order_column = InventoryTransaction.transaction_date
        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        items = query.offset(skip).limit(limit).all()

        return items, total
