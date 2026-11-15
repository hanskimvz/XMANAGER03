"""
생산 요청서 Repository
데이터베이스 접근 로직을 캡슐화합니다.

v0.20.0: 생산 요청서 기능 추가
v0.22.0: 다중 제품 지원
"""

from typing import Optional, List, Tuple
from datetime import date
from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy import desc, asc, or_

from app.repositories.base import BaseRepository, build_keyword_filter
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.schemas.production_request import ProductionRequestCreate, ProductionRequestUpdate


class ProductionRequestRepository(BaseRepository[ProductionRequest, ProductionRequestCreate, ProductionRequestUpdate]):
    """생산 요청서 Repository"""

    def __init__(self, db: Session):
        super().__init__(db, ProductionRequest)

    def get_by_id_with_relations(self, id: int) -> Optional[ProductionRequest]:
        """ID로 생산 요청서 조회 (관계 데이터 포함)"""
        return self.db.query(ProductionRequest).options(
            joinedload(ProductionRequest.customer),
            joinedload(ProductionRequest.product_part),
            joinedload(ProductionRequest.work_orders),
            joinedload(ProductionRequest.items).joinedload(ProductionRequestItem.product_part)  # v0.22.0
        ).filter(ProductionRequest.id == id).first()

    def get_by_request_number(self, request_number: str) -> Optional[ProductionRequest]:
        """요청서 번호로 조회"""
        return self.db.query(ProductionRequest).filter(
            ProductionRequest.request_number == request_number
        ).first()

    def get_by_request_number_with_relations(self, request_number: str) -> Optional[ProductionRequest]:
        """요청서 번호로 조회 (관계 데이터 포함)"""
        return self.db.query(ProductionRequest).options(
            joinedload(ProductionRequest.customer),
            joinedload(ProductionRequest.product_part),
            joinedload(ProductionRequest.work_orders),
            joinedload(ProductionRequest.items).joinedload(ProductionRequestItem.product_part)  # v0.22.0
        ).filter(ProductionRequest.request_number == request_number).first()

    def search_production_requests(
        self,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        priority: Optional[int] = None,
        is_draft: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[ProductionRequest]:
        """생산 요청서 검색"""
        query = self.db.query(ProductionRequest).options(
            joinedload(ProductionRequest.customer),
            joinedload(ProductionRequest.product_part),
            subqueryload(ProductionRequest.work_orders),
            subqueryload(ProductionRequest.items).joinedload(ProductionRequestItem.product_part)  # v0.22.0
        )

        # 키워드 검색
        if keyword:
            columns = [ProductionRequest.request_number, ProductionRequest.pi_number, ProductionRequest.customer_order_no, ProductionRequest.remarks]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 상태 필터
        if status:
            _statuses = [s.strip() for s in str(status).split(",") if s.strip()]
            query = query.filter(ProductionRequest.status.in_(_statuses))

        # 초안 필터(v0.87.0): False=초안 제외(생산팀), True=초안만(영업), None=전체
        if is_draft is not None:
            query = query.filter(ProductionRequest.is_draft == is_draft)

        # 고객사 필터
        if customer_id:
            query = query.filter(ProductionRequest.customer_id == customer_id)

        # 우선순위 필터
        if priority is not None:
            query = query.filter(ProductionRequest.priority == priority)

        # 날짜 필터 (요청일 기준)
        if from_date:
            query = query.filter(ProductionRequest.requested_at >= from_date)
        if to_date:
            query = query.filter(ProductionRequest.requested_at <= to_date)

        # 정렬
        if hasattr(ProductionRequest, order_by):
            column = getattr(ProductionRequest, order_by)
            query = query.order_by(desc(column) if order_desc else asc(column))

        return query.offset(skip).limit(limit).all()

    def search_production_requests_with_count(
        self,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        priority: Optional[int] = None,
        is_draft: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[ProductionRequest], int]:
        """생산 요청서 검색 + 총 개수"""
        query = self.db.query(ProductionRequest)

        # 키워드 검색
        if keyword:
            columns = [ProductionRequest.request_number, ProductionRequest.pi_number, ProductionRequest.customer_order_no, ProductionRequest.remarks]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 상태 필터
        if status:
            _statuses = [s.strip() for s in str(status).split(",") if s.strip()]
            query = query.filter(ProductionRequest.status.in_(_statuses))

        # 초안 필터(v0.87.0): False=초안 제외(생산팀), True=초안만(영업), None=전체
        if is_draft is not None:
            query = query.filter(ProductionRequest.is_draft == is_draft)

        # 고객사 필터
        if customer_id:
            query = query.filter(ProductionRequest.customer_id == customer_id)

        # 우선순위 필터
        if priority is not None:
            query = query.filter(ProductionRequest.priority == priority)

        # 날짜 필터
        if from_date:
            query = query.filter(ProductionRequest.requested_at >= from_date)
        if to_date:
            query = query.filter(ProductionRequest.requested_at <= to_date)

        # 총 개수
        total = query.count()

        # 관계 로딩 및 정렬
        query = query.options(
            joinedload(ProductionRequest.customer),
            joinedload(ProductionRequest.product_part),
            subqueryload(ProductionRequest.work_orders),
            subqueryload(ProductionRequest.items).joinedload(ProductionRequestItem.product_part)  # v0.22.0
        )

        if hasattr(ProductionRequest, order_by):
            column = getattr(ProductionRequest, order_by)
            query = query.order_by(desc(column) if order_desc else asc(column))

        items = query.offset(skip).limit(limit).all()

        return items, total

    def get_pending_requests(self, skip: int = 0, limit: int = 50) -> List[ProductionRequest]:
        """대기 중인 요청서 조회 (REQUESTED 상태)"""
        return self.db.query(ProductionRequest).options(
            joinedload(ProductionRequest.customer),
            joinedload(ProductionRequest.product_part),
            subqueryload(ProductionRequest.items).joinedload(ProductionRequestItem.product_part)  # v0.22.0
        ).filter(
            ProductionRequest.status == "REQUESTED"
        ).order_by(
            desc(ProductionRequest.priority),  # 우선순위 높은 순
            asc(ProductionRequest.due_date),   # 납기 빠른 순
            asc(ProductionRequest.requested_at)  # 요청일 빠른 순
        ).offset(skip).limit(limit).all()

    def get_pending_requests_count(self) -> int:
        """대기 중인 요청서 개수"""
        return self.db.query(ProductionRequest).filter(
            ProductionRequest.status == "REQUESTED"
        ).count()
