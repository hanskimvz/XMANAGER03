"""
Code Master Service
코드 마스터 관련 비즈니스 로직을 처리합니다.

Repository Pattern을 통해 데이터 접근 로직과 분리됩니다.

10개의 코드 테이블을 통합 관리합니다:
- MajorCategory (대분류)
- MiddleCategory (중분류)
- MinorCategory (소분류)
- SubCategory (세분류)
- ItemCode (품목코드)
- Material (재질)
- Treatment (후처리)
- Level (레벨)
- ProcurementType (조달구분)
- Unit (단위)
"""

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.repositories.code_master_repository import CodeMasterRepository
from app.core.database import Base
from app.models.code_master import Level, Material, ProductLine, PartGroup, Treatment
from app.models.parts import Part
from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ValidationException,
)


class CodeMasterService:
    """
    코드 마스터 서비스

    모든 코드 테이블에 대한 공통 CRUD 기능을 제공합니다.
    Repository를 통해 데이터 접근 로직과 분리됩니다.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = CodeMasterRepository(db)

    def _validate_table(self, table_name: str) -> None:
        """테이블명 유효성 검사"""
        if not self.repository.is_valid_table(table_name):
            raise ValidationException(
                f"유효하지 않은 테이블명입니다: {table_name}",
                field="table_name"
            )

    def _get_display_name(self, table_name: str) -> str:
        """테이블 한글 표시명 조회"""
        return self.repository.get_display_name(table_name)

    # ==================== 조회 ====================

    def get(self, table_name: str, id: int) -> Optional[Base]:
        """ID로 코드 조회"""
        self._validate_table(table_name)
        return self.repository.get_by_id(table_name, id)

    def get_or_raise(self, table_name: str, id: int) -> Base:
        """ID로 코드 조회 (없으면 예외)"""
        self._validate_table(table_name)
        item = self.repository.get_by_id(table_name, id)
        if not item:
            display_name = self._get_display_name(table_name)
            raise NotFoundException(display_name, id)
        return item

    def get_by_code(self, table_name: str, code: str) -> Optional[Base]:
        """코드값으로 조회"""
        self._validate_table(table_name)
        return self.repository.get_by_code(table_name, code)

    def get_all(
        self,
        table_name: str,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Base]:
        """
        전체 코드 목록 조회

        Args:
            table_name: 테이블명
            is_active: 활성 여부 필터
            skip: 건너뛸 레코드 수
            limit: 조회할 최대 레코드 수

        Returns:
            코드 리스트
        """
        self._validate_table(table_name)
        return self.repository.get_all(table_name, is_active, skip, limit)

    def get_all_with_count(
        self,
        table_name: str,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Base], int]:
        """
        전체 코드 목록 조회 + 총 개수 반환 (페이지네이션)

        Returns:
            (코드 리스트, 총 개수) 튜플
        """
        self._validate_table(table_name)
        return self.repository.get_all_with_count(table_name, is_active, skip, limit)

    def get_active(self, table_name: str) -> List[Base]:
        """활성 코드만 조회"""
        self._validate_table(table_name)
        return self.repository.get_active(table_name)

    def count(self, table_name: str, is_active: Optional[bool] = None) -> int:
        """코드 수 조회"""
        self._validate_table(table_name)
        return self.repository.count(table_name, is_active)

    # ==================== 생성 ====================

    def create(self, table_name: str, data: Dict[str, Any]) -> Base:
        """
        코드 생성

        Args:
            table_name: 테이블명
            data: 생성할 데이터

        Returns:
            생성된 코드

        Raises:
            AlreadyExistsException: 동일한 코드가 이미 존재하는 경우
        """
        self._validate_table(table_name)
        display_name = self._get_display_name(table_name)

        # 코드 중복 검사
        if 'code' in data:
            if self.repository.exists_by_code(table_name, data['code']):
                raise AlreadyExistsException(display_name, "code", data['code'])

        # 생성
        return self.repository.create(table_name, data)

    # ==================== 수정 ====================

    def update(self, table_name: str, id: int, data: Dict[str, Any]) -> Base:
        """
        코드 수정

        Args:
            table_name: 테이블명
            id: 코드 ID
            data: 수정할 데이터

        Returns:
            수정된 코드

        Raises:
            NotFoundException: 코드를 찾을 수 없는 경우
            AlreadyExistsException: 변경하려는 코드가 이미 존재하는 경우
        """
        db_item = self.get_or_raise(table_name, id)
        display_name = self._get_display_name(table_name)

        # 코드 변경 시 중복 검사
        if 'code' in data and data['code'] != db_item.code:
            if self.repository.exists_by_code(table_name, data['code']):
                raise AlreadyExistsException(display_name, "code", data['code'])

        # 업데이트
        return self.repository.update(table_name, db_item, data)

    # ==================== 삭제 ====================

    def delete(self, table_name: str, id: int) -> bool:
        """
        코드 삭제

        Args:
            table_name: 테이블명
            id: 코드 ID

        Returns:
            삭제 성공 여부

        Raises:
            NotFoundException: 코드를 찾을 수 없는 경우
        """
        db_item = self.get_or_raise(table_name, id)
        return self.repository.delete(table_name, db_item)

    # ==================== 상태 관리 ====================

    def activate(self, table_name: str, id: int) -> Base:
        """코드 활성화"""
        db_item = self.get_or_raise(table_name, id)
        return self.repository.set_active(table_name, db_item, True)

    def deactivate(self, table_name: str, id: int) -> Base:
        """코드 비활성화"""
        db_item = self.get_or_raise(table_name, id)
        return self.repository.set_active(table_name, db_item, False)

    # ==================== 유틸리티 ====================

    def get_all_tables_summary(self) -> Dict[str, int]:
        """
        모든 코드 테이블의 요약 정보 조회

        Returns:
            테이블별 코드 수 딕셔너리
        """
        return self.repository.get_all_tables_summary()

    def update_sort_orders(
        self,
        table_name: str,
        sort_orders: List[Dict[str, int]]
    ) -> List[Base]:
        """
        코드 정렬순서 일괄 업데이트

        Args:
            table_name: 테이블명
            sort_orders: [{"id": 1, "sort_order": 1}, ...]

        Returns:
            수정된 코드 리스트
        """
        self._validate_table(table_name)
        return self.repository.update_sort_orders(table_name, sort_orders)

    # ==================== 특정 테이블 전용 메서드 ====================

    def get_level_by_bom_level(self, bom_level: int) -> Optional[Level]:
        """BOM 레벨로 Level 코드 조회"""
        return self.repository.get_level_by_bom_level(bom_level)

    def get_materials_by_type(self, material_type: str) -> List[Material]:
        """
        재질 타입별 조회

        Args:
            material_type: 재질 타입 (예: 금속, 플라스틱, 고무 등 - description에서 검색)
        """
        return self.repository.get_materials_by_type(material_type)

    # ==================== 품번 일괄 업데이트 ====================

    def get_affected_parts(self, table_name: str, item_id: int) -> Dict[str, Any]:
        """
        코드 변경 시 영향받는 부품 목록 조회

        Args:
            table_name: 코드 테이블명 (product-lines, part-groups, materials, treatments)
            item_id: 코드 ID

        Returns:
            {
                "code_type": str,
                "current_code": str,
                "affected_count": int,
                "parts": [{"id": int, "part_number": str, "part_name": str}, ...]
            }
        """
        self._validate_table(table_name)
        code_item = self.get_or_raise(table_name, item_id)

        # 코드 타입에 따라 영향받는 부품 조회
        parts_query = self.db.query(Part)

        if table_name == "product-lines":
            # 대분류: product_line_id로 조회
            parts_query = parts_query.filter(Part.product_line_id == item_id)
        elif table_name == "part-groups":
            # 품목군: part_group_id로 조회
            parts_query = parts_query.filter(Part.part_group_id == item_id)
        elif table_name == "materials":
            # 재질: material_id로 조회
            parts_query = parts_query.filter(Part.material_id == item_id)
        elif table_name == "treatments":
            # 후처리: treatment_id로 조회
            parts_query = parts_query.filter(Part.treatment_id == item_id)
        else:
            # 품번에 영향을 주지 않는 테이블
            return {
                "code_type": table_name,
                "current_code": code_item.code,
                "affected_count": 0,
                "parts": [],
                "message": "이 코드 유형은 품번에 직접 영향을 주지 않습니다."
            }

        parts = parts_query.all()

        return {
            "code_type": table_name,
            "current_code": code_item.code,
            "affected_count": len(parts),
            "parts": [
                {
                    "id": p.id,
                    "part_number": p.part_number,
                    "part_number_display": p.part_number_display,
                    "part_name": p.part_name
                }
                for p in parts
            ]
        }

    def batch_update_part_numbers(
        self,
        table_name: str,
        item_id: int,
        new_code: str
    ) -> Dict[str, Any]:
        """
        코드 변경에 따른 품번 일괄 업데이트

        Args:
            table_name: 코드 테이블명
            item_id: 코드 ID
            new_code: 새 코드값

        Returns:
            {
                "updated_count": int,
                "parts": [{"id": int, "old_part_number": str, "new_part_number": str}, ...]
            }
        """
        self._validate_table(table_name)
        code_item = self.get_or_raise(table_name, item_id)
        old_code = code_item.code

        if old_code == new_code:
            return {
                "updated_count": 0,
                "parts": [],
                "message": "코드가 변경되지 않았습니다."
            }

        # 영향받는 부품 조회
        parts_query = self.db.query(Part)

        if table_name == "product-lines":
            parts_query = parts_query.filter(Part.product_line_id == item_id)
        elif table_name == "part-groups":
            parts_query = parts_query.filter(Part.part_group_id == item_id)
        elif table_name == "materials":
            parts_query = parts_query.filter(Part.material_id == item_id)
        elif table_name == "treatments":
            parts_query = parts_query.filter(Part.treatment_id == item_id)
        else:
            return {
                "updated_count": 0,
                "parts": [],
                "message": "이 코드 유형은 품번에 직접 영향을 주지 않습니다."
            }

        parts = parts_query.all()
        updated_parts = []

        for part in parts:
            old_part_number = part.part_number
            old_part_number_display = part.part_number_display

            # 품번 업데이트 (코드 위치에 따라 교체)
            new_part_number, new_part_number_display = self._replace_code_in_part_number(
                part, table_name, old_code, new_code
            )

            if new_part_number != old_part_number:
                part.part_number = new_part_number
                part.part_number_display = new_part_number_display

                updated_parts.append({
                    "id": part.id,
                    "part_name": part.part_name,
                    "old_part_number": old_part_number,
                    "new_part_number": new_part_number,
                    "old_part_number_display": old_part_number_display,
                    "new_part_number_display": new_part_number_display
                })

        self.db.commit()

        return {
            "updated_count": len(updated_parts),
            "parts": updated_parts
        }

    def _replace_code_in_part_number(
        self,
        part: Part,
        table_name: str,
        old_code: str,
        new_code: str
    ) -> Tuple[str, str]:
        """
        품번에서 특정 코드를 새 코드로 교체

        품번 구조: [대분류(4)]-[품목군(3)]-[품목코드앞3]-[품목코드뒤2]-[재질(2)]-[후처리(2)]
        예: HB01-DCP-001-01-A6-NK
        시스템용: HB01DCP00101A6NK
        """
        # 현재 품번에서 각 구성요소 추출
        product_line = self.db.query(ProductLine).filter(
            ProductLine.id == part.product_line_id
        ).first()
        part_group = self.db.query(PartGroup).filter(
            PartGroup.id == part.part_group_id
        ).first()
        material = self.db.query(Material).filter(
            Material.id == part.material_id
        ).first() if part.material_id else None
        treatment = self.db.query(Treatment).filter(
            Treatment.id == part.treatment_id
        ).first() if part.treatment_id else None

        # 기본값 설정
        product_line_code = product_line.code if product_line else "XXXX"
        part_group_code = part_group.code if part_group else "XXX"
        material_code = material.code if material else "XX"
        treatment_code = treatment.code if treatment else "NN"
        item_code = part.item_code or "00000"

        # 새 코드로 교체
        if table_name == "product-lines":
            product_line_code = new_code
        elif table_name == "part-groups":
            part_group_code = new_code
        elif table_name == "materials":
            material_code = new_code
        elif table_name == "treatments":
            treatment_code = new_code

        # 품목코드 분리 (앞 3자리, 뒤 2자리)
        item_code_prefix = item_code[:3] if len(item_code) >= 3 else item_code.ljust(3, '0')
        item_code_suffix = item_code[3:] if len(item_code) > 3 else "01"

        # 새 품번 생성
        new_part_number = f"{product_line_code}{part_group_code}{item_code}{material_code}{treatment_code}"
        new_part_number_display = f"{product_line_code}-{part_group_code}-{item_code_prefix}-{item_code_suffix}-{material_code}-{treatment_code}"

        return new_part_number, new_part_number_display
