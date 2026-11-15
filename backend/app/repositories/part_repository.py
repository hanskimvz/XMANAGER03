"""
Part Repository (v0.10.0)
부품 데이터 접근 로직을 처리합니다.

v0.10.0: 품번 구조 변경 (부품코드 관리기준서 적용)
- 신규 필터: product_line_id, part_group_id, development_type_id, part_type_id, drawing_type_id
- Legacy 필터 유지 (하위 호환성)
"""

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.repositories.base import BaseRepository, build_keyword_filter
from app.models.parts import Part
from app.schemas.parts import PartCreate, PartUpdate


class PartRepository(BaseRepository[Part, PartCreate, PartUpdate]):
    """
    부품 Repository (v0.10.0)

    부품 테이블의 데이터 접근 로직을 캡슐화합니다.
    """

    def __init__(self, db: Session):
        super().__init__(db, Part)

    # ==================== 부품 전용 조회 ====================

    def get_by_part_number(self, part_number: str) -> Optional[Part]:
        """
        품번으로 부품 조회

        Args:
            part_number: 품번 (시스템용)

        Returns:
            Part 또는 None
        """
        return self.db.query(Part).filter(Part.part_number == part_number).first()

    def get_by_part_number_display(self, part_number_display: str) -> Optional[Part]:
        """
        표시용 품번으로 부품 조회

        Args:
            part_number_display: 표시용 품번

        Returns:
            Part 또는 None
        """
        return self.db.query(Part).filter(
            Part.part_number_display == part_number_display
        ).first()

    def exists_by_part_number(self, part_number: str) -> bool:
        """품번 존재 여부 확인"""
        return self.db.query(Part).filter(Part.part_number == part_number).count() > 0

    # ==================== 부품 검색 ====================

    def search_parts(
        self,
        keyword: Optional[str] = None,
        # 신규 필터 (v0.10.0)
        product_line_id: Optional[int] = None,
        part_group_id: Optional[int] = None,
        development_type_id: Optional[int] = None,
        part_type_id: Optional[int] = None,
        drawing_type_id: Optional[int] = None,
        # Legacy 필터 (하위 호환성)
        major_category_id: Optional[int] = None,
        middle_category_id: Optional[int] = None,
        minor_category_id: Optional[int] = None,
        # 공통 필터
        level_id: Optional[int] = None,
        material_id: Optional[int] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[Part]:
        """
        부품 검색 (키워드 + 필터)

        Args:
            keyword: 검색 키워드 (품번, 부품명)
            product_line_id: 대분류/제품라인 필터 (v0.10.0)
            part_group_id: 소분류/품목군 필터 (v0.10.0)
            development_type_id: 개발구분 필터 (v0.10.0)
            part_type_id: 부품유형 필터 (v0.10.0)
            drawing_type_id: 도면여부 필터 (v0.10.0)
            major_category_id: [Legacy] 대분류 필터
            middle_category_id: [Legacy] 중분류 필터
            minor_category_id: [Legacy] 소분류 필터
            level_id: 레벨 필터
            material_id: 재질 필터
            status: 상태 필터
            is_active: 사용여부 필터
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수
            order_by: 정렬 기준 컬럼명
            order_desc: 내림차순 정렬 여부

        Returns:
            Part 리스트
        """
        query = self.db.query(Part)

        # 키워드 검색
        if keyword:
            columns = [Part.part_number, Part.part_number_display, Part.part_name, Part.part_name_en, Part.description]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 필터 적용
        query = self._apply_part_filters(
            query,
            product_line_id=product_line_id,
            part_group_id=part_group_id,
            development_type_id=development_type_id,
            part_type_id=part_type_id,
            drawing_type_id=drawing_type_id,
            major_category_id=major_category_id,
            middle_category_id=middle_category_id,
            minor_category_id=minor_category_id,
            level_id=level_id,
            material_id=material_id,
            status=status,
            is_active=is_active
        )

        # 정렬 적용
        if order_by and hasattr(Part, order_by):
            column = getattr(Part, order_by)
            query = query.order_by(desc(column) if order_desc else column)

        return query.offset(skip).limit(limit).all()

    def search_parts_with_count(
        self,
        keyword: Optional[str] = None,
        # 신규 필터 (v0.10.0)
        product_line_id: Optional[int] = None,
        part_group_id: Optional[int] = None,
        development_type_id: Optional[int] = None,
        development_type_ids: Optional[List[int]] = None,  # v0.12.0: 다중 선택
        part_type_id: Optional[int] = None,
        drawing_type_id: Optional[int] = None,
        # Legacy 필터 (하위 호환성)
        major_category_id: Optional[int] = None,
        middle_category_id: Optional[int] = None,
        minor_category_id: Optional[int] = None,
        # 공통 필터
        level_id: Optional[int] = None,
        level_ids: Optional[List[int]] = None,  # 다중 선택
        material_id: Optional[int] = None,
        treatment_id: Optional[int] = None,  # v0.12.0: 후처리 필터
        procurement_type_id: Optional[int] = None,  # v0.12.0: 조달유형 필터
        unit_id: Optional[int] = None,  # v0.12.0: 단위 필터
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        classified: Optional[bool] = None,  # 분류상태: None=전체, True=분류됨, False=미분류
        # 고급 필터: 미입력 필드 검색
        missing_fields: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Part], int]:
        """
        부품 검색 + 총 개수 반환

        Args:
            missing_fields: 미입력 필드 목록 (예: ['supplier_id', 'part_name_en'])
                - supplier_id: 공급업체 미등록
                - part_name_en: 영문 부품명 미등록
                - standard_price: 기준단가 미등록 (0 또는 NULL)
                - specification: 규격 미등록
                - unit_id: 단위 미등록
                - material_id: 재질 미등록
                - treatment_id: 후처리 미등록
                - drawing_file: 도면 미등록
                - photo_file: 사진 미등록

        Returns:
            (Part 리스트, 총 개수) 튜플
        """
        query = self.db.query(Part)

        if keyword:
            columns = [Part.part_number, Part.part_number_display, Part.part_name, Part.part_name_en, Part.description]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        query = self._apply_part_filters(
            query,
            product_line_id=product_line_id,
            part_group_id=part_group_id,
            development_type_id=development_type_id,
            part_type_id=part_type_id,
            drawing_type_id=drawing_type_id,
            major_category_id=major_category_id,
            middle_category_id=middle_category_id,
            minor_category_id=minor_category_id,
            level_id=level_id,
            material_id=material_id,
            treatment_id=treatment_id,
            procurement_type_id=procurement_type_id,
            unit_id=unit_id,
            status=status,
            is_active=is_active
        )

        # 분류상태 필터(미분류 부품 필터링): None=전체, True=분류됨만, False=미분류만
        if classified is not None:
            query = query.filter(Part.is_classified == classified)

        # 다중 레벨 필터 (level_ids)
        # - 미분류만(classified=False): 미분류는 레벨이 없으므로 레벨 필터 무시
        # - 분류됨만(classified=True): 레벨 필터 엄격 적용
        # - 전체(None): 미분류(level_id=NULL)도 함께 노출(신규 미분류가 검색에서 사라지지 않게)
        if level_ids and len(level_ids) > 0 and classified is not False:
            if classified is True:
                query = query.filter(Part.level_id.in_(level_ids))
            else:
                query = query.filter(or_(Part.level_id.in_(level_ids), Part.level_id.is_(None)))

        # v0.12.0: 다중 개발구분 필터 (development_type_ids)
        if development_type_ids and len(development_type_ids) > 0:
            query = query.filter(Part.development_type_id.in_(development_type_ids))

        # 고급 필터: 미입력 필드 검색
        if missing_fields:
            for field in missing_fields:
                if field == 'supplier_id':
                    query = query.filter(Part.supplier_id.is_(None))
                elif field == 'part_name_en':
                    query = query.filter(or_(Part.part_name_en.is_(None), Part.part_name_en == ''))
                elif field == 'standard_price':
                    query = query.filter(or_(Part.standard_price.is_(None), Part.standard_price == 0))
                elif field == 'specification':
                    query = query.filter(or_(Part.specification.is_(None), Part.specification == ''))
                elif field == 'unit_id':
                    query = query.filter(Part.unit_id.is_(None))
                elif field == 'material_id':
                    query = query.filter(Part.material_id.is_(None))
                elif field == 'treatment_id':
                    query = query.filter(Part.treatment_id.is_(None))
                elif field == 'drawing_file':
                    query = query.filter(or_(Part.drawing_file.is_(None), Part.drawing_file == ''))
                elif field == 'photo_file':
                    query = query.filter(or_(Part.photo_file.is_(None), Part.photo_file == ''))
                elif field == 'description':
                    query = query.filter(or_(Part.description.is_(None), Part.description == ''))
                elif field == 'procurement_type_id':
                    query = query.filter(Part.procurement_type_id.is_(None))
                elif field == 'development_type_id':
                    query = query.filter(Part.development_type_id.is_(None))

        total = query.count()

        if order_by and hasattr(Part, order_by):
            column = getattr(Part, order_by)
            query = query.order_by(desc(column) if order_desc else column)

        items = query.offset(skip).limit(limit).all()

        return items, total

    def count_parts(
        self,
        keyword: Optional[str] = None,
        # 신규 필터 (v0.10.0)
        product_line_id: Optional[int] = None,
        part_group_id: Optional[int] = None,
        development_type_id: Optional[int] = None,
        part_type_id: Optional[int] = None,
        drawing_type_id: Optional[int] = None,
        # Legacy 필터 (하위 호환성)
        major_category_id: Optional[int] = None,
        middle_category_id: Optional[int] = None,
        minor_category_id: Optional[int] = None,
        # 공통 필터
        level_id: Optional[int] = None,
        material_id: Optional[int] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """부품 수 조회 (검색 조건 적용)"""
        query = self.db.query(Part)

        if keyword:
            columns = [Part.part_number, Part.part_number_display, Part.part_name, Part.part_name_en, Part.description]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        query = self._apply_part_filters(
            query,
            product_line_id=product_line_id,
            part_group_id=part_group_id,
            development_type_id=development_type_id,
            part_type_id=part_type_id,
            drawing_type_id=drawing_type_id,
            major_category_id=major_category_id,
            middle_category_id=middle_category_id,
            minor_category_id=minor_category_id,
            level_id=level_id,
            material_id=material_id,
            status=status,
            is_active=is_active
        )

        return query.count()

    # ==================== 분류별 조회 ====================

    def get_by_category(
        self,
        major_category_id: Optional[int] = None,
        middle_category_id: Optional[int] = None,
        minor_category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Part]:
        """
        분류별 부품 조회

        Args:
            major_category_id: 대분류 ID
            middle_category_id: 중분류 ID
            minor_category_id: 소분류 ID
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            Part 리스트
        """
        query = self.db.query(Part)

        if major_category_id is not None:
            query = query.filter(Part.major_category_id == major_category_id)
        if middle_category_id is not None:
            query = query.filter(Part.middle_category_id == middle_category_id)
        if minor_category_id is not None:
            query = query.filter(Part.minor_category_id == minor_category_id)

        return query.offset(skip).limit(limit).all()

    def get_by_supplier(
        self,
        supplier_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Part]:
        """
        공급업체별 부품 조회

        Args:
            supplier_id: 공급업체 ID
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            Part 리스트
        """
        return self.db.query(Part).filter(
            Part.supplier_id == supplier_id
        ).offset(skip).limit(limit).all()

    # ==================== 상태별 조회 ====================

    def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Part]:
        """
        상태별 부품 조회

        Args:
            status: 상태 (ACTIVE/INACTIVE/OBSOLETE)
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            Part 리스트
        """
        return self.db.query(Part).filter(
            Part.status == status
        ).offset(skip).limit(limit).all()

    def get_by_approval_status(
        self,
        approval_status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Part]:
        """
        승인 상태별 부품 조회

        Args:
            approval_status: 승인 상태 (DRAFT/PENDING/APPROVED/REJECTED)
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            Part 리스트
        """
        return self.db.query(Part).filter(
            Part.approval_status == approval_status
        ).offset(skip).limit(limit).all()

    def get_pending_approval(self, skip: int = 0, limit: int = 100) -> List[Part]:
        """승인 대기 중인 부품 조회"""
        return self.get_by_approval_status("PENDING", skip, limit)

    # ==================== 최근 품번 조회 ====================

    def get_last_part_number_by_prefix(self, prefix: str) -> Optional[str]:
        """
        특정 프리픽스로 시작하는 마지막 품번 조회

        Args:
            prefix: 품번 프리픽스

        Returns:
            마지막 품번 또는 None
        """
        result = self.db.query(Part.part_number).filter(
            Part.part_number.like(f"{prefix}%")
        ).order_by(desc(Part.part_number)).first()

        return result[0] if result else None

    # ==================== 내부 유틸리티 ====================

    def _apply_part_filters(
        self,
        query,
        # 신규 필터 (v0.10.0)
        product_line_id: Optional[int] = None,
        part_group_id: Optional[int] = None,
        development_type_id: Optional[int] = None,
        part_type_id: Optional[int] = None,
        drawing_type_id: Optional[int] = None,
        # Legacy 필터 (하위 호환성)
        major_category_id: Optional[int] = None,
        middle_category_id: Optional[int] = None,
        minor_category_id: Optional[int] = None,
        # 공통 필터
        level_id: Optional[int] = None,
        material_id: Optional[int] = None,
        treatment_id: Optional[int] = None,  # v0.12.0: 후처리 필터
        procurement_type_id: Optional[int] = None,  # v0.12.0: 조달유형 필터
        unit_id: Optional[int] = None,  # v0.12.0: 단위 필터
        status: Optional[str] = None,
        is_active: Optional[bool] = None
    ):
        """부품 필터 적용 (내부 메서드)"""
        # 신규 필터 (v0.10.0)
        if product_line_id is not None:
            query = query.filter(Part.product_line_id == product_line_id)
        if part_group_id is not None:
            query = query.filter(Part.part_group_id == part_group_id)
        if development_type_id is not None:
            query = query.filter(Part.development_type_id == development_type_id)
        if part_type_id is not None:
            # 부품유형은 M:N 관계이므로 join 필요
            query = query.filter(Part.part_types.any(id=part_type_id))
        if drawing_type_id is not None:
            query = query.filter(Part.drawing_type_id == drawing_type_id)

        # Legacy 필터 (하위 호환성)
        if major_category_id is not None:
            query = query.filter(Part.major_category_id == major_category_id)
        if middle_category_id is not None:
            query = query.filter(Part.middle_category_id == middle_category_id)
        if minor_category_id is not None:
            query = query.filter(Part.minor_category_id == minor_category_id)

        # 공통 필터
        if level_id is not None:
            query = query.filter(Part.level_id == level_id)
        if material_id is not None:
            query = query.filter(Part.material_id == material_id)
        # v0.12.0: 추가 필터
        if treatment_id is not None:
            query = query.filter(Part.treatment_id == treatment_id)
        if procurement_type_id is not None:
            query = query.filter(Part.procurement_type_id == procurement_type_id)
        if unit_id is not None:
            query = query.filter(Part.unit_id == unit_id)
        if status is not None:
            query = query.filter(Part.status == status)
        if is_active is not None:
            query = query.filter(Part.is_active == is_active)

        return query
