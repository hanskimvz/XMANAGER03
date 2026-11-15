"""
Purchase Order Repository
발주서 관련 데이터 접근 로직을 캡슐화합니다.

v0.6.0: 입출고 관리 기능 추가
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, asc, func
from datetime import date

from app.repositories.base import BaseRepository, build_keyword_filter
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderItemCreate,
    PurchaseOrderItemUpdate,
    PurchaseOrderStatus,
)


class PurchaseOrderRepository(BaseRepository[PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate]):
    """
    발주서 Repository

    발주서 관련 데이터베이스 접근 로직을 제공합니다.
    """

    def __init__(self, db: Session):
        super().__init__(db, PurchaseOrder)

    # ==================== 조회 ====================

    def get_by_id_with_relations(self, id: int) -> Optional[PurchaseOrder]:
        """ID로 발주서 조회 (관계 포함)"""
        return self.db.query(PurchaseOrder).options(
            joinedload(PurchaseOrder.supplier),
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.part),
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.unit)
        ).filter(PurchaseOrder.id == id).first()

    def get_by_po_number(self, po_number: str) -> Optional[PurchaseOrder]:
        """발주서 번호로 조회"""
        return self.db.query(PurchaseOrder).filter(
            PurchaseOrder.po_number == po_number
        ).first()

    def get_by_po_number_with_relations(self, po_number: str) -> Optional[PurchaseOrder]:
        """발주서 번호로 조회 (관계 포함)"""
        return self.db.query(PurchaseOrder).options(
            joinedload(PurchaseOrder.supplier),
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.part),
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.unit)
        ).filter(PurchaseOrder.po_number == po_number).first()

    def exists_by_po_number(self, po_number: str) -> bool:
        """발주서 번호 존재 여부 확인"""
        return self.db.query(PurchaseOrder).filter(
            PurchaseOrder.po_number == po_number
        ).count() > 0

    # ==================== 검색 ====================

    def search_purchase_orders(
        self,
        keyword: Optional[str] = None,
        status: Optional[PurchaseOrderStatus] = None,
        supplier_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[PurchaseOrder]:
        """발주서 검색"""
        query = self.db.query(PurchaseOrder).options(
            joinedload(PurchaseOrder.supplier)
        )

        # 키워드 검색
        if keyword:
            columns = [PurchaseOrder.po_number, PurchaseOrder.remarks]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 상태 필터
        if status:
            query = query.filter(PurchaseOrder.status == status.value)

        # 공급업체 필터
        if supplier_id:
            query = query.filter(PurchaseOrder.supplier_id == supplier_id)

        # 날짜 범위 필터
        if from_date:
            query = query.filter(PurchaseOrder.order_date >= from_date)
        if to_date:
            query = query.filter(PurchaseOrder.order_date <= to_date)

        # 정렬
        if hasattr(PurchaseOrder, order_by):
            order_column = getattr(PurchaseOrder, order_by)
        else:
            order_column = PurchaseOrder.created_at

        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        return query.offset(skip).limit(limit).all()

    def search_purchase_orders_with_count(
        self,
        keyword: Optional[str] = None,
        status: Optional[PurchaseOrderStatus] = None,
        supplier_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[PurchaseOrder], int]:
        """발주서 검색 + 총 개수"""
        query = self.db.query(PurchaseOrder).options(
            joinedload(PurchaseOrder.supplier)
        )

        # 키워드 검색
        if keyword:
            columns = [PurchaseOrder.po_number, PurchaseOrder.remarks]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 상태 필터
        if status:
            query = query.filter(PurchaseOrder.status == status.value)

        # 공급업체 필터
        if supplier_id:
            query = query.filter(PurchaseOrder.supplier_id == supplier_id)

        # 날짜 범위 필터
        if from_date:
            query = query.filter(PurchaseOrder.order_date >= from_date)
        if to_date:
            query = query.filter(PurchaseOrder.order_date <= to_date)

        # 총 개수
        total = query.count()

        # 정렬
        if hasattr(PurchaseOrder, order_by):
            order_column = getattr(PurchaseOrder, order_by)
        else:
            order_column = PurchaseOrder.created_at

        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        items = query.offset(skip).limit(limit).all()

        return items, total

    # ==================== 번호 생성 ====================

    def get_last_po_number_for_date(self, date_prefix: str) -> Optional[str]:
        """특정 날짜의 마지막 발주서 번호 조회"""
        return self.db.query(PurchaseOrder.po_number).filter(
            PurchaseOrder.po_number.like(f"{date_prefix}%")
        ).order_by(PurchaseOrder.po_number.desc()).first()

    # ==================== 부품 가격 이력 ====================

    def get_part_price_history(self, part_id: int, limit: int = 5) -> List[dict]:
        """부품별 이전 구매 가격 이력 조회"""
        from app.models.business_partner import BusinessPartner

        results = self.db.query(
            PurchaseOrderItem.unit_price,
            PurchaseOrder.order_date,
            BusinessPartner.partner_name
        ).join(
            PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id
        ).join(
            BusinessPartner, PurchaseOrder.supplier_id == BusinessPartner.id
        ).filter(
            PurchaseOrderItem.part_id == part_id,
            PurchaseOrder.status != PurchaseOrderStatus.CANCELLED
        ).order_by(
            PurchaseOrder.order_date.desc()
        ).limit(limit).all()

        return [
            {
                "unit_price": float(r.unit_price) if r.unit_price else 0,
                "order_date": r.order_date.isoformat() if r.order_date else "",
                "supplier_name": r.partner_name or ""
            }
            for r in results
        ]


class PurchaseOrderItemRepository(BaseRepository[PurchaseOrderItem, PurchaseOrderItemCreate, PurchaseOrderItemUpdate]):
    """
    발주서 항목 Repository

    발주서 항목 관련 데이터베이스 접근 로직을 제공합니다.
    """

    def __init__(self, db: Session):
        super().__init__(db, PurchaseOrderItem)

    # ==================== 조회 ====================

    def get_by_id_with_relations(self, id: int) -> Optional[PurchaseOrderItem]:
        """ID로 발주서 항목 조회 (관계 포함)"""
        return self.db.query(PurchaseOrderItem).options(
            joinedload(PurchaseOrderItem.part),
            joinedload(PurchaseOrderItem.unit)
        ).filter(PurchaseOrderItem.id == id).first()

    def get_by_purchase_order_id(self, purchase_order_id: int) -> List[PurchaseOrderItem]:
        """발주서 ID로 항목 목록 조회"""
        return self.db.query(PurchaseOrderItem).options(
            joinedload(PurchaseOrderItem.part),
            joinedload(PurchaseOrderItem.unit)
        ).filter(
            PurchaseOrderItem.purchase_order_id == purchase_order_id
        ).order_by(PurchaseOrderItem.sort_order).all()

    def delete_by_purchase_order_id(self, purchase_order_id: int) -> int:
        """발주서 ID로 항목 전체 삭제"""
        count = self.db.query(PurchaseOrderItem).filter(
            PurchaseOrderItem.purchase_order_id == purchase_order_id
        ).delete()
        self.db.commit()
        return count
