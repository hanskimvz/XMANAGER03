"""
Business Partner Repository
거래처 데이터 접근 로직을 처리합니다.
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.repositories.base import BaseRepository, build_keyword_filter
from app.models.business_partner import BusinessPartner
from app.schemas.business_partner import BusinessPartnerCreate, BusinessPartnerUpdate


class BusinessPartnerRepository(BaseRepository[BusinessPartner, BusinessPartnerCreate, BusinessPartnerUpdate]):
    """
    거래처 Repository

    거래처 테이블의 데이터 접근 로직을 캡슐화합니다.
    """

    def __init__(self, db: Session):
        super().__init__(db, BusinessPartner)

    # ==================== 거래처 전용 조회 ====================

    def get_by_code(self, partner_code: str) -> Optional[BusinessPartner]:
        """
        거래처 코드로 조회

        Args:
            partner_code: 거래처 코드

        Returns:
            BusinessPartner 또는 None
        """
        return self.db.query(BusinessPartner).filter(
            BusinessPartner.partner_code == partner_code
        ).first()

    def exists_by_code(self, partner_code: str) -> bool:
        """거래처 코드 존재 여부 확인"""
        return self.db.query(BusinessPartner).filter(
            BusinessPartner.partner_code == partner_code
        ).count() > 0

    def get_by_business_number(self, business_number: str) -> Optional[BusinessPartner]:
        """
        사업자등록번호로 조회

        Args:
            business_number: 사업자등록번호

        Returns:
            BusinessPartner 또는 None
        """
        return self.db.query(BusinessPartner).filter(
            BusinessPartner.business_number == business_number
        ).first()

    # ==================== 유형별 조회 ====================

    def get_suppliers(
        self,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[BusinessPartner]:
        """
        공급업체 목록 조회

        Args:
            is_active: 활성 상태 필터
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            BusinessPartner 리스트
        """
        query = self.db.query(BusinessPartner).filter(
            BusinessPartner.is_supplier == True
        )

        if is_active is not None:
            query = query.filter(BusinessPartner.is_active == is_active)

        return query.order_by(BusinessPartner.partner_name).offset(skip).limit(limit).all()

    def get_customers(
        self,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[BusinessPartner]:
        """
        고객사 목록 조회

        Args:
            is_active: 활성 상태 필터
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            BusinessPartner 리스트
        """
        query = self.db.query(BusinessPartner).filter(
            BusinessPartner.is_customer == True
        )

        if is_active is not None:
            query = query.filter(BusinessPartner.is_active == is_active)

        return query.order_by(BusinessPartner.partner_name).offset(skip).limit(limit).all()

    def count_suppliers(self, is_active: Optional[bool] = True) -> int:
        """공급업체 수 조회"""
        query = self.db.query(BusinessPartner).filter(
            BusinessPartner.is_supplier == True
        )
        if is_active is not None:
            query = query.filter(BusinessPartner.is_active == is_active)
        return query.count()

    def count_customers(self, is_active: Optional[bool] = True) -> int:
        """고객사 수 조회"""
        query = self.db.query(BusinessPartner).filter(
            BusinessPartner.is_customer == True
        )
        if is_active is not None:
            query = query.filter(BusinessPartner.is_active == is_active)
        return query.count()

    # ==================== 거래처 검색 ====================

    def search_partners(
        self,
        keyword: Optional[str] = None,
        is_supplier: Optional[bool] = None,
        is_customer: Optional[bool] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "partner_name",
        order_desc: bool = False
    ) -> List[BusinessPartner]:
        """
        거래처 검색 (키워드 + 필터)

        Args:
            keyword: 검색 키워드 (거래처 코드, 거래처명)
            is_supplier: 공급업체 필터
            is_customer: 고객사 필터
            is_active: 활성 상태 필터
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수
            order_by: 정렬 기준 컬럼명
            order_desc: 내림차순 정렬 여부

        Returns:
            BusinessPartner 리스트
        """
        query = self.db.query(BusinessPartner)

        # 키워드 검색 (퍼지 검색)
        if keyword:
            columns = [BusinessPartner.partner_code, BusinessPartner.partner_name, BusinessPartner.partner_name_en, BusinessPartner.business_number]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 필터 적용
        query = self._apply_partner_filters(query, is_supplier, is_customer, is_active)

        # 정렬 적용
        if order_by and hasattr(BusinessPartner, order_by):
            column = getattr(BusinessPartner, order_by)
            query = query.order_by(desc(column) if order_desc else column)

        return query.offset(skip).limit(limit).all()

    def search_partners_with_count(
        self,
        keyword: Optional[str] = None,
        is_supplier: Optional[bool] = None,
        is_customer: Optional[bool] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "partner_name",
        order_desc: bool = False
    ) -> Tuple[List[BusinessPartner], int]:
        """
        거래처 검색 + 총 개수 반환

        Returns:
            (BusinessPartner 리스트, 총 개수) 튜플
        """
        query = self.db.query(BusinessPartner)

        if keyword:
            columns = [BusinessPartner.partner_code, BusinessPartner.partner_name, BusinessPartner.partner_name_en, BusinessPartner.business_number]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        query = self._apply_partner_filters(query, is_supplier, is_customer, is_active)

        total = query.count()

        if order_by and hasattr(BusinessPartner, order_by):
            column = getattr(BusinessPartner, order_by)
            query = query.order_by(desc(column) if order_desc else column)

        items = query.offset(skip).limit(limit).all()

        return items, total

    def count_partners(
        self,
        keyword: Optional[str] = None,
        is_supplier: Optional[bool] = None,
        is_customer: Optional[bool] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """거래처 수 조회 (검색 조건 적용)"""
        query = self.db.query(BusinessPartner)

        if keyword:
            columns = [BusinessPartner.partner_code, BusinessPartner.partner_name, BusinessPartner.partner_name_en]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        query = self._apply_partner_filters(query, is_supplier, is_customer, is_active)

        return query.count()

    # ==================== 등급별 조회 ====================

    def get_by_grade(
        self,
        grade: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[BusinessPartner]:
        """
        등급별 거래처 조회

        Args:
            grade: 거래처 등급
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            BusinessPartner 리스트
        """
        return self.db.query(BusinessPartner).filter(
            BusinessPartner.grade == grade
        ).offset(skip).limit(limit).all()

    def get_by_credit_rating(
        self,
        credit_rating: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[BusinessPartner]:
        """
        신용등급별 거래처 조회

        Args:
            credit_rating: 신용등급
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            BusinessPartner 리스트
        """
        return self.db.query(BusinessPartner).filter(
            BusinessPartner.credit_rating == credit_rating
        ).offset(skip).limit(limit).all()

    # ==================== 내부 유틸리티 ====================

    def _apply_partner_filters(
        self,
        query,
        is_supplier: Optional[bool] = None,
        is_customer: Optional[bool] = None,
        is_active: Optional[bool] = None
    ):
        """거래처 필터 적용 (내부 메서드)"""
        if is_supplier is not None:
            query = query.filter(BusinessPartner.is_supplier == is_supplier)
        if is_customer is not None:
            query = query.filter(BusinessPartner.is_customer == is_customer)
        if is_active is not None:
            query = query.filter(BusinessPartner.is_active == is_active)

        return query
