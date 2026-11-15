"""
Work Order Repository
작업지시서 관련 데이터 접근 로직을 캡슐화합니다.

v0.6.0: 입출고 관리 기능 추가
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, asc, func
from datetime import date

from app.repositories.base import BaseRepository, build_keyword_filter
from app.models.work_order import WorkOrder, WorkOrderItem
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderItemCreate,
    WorkOrderStatus,
)


class WorkOrderRepository(BaseRepository[WorkOrder, WorkOrderCreate, WorkOrderUpdate]):
    """
    작업지시서 Repository

    작업지시서 관련 데이터베이스 접근 로직을 제공합니다.
    """

    def __init__(self, db: Session):
        super().__init__(db, WorkOrder)

    # ==================== 조회 ====================

    def get_by_id_with_relations(self, id: int) -> Optional[WorkOrder]:
        """ID로 작업지시서 조회 (관계 포함)"""
        return self.db.query(WorkOrder).options(
            joinedload(WorkOrder.product_part),
            joinedload(WorkOrder.customer),
            joinedload(WorkOrder.items).joinedload(WorkOrderItem.part),
            joinedload(WorkOrder.items).joinedload(WorkOrderItem.unit)
        ).filter(WorkOrder.id == id).first()

    def get_by_wo_number(self, wo_number: str) -> Optional[WorkOrder]:
        """작업지시서 번호로 조회"""
        return self.db.query(WorkOrder).filter(
            WorkOrder.wo_number == wo_number
        ).first()

    def get_by_wo_number_with_relations(self, wo_number: str) -> Optional[WorkOrder]:
        """작업지시서 번호로 조회 (관계 포함)"""
        return self.db.query(WorkOrder).options(
            joinedload(WorkOrder.product_part),
            joinedload(WorkOrder.customer),
            joinedload(WorkOrder.items).joinedload(WorkOrderItem.part),
            joinedload(WorkOrder.items).joinedload(WorkOrderItem.unit)
        ).filter(WorkOrder.wo_number == wo_number).first()

    def exists_by_wo_number(self, wo_number: str) -> bool:
        """작업지시서 번호 존재 여부 확인"""
        return self.db.query(WorkOrder).filter(
            WorkOrder.wo_number == wo_number
        ).count() > 0

    # ==================== 검색 ====================

    def search_work_orders(
        self,
        keyword: Optional[str] = None,
        status: Optional[WorkOrderStatus] = None,
        customer_id: Optional[int] = None,
        product_part_id: Optional[int] = None,
        priority: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[WorkOrder]:
        """작업지시서 검색"""
        query = self.db.query(WorkOrder).options(
            joinedload(WorkOrder.product_part),
            joinedload(WorkOrder.customer)
        )

        # 키워드 검색
        if keyword:
            columns = [WorkOrder.wo_number, WorkOrder.customer_order_no, WorkOrder.remarks]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 상태 필터
        if status:
            query = query.filter(WorkOrder.status == status.value)

        # 고객사 필터
        if customer_id:
            query = query.filter(WorkOrder.customer_id == customer_id)

        # 완제품 필터
        if product_part_id:
            query = query.filter(WorkOrder.product_part_id == product_part_id)

        # 우선순위 필터
        if priority is not None:
            query = query.filter(WorkOrder.priority == priority)

        # 날짜 범위 필터 (접수일 기준)
        if from_date:
            query = query.filter(func.date(WorkOrder.received_date) >= from_date)
        if to_date:
            query = query.filter(func.date(WorkOrder.received_date) <= to_date)

        # 정렬
        if hasattr(WorkOrder, order_by):
            order_column = getattr(WorkOrder, order_by)
        else:
            order_column = WorkOrder.created_at

        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        return query.offset(skip).limit(limit).all()

    def search_work_orders_with_count(
        self,
        keyword: Optional[str] = None,
        status: Optional[WorkOrderStatus] = None,
        customer_id: Optional[int] = None,
        product_part_id: Optional[int] = None,
        priority: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[WorkOrder], int]:
        """작업지시서 검색 + 총 개수"""
        query = self.db.query(WorkOrder).options(
            joinedload(WorkOrder.product_part),
            joinedload(WorkOrder.customer)
        )

        # 키워드 검색
        if keyword:
            columns = [WorkOrder.wo_number, WorkOrder.customer_order_no, WorkOrder.remarks]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 상태 필터
        if status:
            query = query.filter(WorkOrder.status == status.value)

        # 고객사 필터
        if customer_id:
            query = query.filter(WorkOrder.customer_id == customer_id)

        # 완제품 필터
        if product_part_id:
            query = query.filter(WorkOrder.product_part_id == product_part_id)

        # 우선순위 필터
        if priority is not None:
            query = query.filter(WorkOrder.priority == priority)

        # 날짜 범위 필터
        if from_date:
            query = query.filter(func.date(WorkOrder.received_date) >= from_date)
        if to_date:
            query = query.filter(func.date(WorkOrder.received_date) <= to_date)

        # 총 개수
        total = query.count()

        # 정렬
        if hasattr(WorkOrder, order_by):
            order_column = getattr(WorkOrder, order_by)
        else:
            order_column = WorkOrder.created_at

        query = query.order_by(desc(order_column) if order_desc else asc(order_column))

        items = query.offset(skip).limit(limit).all()

        return items, total

    # ==================== 번호 생성 ====================

    def get_last_wo_number_for_date(self, date_prefix: str) -> Optional[str]:
        """특정 날짜의 마지막 작업지시서 번호 조회"""
        return self.db.query(WorkOrder.wo_number).filter(
            WorkOrder.wo_number.like(f"{date_prefix}%")
        ).order_by(WorkOrder.wo_number.desc()).first()


class WorkOrderItemRepository(BaseRepository[WorkOrderItem, WorkOrderItemCreate, WorkOrderItemCreate]):
    """
    작업지시서 항목 Repository

    작업지시서 항목 관련 데이터베이스 접근 로직을 제공합니다.
    """

    def __init__(self, db: Session):
        super().__init__(db, WorkOrderItem)

    # ==================== 조회 ====================

    def get_by_id_with_relations(self, id: int) -> Optional[WorkOrderItem]:
        """ID로 작업지시서 항목 조회 (관계 포함)"""
        return self.db.query(WorkOrderItem).options(
            joinedload(WorkOrderItem.part),
            joinedload(WorkOrderItem.unit)
        ).filter(WorkOrderItem.id == id).first()

    def get_by_work_order_id(self, work_order_id: int) -> List[WorkOrderItem]:
        """작업지시서 ID로 항목 목록 조회"""
        return self.db.query(WorkOrderItem).options(
            joinedload(WorkOrderItem.part),
            joinedload(WorkOrderItem.unit)
        ).filter(
            WorkOrderItem.work_order_id == work_order_id
        ).order_by(WorkOrderItem.bom_level, WorkOrderItem.sort_order).all()

    def delete_by_work_order_id(self, work_order_id: int) -> int:
        """작업지시서 ID로 항목 전체 삭제"""
        count = self.db.query(WorkOrderItem).filter(
            WorkOrderItem.work_order_id == work_order_id
        ).delete()
        self.db.commit()
        return count
