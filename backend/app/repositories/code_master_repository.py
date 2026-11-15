"""
Code Master Repository
코드 마스터 데이터 접근 로직을 처리합니다.

10개의 코드 테이블을 통합 관리합니다.
"""

from typing import Optional, List, Dict, Any, Type, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.core.database import Base
from app.models.code_master import (
    # 신규 코드 테이블 (v0.10.0)
    ProductLine,
    PartGroup,
    DevelopmentType,
    PartType,
    DrawingType,
    # Legacy 코드 테이블
    MajorCategory,
    MiddleCategory,
    MinorCategory,
    SubCategory,
    ItemCode,
    Material,
    Treatment,
    Level,
    ProcurementType,
    SupplierType,
    Unit,
)


# 코드 테이블 타입 매핑
CODE_TABLES: Dict[str, Type[Base]] = {
    # 신규 코드 테이블 (v0.10.0)
    "product_line": ProductLine,
    "product-lines": ProductLine,
    "part_group": PartGroup,
    "part-groups": PartGroup,
    "development_type": DevelopmentType,
    "development-types": DevelopmentType,
    "part_type": PartType,
    "part-types": PartType,
    "drawing_type": DrawingType,
    "drawing-types": DrawingType,
    # Legacy 코드 테이블
    "major_category": MajorCategory,
    "major-categories": MajorCategory,
    "middle_category": MiddleCategory,
    "middle-categories": MiddleCategory,
    "minor_category": MinorCategory,
    "minor-categories": MinorCategory,
    "sub_category": SubCategory,
    "sub-categories": SubCategory,
    "item_code": ItemCode,
    "item-codes": ItemCode,
    "material": Material,
    "materials": Material,
    "treatment": Treatment,
    "treatments": Treatment,
    "level": Level,
    "levels": Level,
    "procurement_type": ProcurementType,
    "procurement-types": ProcurementType,
    "supplier_type": SupplierType,
    "supplier-types": SupplierType,
    "unit": Unit,
    "units": Unit,
}

# 테이블 한글 표시명
TABLE_DISPLAY_NAMES: Dict[str, str] = {
    # 신규 코드 테이블 (v0.10.0)
    "product_line": "제품라인",
    "product-lines": "제품라인",
    "part_group": "품목군",
    "part-groups": "품목군",
    "development_type": "개발구분",
    "development-types": "개발구분",
    "part_type": "부품유형",
    "part-types": "부품유형",
    "drawing_type": "도면여부",
    "drawing-types": "도면여부",
    # Legacy 코드 테이블
    "major_category": "대분류",
    "major-categories": "대분류",
    "middle_category": "중분류",
    "middle-categories": "중분류",
    "minor_category": "소분류",
    "minor-categories": "소분류",
    "sub_category": "세분류",
    "sub-categories": "세분류",
    "item_code": "품목코드",
    "item-codes": "품목코드",
    "material": "재질",
    "materials": "재질",
    "treatment": "후처리",
    "treatments": "후처리",
    "level": "레벨",
    "levels": "레벨",
    "procurement_type": "조달구분",
    "procurement-types": "조달구분",
    "supplier_type": "공급업체 구분",
    "supplier-types": "공급업체 구분",
    "unit": "단위",
    "units": "단위",
}


class CodeMasterRepository:
    """
    코드 마스터 Repository

    모든 코드 테이블에 대한 통합 데이터 접근 로직을 제공합니다.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== 유틸리티 ====================

    def get_model(self, table_name: str) -> Optional[Type[Base]]:
        """
        테이블명으로 모델 클래스 조회

        Args:
            table_name: 테이블명 (snake_case 또는 kebab-case)

        Returns:
            모델 클래스 또는 None
        """
        return CODE_TABLES.get(table_name)

    def get_display_name(self, table_name: str) -> str:
        """
        테이블명의 한글 표시명 조회

        Args:
            table_name: 테이블명

        Returns:
            한글 표시명
        """
        return TABLE_DISPLAY_NAMES.get(table_name, table_name)

    def is_valid_table(self, table_name: str) -> bool:
        """테이블명 유효성 검사"""
        return table_name in CODE_TABLES

    # ==================== 기본 조회 ====================

    def get_by_id(self, table_name: str, id: int) -> Optional[Base]:
        """
        ID로 코드 조회

        Args:
            table_name: 테이블명
            id: 레코드 ID

        Returns:
            코드 인스턴스 또는 None
        """
        model = self.get_model(table_name)
        if not model:
            return None
        return self.db.query(model).filter(model.id == id).first()

    def get_by_code(self, table_name: str, code: str) -> Optional[Base]:
        """
        코드값으로 조회

        Args:
            table_name: 테이블명
            code: 코드값

        Returns:
            코드 인스턴스 또는 None
        """
        model = self.get_model(table_name)
        if not model:
            return None
        return self.db.query(model).filter(model.code == code).first()

    def exists_by_code(self, table_name: str, code: str) -> bool:
        """코드값 존재 여부 확인"""
        model = self.get_model(table_name)
        if not model:
            return False
        return self.db.query(model).filter(model.code == code).count() > 0

    def exists_by_id(self, table_name: str, id: int) -> bool:
        """ID 존재 여부 확인"""
        model = self.get_model(table_name)
        if not model:
            return False
        return self.db.query(model).filter(model.id == id).count() > 0

    # ==================== 목록 조회 ====================

    def get_all(
        self,
        table_name: str,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "sort_order"
    ) -> List[Base]:
        """
        전체 코드 목록 조회

        Args:
            table_name: 테이블명
            is_active: 활성 여부 필터
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수
            order_by: 정렬 기준 컬럼명

        Returns:
            코드 리스트
        """
        model = self.get_model(table_name)
        if not model:
            return []

        query = self.db.query(model)

        if is_active is not None:
            query = query.filter(model.is_active == is_active)

        # 정렬
        if hasattr(model, order_by):
            query = query.order_by(getattr(model, order_by))
        if order_by != "code" and hasattr(model, "code"):
            query = query.order_by(model.code)

        return query.offset(skip).limit(limit).all()

    def get_all_with_count(
        self,
        table_name: str,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Base], int]:
        """
        전체 코드 목록 조회 + 총 개수 반환

        Returns:
            (코드 리스트, 총 개수) 튜플
        """
        model = self.get_model(table_name)
        if not model:
            return [], 0

        query = self.db.query(model)

        if is_active is not None:
            query = query.filter(model.is_active == is_active)

        total = query.count()
        items = query.order_by(model.sort_order, model.code).offset(skip).limit(limit).all()

        return items, total

    def get_active(self, table_name: str) -> List[Base]:
        """활성 코드만 조회"""
        return self.get_all(table_name, is_active=True)

    def count(self, table_name: str, is_active: Optional[bool] = None) -> int:
        """
        코드 수 조회

        Args:
            table_name: 테이블명
            is_active: 활성 여부 필터

        Returns:
            레코드 수
        """
        model = self.get_model(table_name)
        if not model:
            return 0

        query = self.db.query(model)

        if is_active is not None:
            query = query.filter(model.is_active == is_active)

        return query.count()

    # ==================== 생성 ====================

    def create(self, table_name: str, data: Dict[str, Any]) -> Optional[Base]:
        """
        코드 생성

        Args:
            table_name: 테이블명
            data: 생성할 데이터

        Returns:
            생성된 코드 인스턴스 또는 None
        """
        model = self.get_model(table_name)
        if not model:
            return None

        db_item = model(**data)
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def bulk_create(
        self,
        table_name: str,
        data_list: List[Dict[str, Any]]
    ) -> List[Base]:
        """
        다건 코드 생성

        Args:
            table_name: 테이블명
            data_list: 생성할 데이터 리스트

        Returns:
            생성된 코드 인스턴스 리스트
        """
        model = self.get_model(table_name)
        if not model:
            return []

        db_items = []
        for data in data_list:
            db_item = model(**data)
            self.db.add(db_item)
            db_items.append(db_item)

        self.db.commit()
        for item in db_items:
            self.db.refresh(item)

        return db_items

    # ==================== 수정 ====================

    def update(
        self,
        table_name: str,
        db_obj: Base,
        data: Dict[str, Any]
    ) -> Base:
        """
        코드 수정

        Args:
            table_name: 테이블명
            db_obj: 수정할 모델 인스턴스
            data: 수정할 데이터

        Returns:
            수정된 코드 인스턴스
        """
        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_by_id(
        self,
        table_name: str,
        id: int,
        data: Dict[str, Any]
    ) -> Optional[Base]:
        """
        ID로 코드 수정

        Args:
            table_name: 테이블명
            id: 레코드 ID
            data: 수정할 데이터

        Returns:
            수정된 코드 인스턴스 또는 None
        """
        db_obj = self.get_by_id(table_name, id)
        if not db_obj:
            return None
        return self.update(table_name, db_obj, data)

    def update_sort_orders(
        self,
        table_name: str,
        sort_orders: List[Dict[str, int]]
    ) -> List[Base]:
        """
        정렬순서 일괄 업데이트

        Args:
            table_name: 테이블명
            sort_orders: [{"id": 1, "sort_order": 1}, ...]

        Returns:
            수정된 코드 인스턴스 리스트
        """
        model = self.get_model(table_name)
        if not model:
            return []

        updated = []
        for item in sort_orders:
            db_item = self.db.query(model).filter(model.id == item['id']).first()
            if db_item:
                db_item.sort_order = item['sort_order']
                updated.append(db_item)

        self.db.commit()
        for item in updated:
            self.db.refresh(item)

        return updated

    # ==================== 삭제 ====================

    def delete(self, table_name: str, db_obj: Base) -> bool:
        """
        코드 삭제

        Args:
            table_name: 테이블명
            db_obj: 삭제할 모델 인스턴스

        Returns:
            삭제 성공 여부
        """
        self.db.delete(db_obj)
        self.db.commit()
        return True

    def delete_by_id(self, table_name: str, id: int) -> bool:
        """
        ID로 코드 삭제

        Args:
            table_name: 테이블명
            id: 레코드 ID

        Returns:
            삭제 성공 여부
        """
        db_obj = self.get_by_id(table_name, id)
        if not db_obj:
            return False
        return self.delete(table_name, db_obj)

    # ==================== 상태 관리 ====================

    def set_active(self, table_name: str, db_obj: Base, is_active: bool) -> Base:
        """
        활성 상태 설정

        Args:
            table_name: 테이블명
            db_obj: 모델 인스턴스
            is_active: 활성 여부

        Returns:
            수정된 코드 인스턴스
        """
        db_obj.is_active = is_active
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    # ==================== 특정 테이블 전용 메서드 ====================

    def get_level_by_bom_level(self, bom_level: int) -> Optional[Level]:
        """BOM 레벨로 Level 코드 조회"""
        return self.db.query(Level).filter(Level.bom_level == bom_level).first()

    def get_materials_by_type(self, material_type: str) -> List[Material]:
        """
        재질 타입별 조회

        Args:
            material_type: 재질 타입 (description에서 검색)

        Returns:
            Material 리스트
        """
        return self.db.query(Material).filter(
            Material.description.ilike(f"%{material_type}%"),
            Material.is_active == True
        ).order_by(Material.sort_order).all()

    # ==================== 통계 ====================

    def get_all_tables_summary(self) -> Dict[str, int]:
        """
        모든 코드 테이블의 요약 정보 조회

        Returns:
            테이블별 코드 수 딕셔너리
        """
        unique_tables = [
            "major_category",
            "middle_category",
            "minor_category",
            "sub_category",
            "item_code",
            "material",
            "treatment",
            "level",
            "procurement_type",
            "unit",
        ]

        summary = {}
        for table_name in unique_tables:
            summary[table_name] = self.count(table_name)

        return summary

    # ==================== 트랜잭션 ====================

    def flush(self) -> None:
        """세션 플러시"""
        self.db.flush()

    def commit(self) -> None:
        """세션 커밋"""
        self.db.commit()

    def rollback(self) -> None:
        """세션 롤백"""
        self.db.rollback()
