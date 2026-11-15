"""
Base Service
모든 서비스의 기본 클래스를 정의합니다.

공통 CRUD 작업과 유틸리티 메서드를 제공합니다.
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel

from app.core.database import Base

# 타입 변수 정의
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    기본 서비스 클래스

    모든 서비스가 상속받아 사용합니다.
    공통 CRUD 작업을 제공하며, 필요시 오버라이드하여 사용합니다.

    사용 예시:
        class PartService(BaseService[Part, PartCreate, PartUpdate]):
            def __init__(self, db: Session):
                super().__init__(db, Part)
    """

    def __init__(self, db: Session, model: Type[ModelType]):
        """
        서비스 초기화

        Args:
            db: SQLAlchemy 세션
            model: 대상 모델 클래스
        """
        self.db = db
        self.model = model

    # ==================== 기본 CRUD ====================

    def get(self, id: int) -> Optional[ModelType]:
        """
        ID로 단일 레코드 조회

        Args:
            id: 레코드 ID

        Returns:
            모델 인스턴스 또는 None
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_or_raise(self, id: int) -> ModelType:
        """
        ID로 단일 레코드 조회 (없으면 예외 발생)

        Args:
            id: 레코드 ID

        Returns:
            모델 인스턴스

        Raises:
            ValueError: 레코드를 찾을 수 없는 경우
        """
        obj = self.get(id)
        if obj is None:
            raise ValueError(f"{self.model.__name__} with id {id} not found")
        return obj

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        전체 레코드 조회 (페이지네이션 지원)

        Args:
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수
            filters: 필터 조건 (컬럼명: 값)
            order_by: 정렬 기준 컬럼명
            order_desc: 내림차순 정렬 여부

        Returns:
            모델 인스턴스 리스트
        """
        query = self.db.query(self.model)

        # 필터 적용
        if filters:
            query = self._apply_filters(query, filters)

        # 정렬 적용
        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            query = query.order_by(column.desc() if order_desc else column)

        return query.offset(skip).limit(limit).all()

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        레코드 수 조회

        Args:
            filters: 필터 조건

        Returns:
            레코드 수
        """
        query = self.db.query(self.model)
        if filters:
            query = self._apply_filters(query, filters)
        return query.count()

    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        새 레코드 생성

        Args:
            obj_in: 생성할 데이터 (Pydantic 스키마)

        Returns:
            생성된 모델 인스턴스
        """
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(
        self,
        id: int,
        obj_in: UpdateSchemaType,
        exclude_unset: bool = True
    ) -> Optional[ModelType]:
        """
        레코드 수정

        Args:
            id: 수정할 레코드 ID
            obj_in: 수정할 데이터 (Pydantic 스키마)
            exclude_unset: 설정되지 않은 필드 제외 여부

        Returns:
            수정된 모델 인스턴스 또는 None
        """
        db_obj = self.get(id)
        if db_obj is None:
            return None

        if hasattr(obj_in, 'model_dump'):
            update_data = obj_in.model_dump(exclude_unset=exclude_unset)
        else:
            update_data = obj_in.dict(exclude_unset=exclude_unset)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> bool:
        """
        레코드 삭제

        Args:
            id: 삭제할 레코드 ID

        Returns:
            삭제 성공 여부
        """
        db_obj = self.get(id)
        if db_obj is None:
            return False

        self.db.delete(db_obj)
        self.db.commit()
        return True

    def soft_delete(self, id: int) -> Optional[ModelType]:
        """
        소프트 삭제 (is_active = False)

        Args:
            id: 삭제할 레코드 ID

        Returns:
            수정된 모델 인스턴스 또는 None
        """
        db_obj = self.get(id)
        if db_obj is None or not hasattr(db_obj, 'is_active'):
            return None

        db_obj.is_active = False
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    # ==================== 유틸리티 메서드 ====================

    def exists(self, id: int) -> bool:
        """레코드 존재 여부 확인"""
        return self.db.query(self.model).filter(self.model.id == id).count() > 0

    def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """
        특정 필드 값으로 레코드 조회

        Args:
            field: 필드명
            value: 필드 값

        Returns:
            모델 인스턴스 또는 None
        """
        if not hasattr(self.model, field):
            return None
        return self.db.query(self.model).filter(
            getattr(self.model, field) == value
        ).first()

    def get_all_by_field(
        self,
        field: str,
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        특정 필드 값으로 여러 레코드 조회

        Args:
            field: 필드명
            value: 필드 값
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            모델 인스턴스 리스트
        """
        if not hasattr(self.model, field):
            return []
        return self.db.query(self.model).filter(
            getattr(self.model, field) == value
        ).offset(skip).limit(limit).all()

    def get_active(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        활성화된 레코드만 조회 (is_active = True)

        Args:
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            모델 인스턴스 리스트
        """
        if not hasattr(self.model, 'is_active'):
            return self.get_all(skip=skip, limit=limit)

        return self.db.query(self.model).filter(
            self.model.is_active == True
        ).offset(skip).limit(limit).all()

    def bulk_create(self, objects_in: List[CreateSchemaType]) -> List[ModelType]:
        """
        다건 레코드 생성

        Args:
            objects_in: 생성할 데이터 리스트

        Returns:
            생성된 모델 인스턴스 리스트
        """
        db_objects = []
        for obj_in in objects_in:
            obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
            db_obj = self.model(**obj_data)
            self.db.add(db_obj)
            db_objects.append(db_obj)

        self.db.commit()
        for db_obj in db_objects:
            self.db.refresh(db_obj)
        return db_objects

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """
        필터 조건 적용 (내부 메서드)

        Args:
            query: SQLAlchemy 쿼리
            filters: 필터 조건

        Returns:
            필터가 적용된 쿼리
        """
        for field, value in filters.items():
            if value is None:
                continue
            if not hasattr(self.model, field):
                continue
            query = query.filter(getattr(self.model, field) == value)
        return query

    def search(
        self,
        keyword: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        키워드 검색 (여러 필드에서 LIKE 검색)

        Args:
            keyword: 검색 키워드
            search_fields: 검색할 필드 리스트
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            모델 인스턴스 리스트
        """
        if not keyword or not search_fields:
            return self.get_all(skip=skip, limit=limit)

        conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                conditions.append(column.ilike(f"%{keyword}%"))

        if not conditions:
            return []

        return self.db.query(self.model).filter(
            or_(*conditions)
        ).offset(skip).limit(limit).all()
