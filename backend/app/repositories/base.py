"""
Base Repository
모든 Repository의 기본 클래스를 정의합니다.

데이터베이스 접근 로직을 캡슐화하여 Service Layer에서 사용합니다.
"""

import re
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from pydantic import BaseModel

from app.core.database import Base


def build_keyword_filter(keyword: str, columns: list) -> list:
    """
    퍼지 키워드 검색 필터 생성

    - 공백으로 토큰 분리 후 AND 조합
    - 3자 이상 토큰: 문자 사이 와일드카드 삽입 (h15 → %h%1%5%)
    - 2자 이하 토큰: 기존 ILIKE 방식 (%ab%)
    - 하이픈, 대괄호 제거 후 패턴 생성

    Returns:
        SQLAlchemy filter 조건 리스트 (AND 조합용)
    """
    if not keyword or not keyword.strip():
        return []

    tokens = keyword.strip().split()
    and_conditions = []

    for token in tokens:
        if not token:
            continue

        # 하이픈, 대괄호 제거
        cleaned = re.sub(r'[-\[\]]', '', token).strip()
        if not cleaned:
            continue

        # ILIKE 특수문자 이스케이프
        cleaned = cleaned.replace('%', r'\%').replace('_', r'\_')

        if len(cleaned) >= 3:
            # 3자 이상: 문자 사이 와일드카드 삽입
            pattern = '%' + '%'.join(cleaned) + '%'
        else:
            # 2자 이하: 기존 방식
            pattern = f'%{cleaned}%'

        or_conditions = []
        for col in columns:
            or_conditions.append(col.ilike(pattern))

        if or_conditions:
            and_conditions.append(or_(*or_conditions))

    return and_conditions

# 타입 변수 정의
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    기본 Repository 클래스

    모든 Repository가 상속받아 사용합니다.
    데이터베이스 CRUD 작업을 추상화하여 제공합니다.

    사용 예시:
        class PartRepository(BaseRepository[Part, PartCreate, PartUpdate]):
            def __init__(self, db: Session):
                super().__init__(db, Part)
    """

    def __init__(self, db: Session, model: Type[ModelType]):
        """
        Repository 초기화

        Args:
            db: SQLAlchemy 세션
            model: 대상 모델 클래스
        """
        self.db = db
        self.model = model

    # ==================== 기본 조회 ====================

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        ID로 단일 레코드 조회

        Args:
            id: 레코드 ID

        Returns:
            모델 인스턴스 또는 None
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_by_ids(self, ids: List[int]) -> List[ModelType]:
        """
        여러 ID로 레코드 조회

        Args:
            ids: 레코드 ID 리스트

        Returns:
            모델 인스턴스 리스트
        """
        return self.db.query(self.model).filter(self.model.id.in_(ids)).all()

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

    def exists(self, id: int) -> bool:
        """레코드 존재 여부 확인"""
        return self.db.query(self.model).filter(self.model.id == id).count() > 0

    def exists_by_field(self, field: str, value: Any) -> bool:
        """특정 필드 값으로 레코드 존재 여부 확인"""
        if not hasattr(self.model, field):
            return False
        return self.db.query(self.model).filter(
            getattr(self.model, field) == value
        ).count() > 0

    # ==================== 목록 조회 ====================

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
            query = query.order_by(desc(column) if order_desc else asc(column))

        return query.offset(skip).limit(limit).all()

    def get_all_with_count(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> Tuple[List[ModelType], int]:
        """
        전체 레코드 조회 + 총 개수 반환 (페이지네이션)

        Args:
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수
            filters: 필터 조건
            order_by: 정렬 기준 컬럼명
            order_desc: 내림차순 정렬 여부

        Returns:
            (모델 인스턴스 리스트, 총 개수) 튜플
        """
        query = self.db.query(self.model)

        if filters:
            query = self._apply_filters(query, filters)

        total = query.count()

        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            query = query.order_by(desc(column) if order_desc else asc(column))

        items = query.offset(skip).limit(limit).all()

        return items, total

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

    # ==================== 검색 ====================

    def search(
        self,
        keyword: str,
        search_fields: List[str],
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        키워드 검색 (여러 필드에서 LIKE 검색)

        Args:
            keyword: 검색 키워드
            search_fields: 검색할 필드 리스트
            filters: 추가 필터 조건
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수
            order_by: 정렬 기준 컬럼명
            order_desc: 내림차순 정렬 여부

        Returns:
            모델 인스턴스 리스트
        """
        query = self.db.query(self.model)

        # 키워드 검색 (퍼지 검색)
        if keyword and search_fields:
            columns = [getattr(self.model, f) for f in search_fields if hasattr(self.model, f)]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        # 필터 적용
        if filters:
            query = self._apply_filters(query, filters)

        # 정렬 적용
        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            query = query.order_by(desc(column) if order_desc else asc(column))

        return query.offset(skip).limit(limit).all()

    def search_with_count(
        self,
        keyword: str,
        search_fields: List[str],
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> Tuple[List[ModelType], int]:
        """
        키워드 검색 + 총 개수 반환

        Args:
            keyword: 검색 키워드
            search_fields: 검색할 필드 리스트
            filters: 추가 필터 조건
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수
            order_by: 정렬 기준 컬럼명
            order_desc: 내림차순 정렬 여부

        Returns:
            (모델 인스턴스 리스트, 총 개수) 튜플
        """
        query = self.db.query(self.model)

        if keyword and search_fields:
            columns = [getattr(self.model, f) for f in search_fields if hasattr(self.model, f)]
            for condition in build_keyword_filter(keyword, columns):
                query = query.filter(condition)

        if filters:
            query = self._apply_filters(query, filters)

        total = query.count()

        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            query = query.order_by(desc(column) if order_desc else asc(column))

        items = query.offset(skip).limit(limit).all()

        return items, total

    # ==================== 생성 ====================

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

    def create_from_dict(self, data: Dict[str, Any]) -> ModelType:
        """
        딕셔너리로 새 레코드 생성

        Args:
            data: 생성할 데이터 딕셔너리

        Returns:
            생성된 모델 인스턴스
        """
        db_obj = self.model(**data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

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

    # ==================== 수정 ====================

    def update(
        self,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
        exclude_unset: bool = True
    ) -> ModelType:
        """
        레코드 수정

        Args:
            db_obj: 수정할 모델 인스턴스
            obj_in: 수정할 데이터 (Pydantic 스키마)
            exclude_unset: 설정되지 않은 필드 제외 여부

        Returns:
            수정된 모델 인스턴스
        """
        if hasattr(obj_in, 'model_dump'):
            update_data = obj_in.model_dump(exclude_unset=exclude_unset)
        else:
            update_data = obj_in.dict(exclude_unset=exclude_unset)

        return self.update_from_dict(db_obj, update_data)

    def update_from_dict(
        self,
        db_obj: ModelType,
        data: Dict[str, Any]
    ) -> ModelType:
        """
        딕셔너리로 레코드 수정

        Args:
            db_obj: 수정할 모델 인스턴스
            data: 수정할 데이터 딕셔너리

        Returns:
            수정된 모델 인스턴스
        """
        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_by_id(
        self,
        id: int,
        obj_in: UpdateSchemaType,
        exclude_unset: bool = True
    ) -> Optional[ModelType]:
        """
        ID로 레코드 수정

        Args:
            id: 수정할 레코드 ID
            obj_in: 수정할 데이터
            exclude_unset: 설정되지 않은 필드 제외 여부

        Returns:
            수정된 모델 인스턴스 또는 None
        """
        db_obj = self.get_by_id(id)
        if db_obj is None:
            return None
        return self.update(db_obj, obj_in, exclude_unset)

    # ==================== 삭제 ====================

    def delete(self, db_obj: ModelType) -> bool:
        """
        레코드 삭제

        Args:
            db_obj: 삭제할 모델 인스턴스

        Returns:
            삭제 성공 여부
        """
        self.db.delete(db_obj)
        self.db.commit()
        return True

    def delete_by_id(self, id: int) -> bool:
        """
        ID로 레코드 삭제

        Args:
            id: 삭제할 레코드 ID

        Returns:
            삭제 성공 여부
        """
        db_obj = self.get_by_id(id)
        if db_obj is None:
            return False
        return self.delete(db_obj)

    def soft_delete(self, db_obj: ModelType) -> Optional[ModelType]:
        """
        소프트 삭제 (is_active = False)

        Args:
            db_obj: 삭제할 모델 인스턴스

        Returns:
            수정된 모델 인스턴스 또는 None
        """
        if not hasattr(db_obj, 'is_active'):
            return None

        db_obj.is_active = False
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def soft_delete_by_id(self, id: int) -> Optional[ModelType]:
        """
        ID로 소프트 삭제

        Args:
            id: 삭제할 레코드 ID

        Returns:
            수정된 모델 인스턴스 또는 None
        """
        db_obj = self.get_by_id(id)
        if db_obj is None:
            return None
        return self.soft_delete(db_obj)

    # ==================== 내부 유틸리티 ====================

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

    # ==================== 트랜잭션 ====================

    def flush(self) -> None:
        """세션 플러시 (커밋 전 데이터베이스에 반영)"""
        self.db.flush()

    def commit(self) -> None:
        """세션 커밋"""
        self.db.commit()

    def rollback(self) -> None:
        """세션 롤백"""
        self.db.rollback()

    def refresh(self, db_obj: ModelType) -> ModelType:
        """모델 인스턴스 새로고침"""
        self.db.refresh(db_obj)
        return db_obj
