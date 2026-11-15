"""
BOM Repository
BOM 데이터 접근 계층
"""

from typing import List, Optional, Tuple
from sqlalchemy import desc, asc
from sqlalchemy.orm import Session, joinedload

from app.repositories.base import BaseRepository
from app.models.bom import BOM
from app.models.parts import Part
from app.schemas.bom import BOMCreate, BOMUpdate


class BOMRepository(BaseRepository[BOM, BOMCreate, BOMUpdate]):
    """BOM 데이터 접근 Repository"""

    def __init__(self, db: Session):
        super().__init__(db, BOM)

    def get_with_parts(self, bom_id: int) -> Optional[BOM]:
        """BOM 상세 조회 (부품 정보 포함)"""
        return self.db.query(BOM).options(
            joinedload(BOM.parent_part),
            joinedload(BOM.child_part),
            joinedload(BOM.unit)
        ).filter(BOM.id == bom_id).first()

    def get_by_parent_and_child(self, parent_part_id: int, child_part_id: int) -> Optional[BOM]:
        """상위-하위 부품 조합으로 BOM 조회"""
        return self.db.query(BOM).filter(
            BOM.parent_part_id == parent_part_id,
            BOM.child_part_id == child_part_id
        ).first()

    def get_children(self, parent_part_id: int, is_active: Optional[bool] = None) -> List[BOM]:
        """상위 부품의 하위 부품 목록 조회"""
        query = self.db.query(BOM).options(
            joinedload(BOM.child_part).joinedload(Part.unit),
            joinedload(BOM.unit)
        ).filter(BOM.parent_part_id == parent_part_id)

        if is_active is not None:
            query = query.filter(BOM.is_active == is_active)

        return query.order_by(BOM.sort_order, BOM.id).all()

    def get_parents(self, child_part_id: int, is_active: Optional[bool] = None) -> List[BOM]:
        """하위 부품이 사용되는 상위 부품 목록 조회"""
        query = self.db.query(BOM).options(
            joinedload(BOM.parent_part),
            joinedload(BOM.unit)
        ).filter(BOM.child_part_id == child_part_id)

        if is_active is not None:
            query = query.filter(BOM.is_active == is_active)

        return query.order_by(BOM.parent_part_id).all()

    def search_bom_with_count(
        self,
        parent_part_id: Optional[int] = None,
        child_part_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[BOM], int]:
        """BOM 검색 (페이지네이션)"""
        query = self.db.query(BOM).options(
            joinedload(BOM.parent_part),
            joinedload(BOM.child_part),
            joinedload(BOM.unit)
        )

        if parent_part_id is not None:
            query = query.filter(BOM.parent_part_id == parent_part_id)

        if child_part_id is not None:
            query = query.filter(BOM.child_part_id == child_part_id)

        if is_active is not None:
            query = query.filter(BOM.is_active == is_active)

        total = query.count()
        items = query.order_by(BOM.parent_part_id, BOM.sort_order).offset(skip).limit(limit).all()

        return items, total

    def get_bom_tree(self, parent_part_id: int, max_level: int = 10) -> List[dict]:
        """
        BOM 트리 구조 조회 (재귀)
        max_level로 무한 루프 방지
        """
        result = []
        self._build_tree(parent_part_id, 1, max_level, result, set())
        return result

    def _build_tree(
        self,
        parent_id: int,
        current_level: int,
        max_level: int,
        result: List[dict],
        visited: set
    ):
        """재귀적으로 BOM 트리 구성"""
        if current_level > max_level or parent_id in visited:
            return

        visited.add(parent_id)

        children = self.get_children(parent_id, is_active=True)
        for bom in children:
            child_part = bom.child_part
            unit_name = bom.unit.name_ko if bom.unit else (child_part.unit.name_ko if child_part and child_part.unit else None)

            node = {
                "id": bom.id,
                "part_id": bom.child_part_id,
                "part_number": child_part.part_number if child_part else "",
                "part_number_display": child_part.part_number_display if child_part else "",
                "part_name": child_part.part_name if child_part else "",
                "description": child_part.description if child_part else None,  # v0.21.0
                "specification": child_part.specification if child_part else None,
                "quantity": bom.quantity,
                "unit_name": unit_name,
                "bom_level": current_level,
                "level_code": (child_part.level.code if child_part and getattr(child_part, "level", None) else None),
                "is_classified": bool(getattr(child_part, "is_classified", True)) if child_part else True,
                "attachment_count": len(getattr(child_part, "attachments", []) or []) if child_part else 0,
                "children": []
            }

            # 재귀 호출 (하위 부품의 하위 부품)
            child_children = []
            self._build_tree(bom.child_part_id, current_level + 1, max_level, child_children, visited.copy())
            node["children"] = child_children

            result.append(node)

    def check_circular_reference(self, parent_part_id: int, child_part_id: int) -> bool:
        """
        순환 참조 체크
        child_part_id가 parent_part_id의 상위에 있는지 확인
        True: 순환 참조 있음, False: 없음
        """
        visited = set()
        return self._check_circular(child_part_id, parent_part_id, visited)

    def _check_circular(self, current_id: int, target_id: int, visited: set) -> bool:
        """재귀적으로 순환 참조 체크"""
        if current_id == target_id:
            return True

        if current_id in visited:
            return False

        visited.add(current_id)

        # current_id가 상위품인 BOM 조회
        children = self.db.query(BOM).filter(
            BOM.parent_part_id == current_id,
            BOM.is_active == True
        ).all()

        for bom in children:
            if self._check_circular(bom.child_part_id, target_id, visited):
                return True

        return False

    def delete_by_parent(self, parent_part_id: int) -> int:
        """상위 부품의 모든 BOM 삭제"""
        count = self.db.query(BOM).filter(BOM.parent_part_id == parent_part_id).delete()
        self.db.commit()
        return count

    def update_sort_orders(self, parent_part_id: int, orders: List[dict]) -> None:
        """BOM 정렬 순서 일괄 업데이트"""
        for order in orders:
            self.db.query(BOM).filter(
                BOM.parent_part_id == parent_part_id,
                BOM.id == order["id"]
            ).update({"sort_order": order["sort_order"]})
        self.db.commit()
