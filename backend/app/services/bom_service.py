"""
BOM Service
BOM 비즈니스 로직 처리

v0.18.0: BOM 변경 시 자동 원가 재계산 추가
"""

from typing import List, Optional, Tuple, Set
from sqlalchemy.orm import Session

from app.models.bom import BOM
from app.models.parts import Part
from app.repositories.bom_repository import BOMRepository
from app.schemas.bom import BOMCreate, BOMUpdate, BOMItemCreate
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException,
    CircularReferenceException,
)


class BOMService:
    """BOM 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = BOMRepository(db)

    def _recalculate_parent_costs(self, parent_part_id: int, visited: Optional[Set[int]] = None) -> None:
        """
        상위 부품의 원가를 재계산하고, 해당 부품을 사용하는 상위 BOM도 연쇄적으로 재계산

        Args:
            parent_part_id: 재계산할 부품 ID
            visited: 순환 참조 방지용 방문 기록
        """
        if visited is None:
            visited = set()

        if parent_part_id in visited:
            return  # 순환 참조 방지

        visited.add(parent_part_id)

        try:
            # PriceService를 사용하여 원가 계산 및 저장
            from app.services.price_service import PriceService
            price_service = PriceService(self.db)
            price_service.save_calculated_cost(parent_part_id)

            # 이 부품을 하위로 사용하는 상위 BOM들도 재계산
            parent_boms = self.repository.get_parents(parent_part_id, is_active=True)
            for bom in parent_boms:
                self._recalculate_parent_costs(bom.parent_part_id, visited.copy())

        except Exception as e:
            # 원가 계산 실패해도 BOM 작업은 계속 진행
            print(f"원가 재계산 실패 (부품 ID: {parent_part_id}): {e}")

    def get_or_raise(self, bom_id: int) -> BOM:
        """BOM 조회 (없으면 예외)"""
        bom = self.repository.get_with_parts(bom_id)
        if not bom:
            raise NotFoundException("BOM", bom_id)
        return bom

    def get_children(self, parent_part_id: int, is_active: Optional[bool] = True) -> List[BOM]:
        """상위 부품의 하위 부품 목록 조회"""
        # 상위 부품 존재 확인
        parent = self.db.query(Part).filter(Part.id == parent_part_id).first()
        if not parent:
            raise NotFoundException("부품", parent_part_id)

        return self.repository.get_children(parent_part_id, is_active)

    def get_parents(self, child_part_id: int, is_active: Optional[bool] = True) -> List[BOM]:
        """하위 부품이 사용되는 상위 부품 목록 조회"""
        # 하위 부품 존재 확인
        child = self.db.query(Part).filter(Part.id == child_part_id).first()
        if not child:
            raise NotFoundException("부품", child_part_id)

        return self.repository.get_parents(child_part_id, is_active)

    def get_bom_tree(self, parent_part_id: int) -> List[dict]:
        """BOM 트리 구조 조회"""
        # 상위 부품 존재 확인
        parent = self.db.query(Part).filter(Part.id == parent_part_id).first()
        if not parent:
            raise NotFoundException("부품", parent_part_id)

        return self.repository.get_bom_tree(parent_part_id)

    def search_bom_with_count(
        self,
        parent_part_id: Optional[int] = None,
        child_part_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[BOM], int]:
        """BOM 검색"""
        return self.repository.search_bom_with_count(
            parent_part_id=parent_part_id,
            child_part_id=child_part_id,
            is_active=is_active,
            skip=skip,
            limit=limit
        )

    def get_bom_parts(
        self,
        keyword: Optional[str] = None,
        part_type: Optional[str] = None,
        product_line_id: Optional[int] = None,
        part_group_id: Optional[int] = None,
        level_id: Optional[int] = None,
        material_id: Optional[int] = None,
        treatment_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[dict], int]:
        """
        BOM에 등록된 부품 목록 조회 (v0.20.0, v0.22.0 필터 추가)

        상위 부품(완제품/반제품) 또는 하위 부품 모두를 조회할 수 있습니다.

        Args:
            keyword: 검색어 (품번/품명)
            part_type: 'parent', 'child', 'all' (기본값: 'all')
            product_line_id: 대분류/제품라인 필터
            part_group_id: 소분류/품목군 필터
            level_id: 레벨 필터
            material_id: 재질 필터
            treatment_id: 후처리 필터
            skip: 건너뛸 개수
            limit: 조회 개수

        Returns:
            (부품 목록, 총 개수)
        """
        from sqlalchemy import union_all, distinct, func, or_

        # 기본값 설정
        if not part_type:
            part_type = 'all'

        # 쿼리 빌드
        if part_type == 'parent':
            # 상위 부품만 (BOM에서 parent_part_id로 사용된 부품)
            part_ids_subq = self.db.query(distinct(BOM.parent_part_id)).filter(BOM.is_active == True).subquery()
            query = self.db.query(Part).filter(Part.id.in_(part_ids_subq))
        elif part_type == 'child':
            # 하위 부품만 (BOM에서 child_part_id로 사용된 부품)
            part_ids_subq = self.db.query(distinct(BOM.child_part_id)).filter(BOM.is_active == True).subquery()
            query = self.db.query(Part).filter(Part.id.in_(part_ids_subq))
        else:
            # 모든 BOM 관련 부품 (상위 + 하위)
            parent_ids = self.db.query(BOM.parent_part_id).filter(BOM.is_active == True)
            child_ids = self.db.query(BOM.child_part_id).filter(BOM.is_active == True)
            all_ids = parent_ids.union(child_ids).subquery()
            query = self.db.query(Part).filter(Part.id.in_(all_ids))

        # 활성 부품만
        query = query.filter(Part.is_active == True)

        # 키워드 검색
        if keyword:
            keyword_filter = f"%{keyword}%"
            query = query.filter(
                or_(
                    Part.part_number.ilike(keyword_filter),
                    Part.part_number_display.ilike(keyword_filter),
                    Part.part_name.ilike(keyword_filter),
                    Part.part_name_en.ilike(keyword_filter),
                    Part.description.ilike(keyword_filter),
                )
            )

        # v0.22.0: 코드 마스터 기반 필터
        if product_line_id:
            query = query.filter(Part.product_line_id == product_line_id)
        if part_group_id:
            query = query.filter(Part.part_group_id == part_group_id)
        if level_id:
            query = query.filter(Part.level_id == level_id)
        if material_id:
            query = query.filter(Part.material_id == material_id)
        if treatment_id:
            query = query.filter(Part.treatment_id == treatment_id)

        # 총 개수
        total = query.count()

        # 페이지네이션 및 정렬
        parts = query.order_by(Part.part_number).offset(skip).limit(limit).all()

        # 결과 변환
        items = []
        for part in parts:
            items.append({
                "id": part.id,
                "part_number": part.part_number,
                "part_number_display": part.part_number_display,
                "part_name": part.part_name or part.part_name_en or "",
                "name_ko": part.part_name,
                "name_en": part.part_name_en,
                "specification": part.specification,
                "product_line": {
                    "id": part.product_line.id,
                    "code": part.product_line.code,
                    "name_ko": part.product_line.name_ko,
                } if part.product_line else None,
                "part_group": {
                    "id": part.part_group.id,
                    "code": part.part_group.code,
                    "name_ko": part.part_group.name_ko,
                } if part.part_group else None,
                "level": {
                    "id": part.level.id,
                    "code": part.level.code,
                    "name_ko": part.level.name_ko,
                } if part.level else None,
                "material": {
                    "id": part.material.id,
                    "code": part.material.code,
                    "name_ko": part.material.name_ko,
                } if part.material else None,
                "treatment": {
                    "id": part.treatment.id,
                    "code": part.treatment.code,
                    "name_ko": part.treatment.name_ko,
                } if part.treatment else None,
            })

        return items, total

    def create_bom(self, data: BOMCreate) -> BOM:
        """BOM 생성"""
        # 상위 부품 존재 확인
        parent = self.db.query(Part).filter(Part.id == data.parent_part_id).first()
        if not parent:
            raise NotFoundException("상위 부품", data.parent_part_id)

        # 하위 부품 존재 확인
        child = self.db.query(Part).filter(Part.id == data.child_part_id).first()
        if not child:
            raise NotFoundException("하위 부품", data.child_part_id)

        # 자기 자신 참조 방지
        if data.parent_part_id == data.child_part_id:
            raise ValidationException("상위 부품과 하위 부품이 같을 수 없습니다.")

        # 중복 체크
        existing = self.repository.get_by_parent_and_child(data.parent_part_id, data.child_part_id)
        if existing:
            raise AlreadyExistsException(
                "BOM",
                "parent-child",
                f"{data.parent_part_id}-{data.child_part_id}"
            )

        # 순환 참조 체크
        if self.repository.check_circular_reference(data.parent_part_id, data.child_part_id):
            raise CircularReferenceException(
                f"순환 참조가 감지되었습니다. 하위 부품({child.part_number})이 이미 상위 부품({parent.part_number})의 상위 구조에 포함되어 있습니다."
            )

        # BOM 생성
        bom = self.repository.create(data)

        # v0.18.0: 상위 부품 원가 재계산
        self._recalculate_parent_costs(data.parent_part_id)

        return bom

    def create_bulk(self, parent_part_id: int, items: List[BOMItemCreate]) -> List[BOM]:
        """BOM 일괄 생성"""
        # 상위 부품 존재 확인
        parent = self.db.query(Part).filter(Part.id == parent_part_id).first()
        if not parent:
            raise NotFoundException("상위 부품", parent_part_id)

        created = []
        for item in items:
            # 하위 부품 존재 확인
            child = self.db.query(Part).filter(Part.id == item.child_part_id).first()
            if not child:
                raise NotFoundException("하위 부품", item.child_part_id)

            # 자기 자신 참조 방지
            if parent_part_id == item.child_part_id:
                raise ValidationException(f"상위 부품과 하위 부품이 같을 수 없습니다. (부품 ID: {item.child_part_id})")

            # 중복 체크 (이미 있으면 건너뜀)
            existing = self.repository.get_by_parent_and_child(parent_part_id, item.child_part_id)
            if existing:
                continue

            # 순환 참조 체크
            if self.repository.check_circular_reference(parent_part_id, item.child_part_id):
                raise CircularReferenceException(
                    f"순환 참조가 감지되었습니다. 부품({child.part_number})"
                )

            # BOM 생성
            bom_data = {
                "parent_part_id": parent_part_id,
                "child_part_id": item.child_part_id,
                "quantity": item.quantity,
                "unit_id": item.unit_id,
                "sort_order": item.sort_order,
                "remark": item.remark,
                "bom_level": 1,
                "is_active": True
            }
            bom = self.repository.create_from_dict(bom_data)
            created.append(bom)

        # v0.18.0: 상위 부품 원가 재계산 (일괄 추가 후 1회만 계산)
        if created:
            self._recalculate_parent_costs(parent_part_id)

        return created

    def update_bom(self, bom_id: int, data: BOMUpdate) -> BOM:
        """BOM 수정"""
        bom = self.get_or_raise(bom_id)
        parent_part_id = bom.parent_part_id  # 재계산용

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return bom

        for key, value in update_data.items():
            setattr(bom, key, value)

        self.db.commit()
        self.db.refresh(bom)

        # v0.18.0: 수량 변경 시 상위 부품 원가 재계산
        if 'quantity' in update_data:
            self._recalculate_parent_costs(parent_part_id)

        return bom

    def delete_bom(self, bom_id: int) -> None:
        """BOM 삭제"""
        bom = self.get_or_raise(bom_id)
        parent_part_id = bom.parent_part_id  # 재계산용
        self.repository.delete(bom)

        # v0.18.0: 상위 부품 원가 재계산
        self._recalculate_parent_costs(parent_part_id)

    def delete_all_children(self, parent_part_id: int) -> int:
        """상위 부품의 모든 BOM 삭제"""
        result = self.repository.delete_by_parent(parent_part_id)

        # v0.18.0: 상위 부품 원가 재계산
        self._recalculate_parent_costs(parent_part_id)

        return result

    def update_sort_orders(self, parent_part_id: int, orders: List[dict]) -> None:
        """BOM 정렬 순서 일괄 업데이트"""
        self.repository.update_sort_orders(parent_part_id, orders)

    # ==================== BOM 개편 P2/P3: 이동·묶기·감사로그 ====================

    def _log(self, action: str, parent_id, child_id, detail: dict, actor_id):
        """BOM 변경 감사로그 기록."""
        from app.models.bom import BomChangeLog
        self.db.add(BomChangeLog(action=action, parent_part_id=parent_id,
                                 child_part_id=child_id, detail=detail, actor_id=actor_id))

    def move_bom(self, bom_id: int, new_parent_part_id: int, actor_id: Optional[int] = None) -> BOM:
        """BOM 연결(edge)을 다른 상위로 이동(reparent). 순환/자기참조/중복 검증.

        edge 단위 이동이므로 같은 하위품이 다른 상위에 걸려 있어도 그 연결은 영향 없음.
        """
        bom = self.repository.get_with_parts(bom_id)
        if not bom:
            raise NotFoundException("BOM", bom_id)
        old_parent = bom.parent_part_id
        if new_parent_part_id == old_parent:
            return bom  # 변화 없음
        if new_parent_part_id == bom.child_part_id:
            raise ValidationException("자기 자신을 상위로 지정할 수 없습니다.", field="new_parent_part_id")
        new_parent = self.db.query(Part).filter(Part.id == new_parent_part_id).first()
        if not new_parent:
            raise NotFoundException("부품", new_parent_part_id)
        # 순환: 하위품이 새 상위의 조상인지
        if self.repository.check_circular_reference(new_parent_part_id, bom.child_part_id):
            raise CircularReferenceException(
                f"순환 참조: 하위 부품이 이미 상위 '{new_parent.part_number}'의 상위 구조에 포함되어 있습니다.")
        # 중복: 새 상위에 같은 하위가 이미 있으면
        dup = self.repository.get_by_parent_and_child(new_parent_part_id, bom.child_part_id)
        if dup and dup.id != bom.id:
            raise ValidationException("대상 상위에 이미 같은 하위 부품이 있습니다.", field="new_parent_part_id")
        bom.parent_part_id = new_parent_part_id
        self._log("MOVE", new_parent_part_id, bom.child_part_id,
                  {"from_parent": old_parent, "to_parent": new_parent_part_id, "bom_id": bom_id}, actor_id)
        self.db.commit()
        self.db.refresh(bom)
        # 원가 재계산(양쪽)
        try:
            self._recalculate_parent_costs(old_parent)
            self._recalculate_parent_costs(new_parent_part_id)
        except Exception:
            pass
        return bom

    def group_under(self, child_bom_ids: List[int], new_parent_part_id: int,
                    actor_id: Optional[int] = None) -> dict:
        """상위 트리 만들기: 선택한 하위 연결들을 새 상위(new_parent) 밑으로 묶는다.

        선택 노드가 공통 상위 P의 자식이면, P→new_parent 연결을 추가하고 각 노드를 new_parent로 이동.
        """
        if not child_bom_ids:
            raise ValidationException("묶을 하위 항목을 선택하세요.", field="child_bom_ids")
        boms = [self.repository.get_with_parts(b) for b in child_bom_ids]
        boms = [b for b in boms if b]
        if not boms:
            raise NotFoundException("BOM", child_bom_ids)
        parents = {b.parent_part_id for b in boms}
        common_parent = next(iter(parents)) if len(parents) == 1 else None
        new_parent = self.db.query(Part).filter(Part.id == new_parent_part_id).first()
        if not new_parent:
            raise NotFoundException("부품", new_parent_part_id)
        # new_parent가 선택 하위 중 하나면 안 됨
        if any(b.child_part_id == new_parent_part_id for b in boms):
            raise ValidationException("새 상위가 선택한 하위 중 하나일 수 없습니다.", field="new_parent_part_id")
        # 공통 상위가 있으면 P→new_parent 연결 추가(없을 때만)
        if common_parent and not self.repository.get_by_parent_and_child(common_parent, new_parent_part_id):
            if self.repository.check_circular_reference(common_parent, new_parent_part_id):
                raise CircularReferenceException("순환 참조로 상위 묶기를 할 수 없습니다.")
            self.repository.create_from_dict({
                "parent_part_id": common_parent, "child_part_id": new_parent_part_id,
                "quantity": 1.0, "bom_level": 1, "sort_order": 0, "is_active": True,
            })
        # 각 선택 노드를 new_parent로 이동
        moved = 0
        for b in boms:
            if b.child_part_id == new_parent_part_id:
                continue
            if self.repository.check_circular_reference(new_parent_part_id, b.child_part_id):
                continue
            if self.repository.get_by_parent_and_child(new_parent_part_id, b.child_part_id):
                continue
            b.parent_part_id = new_parent_part_id
            moved += 1
        self._log("GROUP", new_parent_part_id, None,
                  {"common_parent": common_parent, "moved_bom_ids": child_bom_ids, "moved": moved}, actor_id)
        self.db.commit()
        try:
            if common_parent:
                self._recalculate_parent_costs(common_parent)
            self._recalculate_parent_costs(new_parent_part_id)
        except Exception:
            pass
        return {"new_parent_part_id": new_parent_part_id, "common_parent": common_parent, "moved": moved}

    def get_change_log(self, parent_part_id: Optional[int] = None, limit: int = 100) -> List:
        """BOM 변경 감사로그 조회."""
        from app.models.bom import BomChangeLog
        q = self.db.query(BomChangeLog)
        if parent_part_id is not None:
            q = q.filter(BomChangeLog.parent_part_id == parent_part_id)
        return q.order_by(BomChangeLog.created_at.desc()).limit(limit).all()
