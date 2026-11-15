"""
Part Service (v0.12.0)
부품 관련 비즈니스 로직을 처리합니다.

Repository Pattern을 통해 데이터 접근 로직과 분리됩니다.

v0.11.0: 품목코드 구조 변경
- 품번 구조: [대분류(4)]-[소분류(3)]-[품목코드(5)]-[재질(2)]-[후처리(2)]
- 품목코드 5자리 = 앞 3자리 (사용자 입력) + 뒤 2자리 (자동채번)
- 예시: HB01-DCP-001-01-A6-NK

v0.12.0: Part UID 및 품번 수정 기능
- part_uid: 바코드/QR용 고유 ID (PT-XXXXXXXX), 변경 불가
- part_number: 품번 직접 수정 가능
- 분류 속성 변경 시 품번 자동 재생성 제거
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.repositories.part_repository import PartRepository
from app.models.parts import Part
from app.models.code_master import PartType
from app.models.inventory import Inventory
from app.schemas.parts import PartCreate, PartUpdate, AssemblyCreate
from app.schemas.inventory import InventoryStatus
from app.utils.part_number_generator import generate_part_number, generate_part_number_v2
from app.utils.uid_generator import generate_part_uid
from app.utils.part_name_helper import get_part_name
from app.services.pdf.highlight import strip_markup
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException,
)


class PartService:
    """
    부품 서비스 (v0.10.0)

    부품 관련 비즈니스 로직을 캡슐화합니다.
    Repository를 통해 데이터 접근 로직과 분리됩니다.
    - 품번 자동 생성 (v2: 대분류-소분류-품목코드-재질-후처리)
    - 부품 검색 및 필터링
    - 상태 관리
    - 승인 프로세스
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = PartRepository(db)

    # ==================== 조회 ====================

    def get(self, id: int) -> Optional[Part]:
        """ID로 부품 조회"""
        return self.repository.get_by_id(id)

    def get_or_raise(self, id: int) -> Part:
        """ID로 부품 조회 (없으면 예외)"""
        part = self.repository.get_by_id(id)
        if not part:
            raise NotFoundException("부품", id)
        return part

    def _part_uid_exists(self, uid: str) -> bool:
        """part_uid 중복 여부 (최소등록 잠정 품번=UID 유니크 보장용)."""
        return self.db.query(Part.id).filter(Part.part_uid == uid).first() is not None

    def classify_part(self, part_id: int, data: dict) -> Part:
        """미분류 부품을 정식 분류/채번으로 승격 (v0.97.0).

        코드 구성요소(대분류·소분류·품목코드·레벨 + 재질/후처리)를 채워 정식 품번 생성.
        part_uid·id는 유지되므로 BOM·재고·발주 참조가 안 깨진다.
        """
        part = self.repository.get_by_id(part_id) if hasattr(self.repository, "get_by_id") else \
            self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)
        pl = data.get("product_line_id"); pg = data.get("part_group_id")
        prefix = data.get("item_code_prefix"); level_id = data.get("level_id")
        if not (pl and pg and prefix and level_id):
            raise ValidationException(
                "분류에는 대분류·소분류·품목코드(3자리)·레벨이 필요합니다.", field="classify")
        try:
            part_number, part_number_display, item_code = generate_part_number_v2(
                db=self.db, product_line_id=pl, part_group_id=pg,
                item_code_prefix=prefix, level_id=level_id,
                material_id=data.get("material_id"), treatment_id=data.get("treatment_id"),
                item_code_suffix=data.get("item_code_suffix"),
            )
        except ValueError as e:
            raise ValidationException(str(e), field="part_number")
        part.part_number = part_number
        part.part_number_display = part_number_display
        part.item_code = item_code
        part.product_line_id = pl
        part.part_group_id = pg
        part.level_id = level_id
        if data.get("material_id") is not None:
            part.material_id = data["material_id"]
        if data.get("treatment_id") is not None:
            part.treatment_id = data["treatment_id"]
        if data.get("part_name"):
            part.part_name = data["part_name"]
        part.is_classified = True
        self.db.commit()
        self.db.refresh(part)
        return part

    def merge_parts(self, source_id: int, target_id: int, actor_id: Optional[int] = None) -> dict:
        """중복 부품 병합: source의 BOM 참조를 target으로 옮기고 source를 비활성화(soft delete).

        1차 버전: BOM(상위/하위) 참조 이관 + source is_active=False. (재고/발주 이관은 추후)
        """
        if source_id == target_id:
            raise ValidationException("같은 부품끼리는 병합할 수 없습니다.", field="target_id")
        from app.models.bom import BOM, BomChangeLog
        src = self.db.query(Part).filter(Part.id == source_id).first()
        tgt = self.db.query(Part).filter(Part.id == target_id).first()
        if not src or not tgt:
            raise NotFoundException("부품", source_id if not src else target_id)
        moved_child = moved_parent = 0
        # source가 하위품인 연결: child를 target으로 (중복/순환 시 건너뜀)
        for b in self.db.query(BOM).filter(BOM.child_part_id == source_id).all():
            exists = self.db.query(BOM).filter(BOM.parent_part_id == b.parent_part_id,
                                               BOM.child_part_id == target_id).first()
            if exists or b.parent_part_id == target_id:
                self.db.delete(b)
            else:
                b.child_part_id = target_id; moved_child += 1
        # source가 상위품인 연결: parent를 target으로
        for b in self.db.query(BOM).filter(BOM.parent_part_id == source_id).all():
            exists = self.db.query(BOM).filter(BOM.parent_part_id == target_id,
                                               BOM.child_part_id == b.child_part_id).first()
            if exists or b.child_part_id == target_id:
                self.db.delete(b)
            else:
                b.parent_part_id = target_id; moved_parent += 1
        src.is_active = False
        self.db.add(BomChangeLog(action="MERGE", parent_part_id=target_id, child_part_id=source_id,
                                 detail={"source": source_id, "target": target_id,
                                         "moved_child": moved_child, "moved_parent": moved_parent},
                                 actor_id=actor_id))
        self.db.commit()
        return {"source_id": source_id, "target_id": target_id,
                "moved_child": moved_child, "moved_parent": moved_parent}

    def get_by_part_number(self, part_number: str) -> Optional[Part]:
        """
        품번으로 부품 조회

        Args:
            part_number: 품번 (시스템용)

        Returns:
            Part 또는 None
        """
        return self.repository.get_by_part_number(part_number)

    def get_by_part_number_or_raise(self, part_number: str) -> Part:
        """품번으로 부품 조회 (없으면 예외)"""
        part = self.repository.get_by_part_number(part_number)
        if not part:
            raise NotFoundException("부품", part_number)
        return part

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
        limit: int = 100
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

        Returns:
            Part 리스트
        """
        return self.repository.search_parts(
            keyword=keyword,
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
            is_active=is_active,
            skip=skip,
            limit=limit
        )

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
        부품 검색 + 총 개수 반환 (페이지네이션)

        Args:
            missing_fields: 미입력 필드 목록 (예: ['supplier_id', 'part_name_en'])

        Returns:
            (Part 리스트, 총 개수) 튜플
        """
        return self.repository.search_parts_with_count(
            keyword=keyword,
            product_line_id=product_line_id,
            part_group_id=part_group_id,
            development_type_id=development_type_id,
            development_type_ids=development_type_ids,
            part_type_id=part_type_id,
            drawing_type_id=drawing_type_id,
            major_category_id=major_category_id,
            middle_category_id=middle_category_id,
            minor_category_id=minor_category_id,
            level_id=level_id,
            level_ids=level_ids,
            material_id=material_id,
            treatment_id=treatment_id,
            procurement_type_id=procurement_type_id,
            unit_id=unit_id,
            status=status,
            is_active=is_active,
            classified=classified,
            missing_fields=missing_fields,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc
        )

    def count_parts(
        self,
        keyword: Optional[str] = None,
        major_category_id: Optional[int] = None,
        middle_category_id: Optional[int] = None,
        minor_category_id: Optional[int] = None,
        level_id: Optional[int] = None,
        material_id: Optional[int] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """부품 수 조회 (검색 조건 적용)"""
        return self.repository.count_parts(
            keyword=keyword,
            major_category_id=major_category_id,
            middle_category_id=middle_category_id,
            minor_category_id=minor_category_id,
            level_id=level_id,
            material_id=material_id,
            status=status,
            is_active=is_active
        )

    # ==================== 생성 ====================

    def create_part(self, part_in: PartCreate) -> Part:
        """
        부품 생성 (품번 자동 생성) - v0.12.0

        신규 품번 구조: [대분류(4)]-[소분류(3)]-[품목코드(5)]-[재질(2)]-[후처리(2)]
        품목코드 5자리 = 앞 3자리 (사용자 입력) + 뒤 2자리 (자동채번)
        예시: HB01-DCP-001-01-A6-NK

        v0.12.0: Part UID 자동 생성 (PT-XXXXXXXX)

        Args:
            part_in: 부품 생성 데이터

        Returns:
            생성된 Part

        Raises:
            ValidationException: 품번 생성 실패 시
        """
        # 품번/품명은 식별자이므로 강조 마크업([[]], **, {color:} 등)이 새어들면 제거 (재발 방지)
        if part_in.part_number:
            part_in.part_number = strip_markup(part_in.part_number)
        if getattr(part_in, 'part_number_display', None):
            part_in.part_number_display = strip_markup(part_in.part_number_display)
        if getattr(part_in, 'part_name', None):
            part_in.part_name = strip_markup(part_in.part_name)

        # item_code_prefix, item_code_suffix는 품번 생성에만 사용되고 모델에는 저장되지 않음
        part_data = part_in.model_dump(exclude={'part_type_ids', 'item_code_prefix', 'item_code_suffix'})

        # 직접 입력 모드: part_number가 직접 전달된 경우 (v0.19.2, v0.21.0 파싱 추가)
        if part_in.part_number:
            import re
            from app.utils.part_number_parser import parse_part_number
            from app.models.code_master import Level

            # v0.21.0: 품번 파싱 시도 - 규칙에 맞으면 자동으로 ID 매핑
            parsed = parse_part_number(self.db, part_in.part_number)

            if parsed['success']:
                # 파싱 성공: 자동으로 ID 매핑
                if parsed['product_line_id']:
                    part_data['product_line_id'] = parsed['product_line_id']
                if parsed['part_group_id']:
                    part_data['part_group_id'] = parsed['part_group_id']
                if parsed['item_code']:
                    part_data['item_code'] = parsed['item_code']
                if parsed['material_id']:
                    part_data['material_id'] = parsed['material_id']
                if parsed['treatment_id']:
                    part_data['treatment_id'] = parsed['treatment_id']
                if parsed['level_id']:
                    part_data['level_id'] = parsed['level_id']

            # 레벨 코드 조회 (파싱된 level_id 또는 직접 선택한 level_id 사용)
            level_code = ""
            final_level_id = parsed.get('level_id') or part_in.level_id
            if final_level_id:
                level = self.db.query(Level).filter(Level.id == final_level_id).first()
                if level:
                    level_code = level.code
                    part_data['level_id'] = final_level_id

            # 하이픈 제거한 값 + 레벨코드를 내부 품번으로 저장
            base_part_number = part_in.part_number.replace("-", "").replace(" ", "")
            # 대괄호 레벨 부분 제거 (이미 포함된 경우)
            base_part_number = re.sub(r'\[[A-Za-z0-9]+\]', '', base_part_number)
            final_part_number = base_part_number + level_code if level_code else base_part_number

            # v0.24.0: 중복 체크 - 레벨 포함한 최종 품번으로 검사
            existing = self.repository.get_by_part_number(final_part_number)
            if existing:
                display_number = re.sub(r'\s*\[[A-Za-z0-9]+\]', '', part_in.part_number).strip()
                display_with_level = f"{display_number} [{level_code}]" if level_code else display_number
                raise ValidationException(
                    f"이미 존재하는 품번입니다: {display_with_level}",
                    field="part_number"
                )

            part_data['part_number'] = final_part_number
            # 표시용 품번: 입력값 + 공백 + [레벨]
            display_number = re.sub(r'\s*\[[A-Za-z0-9]+\]', '', part_in.part_number).strip()
            part_data['part_number_display'] = f"{display_number} [{level_code}]" if level_code else display_number
        # 신규 품번 구조 사용 (v0.20.0 - 레벨 필수 추가)
        elif part_in.product_line_id and part_in.part_group_id and part_in.item_code_prefix and part_in.level_id:
            try:
                part_number, part_number_display, item_code = generate_part_number_v2(
                    db=self.db,
                    product_line_id=part_in.product_line_id,
                    part_group_id=part_in.part_group_id,
                    item_code_prefix=part_in.item_code_prefix,
                    level_id=part_in.level_id,  # v0.20.0: 레벨 필수
                    material_id=part_in.material_id,
                    treatment_id=part_in.treatment_id,
                    item_code_suffix=part_in.item_code_suffix,  # v0.19.2: 직접 입력 suffix
                )
                part_data['part_number'] = part_number
                part_data['part_number_display'] = part_number_display
                part_data['item_code'] = item_code
            except ValueError as e:
                raise ValidationException(str(e), field="part_number")
        # Legacy 품번 구조 (하위 호환성)
        elif part_in.major_category_id and part_in.minor_category_id:
            try:
                part_number, part_number_display = generate_part_number(
                    db=self.db,
                    major_category_id=part_in.major_category_id,
                    middle_category_id=part_in.middle_category_id,
                    minor_category_id=part_in.minor_category_id
                )
                part_data['part_number'] = part_number
                part_data['part_number_display'] = part_number_display
            except ValueError as e:
                raise ValidationException(str(e), field="part_number")
        elif (part_data.get('part_name') or '').strip() or (part_data.get('description') or '').strip():
            # 최소 등록(미분류 부품, v0.96.0): 이름만으로 생성 → 고유 ID를 잠정 품번으로,
            # 코드·레벨은 나중에 '분류/채번'으로 승격. 참조는 내부 id/UID 기반이라 승격해도 안 깨짐.
            seed_name = (part_data.get('part_name') or part_data.get('description') or 'part').strip()
            uid = generate_part_uid(seed_name, datetime.now())
            cand, n = uid, 1
            while self.repository.get_by_part_number(cand) or self._part_uid_exists(cand):
                cand = f"{uid}-{n}"; n += 1
            part_data['part_number'] = cand
            # 미분류는 아직 진짜 품번이 없으므로 표시용 품번은 공백(고유ID는 내부 식별용으로만 유지)
            part_data['part_number_display'] = None
            part_data['part_uid'] = cand
            part_data['item_code'] = None
            part_data['is_classified'] = False
        else:
            raise ValidationException(
                "품번 생성을 위해 product_line_id, part_group_id, item_code_prefix (또는 부품명만으로 최소 등록)가 필요합니다.",
                field="part_number"
            )

        # Part UID 자동 생성 (v0.12.0) — 최소등록에서 이미 지정했으면 유지
        created_at = datetime.now()
        if not part_data.get('part_uid'):
            part_data['part_uid'] = generate_part_uid(part_data['part_number'], created_at)

        # v0.21.0: 부품명 자동 설정 (부품명이 없거나 "부품"인 경우 description에서 추출)
        part_data['part_name'] = get_part_name(
            part_data.get('part_name'),
            part_data.get('description'),
            part_data.get('part_number')  # fallback: 품번
        )

        # 부품 생성
        new_part = self.repository.create_from_dict(part_data)

        # 부품유형 (M:N 관계) 처리
        if part_in.part_type_ids:
            for part_type_id in part_in.part_type_ids:
                part_type = self.db.query(PartType).filter(PartType.id == part_type_id).first()
                if part_type:
                    new_part.part_types.append(part_type)
            self.db.commit()
            self.db.refresh(new_part)

        # 재고 자동 생성 (v0.5.0)
        self._create_inventory_for_part(new_part.id)

        return new_part

    def create_assembly(self, assembly_in: AssemblyCreate) -> Part:
        """
        조합/키트 생성 (자유형식 코드)

        BOM에서 사용할 조합(Assembly), 키트(Kit), 서브조합(Sub-Assembly) 등을 등록합니다.
        품번은 사용자가 직접 입력하며, 자동생성하지 않습니다.

        Args:
            assembly_in: 조합/키트 생성 데이터

        Returns:
            생성된 Part

        Raises:
            ValidationException: 품번 중복 시
        """
        # 품번/품명 식별자에서 강조 마크업 제거 (재발 방지)
        if assembly_in.part_number:
            assembly_in.part_number = strip_markup(assembly_in.part_number)
        if getattr(assembly_in, 'part_name', None):
            assembly_in.part_name = strip_markup(assembly_in.part_name)

        # 품번 중복 체크
        existing = self.repository.get_by_part_number(assembly_in.part_number)
        if existing:
            raise ValidationException(
                f"이미 존재하는 품번입니다: {assembly_in.part_number}",
                field="part_number"
            )

        # 데이터 준비 (part_type_ids 제외)
        assembly_data = assembly_in.model_dump(exclude={'part_type_ids'})

        # 표시용 품번 설정 (자유형식이므로 입력값 그대로 사용)
        assembly_data['part_number_display'] = assembly_in.part_number

        # Part UID 자동 생성 (v0.12.0) - 조합/키트에도 UID 생성
        created_at = datetime.now()
        assembly_data['part_uid'] = generate_part_uid(assembly_data['part_number'], created_at)

        # 조합/키트 생성
        new_assembly = self.repository.create_from_dict(assembly_data)

        # 부품유형 (M:N 관계) 처리
        if assembly_in.part_type_ids:
            for part_type_id in assembly_in.part_type_ids:
                part_type = self.db.query(PartType).filter(PartType.id == part_type_id).first()
                if part_type:
                    new_assembly.part_types.append(part_type)
            self.db.commit()
            self.db.refresh(new_assembly)

        # 재고 자동 생성 (v0.5.0)
        self._create_inventory_for_part(new_assembly.id)

        return new_assembly

    def _create_inventory_for_part(self, part_id: int) -> None:
        """
        부품에 대한 재고 자동 생성 (내부 메서드)

        Args:
            part_id: 부품 ID
        """
        # 이미 존재하면 건너뛰기
        existing = self.db.query(Inventory).filter(Inventory.part_id == part_id).first()
        if existing:
            return

        # 재고 생성 (초기 수량 0)
        inventory = Inventory(
            part_id=part_id,
            quantity_on_hand=0,
            status=InventoryStatus.OUT_OF_STOCK.value,
            is_active=True
        )
        self.db.add(inventory)
        self.db.commit()

    # ==================== 수정 ====================

    def update_part(self, part_id: int, part_in: PartUpdate) -> Part:
        """
        부품 수정 (v0.12.0 -> v0.19.1)

        두 가지 모드 지원:
        1. 직접 입력 모드: part_number가 전달되면 해당 값으로 품번 변경
        2. 구성요소 모드: part_number가 없고 구성요소가 변경되면 품번 재생성

        Args:
            part_id: 부품 ID
            part_in: 수정 데이터

        Returns:
            수정된 Part

        Raises:
            NotFoundException: 부품을 찾을 수 없는 경우
            ValidationException: 품번 중복 등 검증 실패 시
        """
        db_part = self.get_or_raise(part_id)

        # 품번/품명 식별자에서 강조 마크업 제거 (재발 방지)
        if getattr(part_in, 'part_number', None):
            part_in.part_number = strip_markup(part_in.part_number)
        if getattr(part_in, 'part_number_display', None):
            part_in.part_number_display = strip_markup(part_in.part_number_display)
        if getattr(part_in, 'part_name', None):
            part_in.part_name = strip_markup(part_in.part_name)

        # item_code_prefix, item_code_suffix, regenerate_part_number는 품번 생성에만 사용되고 모델에는 저장되지 않음
        update_data = part_in.model_dump(exclude_unset=True, exclude={'part_type_ids', 'item_code_prefix', 'item_code_suffix', 'regenerate_part_number'})

        # 품번규칙 A 모드: regenerate_part_number=True이면 품번 재생성
        if part_in.regenerate_part_number:
            # 재생성에 필요한 값 결정 (변경된 값 또는 기존 값)
            product_line_id = update_data.get('product_line_id') or db_part.product_line_id
            part_group_id = update_data.get('part_group_id') or db_part.part_group_id
            material_id = update_data.get('material_id', db_part.material_id)
            treatment_id = update_data.get('treatment_id', db_part.treatment_id)
            level_id = update_data.get('level_id') or db_part.level_id  # v0.20.0: 레벨 필수

            # item_code_prefix 결정 (변경 값 → 기존 item_code에서 추출)
            item_code_prefix = part_in.item_code_prefix
            if not item_code_prefix and db_part.item_code and len(db_part.item_code) >= 3:
                item_code_prefix = db_part.item_code[:3]

            # item_code_suffix 결정 (변경 값 → 없으면 자동 생성)
            item_code_suffix = part_in.item_code_suffix

            # 필수 값이 있는 경우에만 재생성 (v0.20.0: level_id 필수)
            if product_line_id and part_group_id and item_code_prefix and level_id:
                try:
                    part_number, part_number_display, item_code = generate_part_number_v2(
                        db=self.db,
                        product_line_id=product_line_id,
                        part_group_id=part_group_id,
                        item_code_prefix=item_code_prefix,
                        level_id=level_id,  # v0.20.0: 레벨 필수
                        material_id=material_id,
                        treatment_id=treatment_id,
                        item_code_suffix=item_code_suffix,  # v0.19.2: 직접 입력 suffix
                        exclude_part_id=part_id,  # 자기 자신 제외 (중복 체크 시)
                    )
                    update_data['part_number'] = part_number
                    update_data['part_number_display'] = part_number_display
                    update_data['item_code'] = item_code
                except ValueError as e:
                    raise ValidationException(str(e), field="part_number")
        # 품번 직접 수정 처리 (직접 입력 모드)
        elif 'part_number' in update_data and update_data['part_number']:
            new_part_number = update_data['part_number']
            # 레벨 코드 조회 (직접 입력 모드에서도 레벨 선택 가능)
            level_code = ""
            level_id = update_data.get('level_id') or db_part.level_id
            if level_id:
                from app.models.code_master import Level
                level = self.db.query(Level).filter(Level.id == level_id).first()
                if level:
                    level_code = level.code
            # 하이픈 제거한 값 + 레벨코드를 내부 품번으로 저장
            base_part_number = new_part_number.replace("-", "")
            final_part_number = base_part_number + level_code if level_code else base_part_number
            # 기존 품번과 다른 경우에만 중복 검증 및 part_number_display 자동 업데이트
            if final_part_number != db_part.part_number:
                existing = self.repository.get_by_part_number(final_part_number)
                if existing and existing.id != part_id:
                    raise ValidationException(
                        f"품번 '{new_part_number}'은(는) 이미 사용 중입니다.",
                        field="part_number"
                    )
            # 내부 품번 업데이트
            update_data['part_number'] = final_part_number
            # 표시용 품번: 입력값 + 공백 + [레벨]
            update_data['part_number_display'] = f"{new_part_number} [{level_code}]" if level_code else new_part_number

        # 부품유형 (M:N 관계) 처리
        if part_in.part_type_ids is not None:
            # 기존 관계 삭제
            db_part.part_types.clear()
            # 새 관계 추가
            for part_type_id in part_in.part_type_ids:
                part_type = self.db.query(PartType).filter(PartType.id == part_type_id).first()
                if part_type:
                    db_part.part_types.append(part_type)

        # v0.21.0: 부품명 자동 설정 (부품명이 없거나 "부품"인 경우 description에서 추출)
        final_part_name = update_data.get('part_name', db_part.part_name)
        final_description = update_data.get('description', db_part.description)
        update_data['part_name'] = get_part_name(
            final_part_name,
            final_description,
            db_part.part_number  # fallback: 품번
        )

        return self.repository.update_from_dict(db_part, update_data)

    # ==================== 상태 관리 ====================

    def activate(self, part_id: int) -> Part:
        """부품 활성화"""
        db_part = self.get_or_raise(part_id)
        return self.repository.update_from_dict(db_part, {"is_active": True})

    def deactivate(self, part_id: int) -> Part:
        """부품 비활성화"""
        db_part = self.get_or_raise(part_id)
        return self.repository.update_from_dict(db_part, {"is_active": False})

    def update_status(self, part_id: int, new_status: str) -> Part:
        """
        부품 상태 변경

        Args:
            part_id: 부품 ID
            new_status: 새로운 상태 (ACTIVE/INACTIVE/OBSOLETE)

        Returns:
            수정된 Part

        Raises:
            NotFoundException: 부품을 찾을 수 없는 경우
            ValidationException: 유효하지 않은 상태값
        """
        valid_statuses = ["ACTIVE", "INACTIVE", "OBSOLETE"]
        if new_status not in valid_statuses:
            raise ValidationException(
                f"유효하지 않은 상태입니다. 허용된 값: {', '.join(valid_statuses)}",
                field="status"
            )

        db_part = self.get_or_raise(part_id)

        # status와 is_active 동기화
        # ACTIVE/INACTIVE → is_active: True, OBSOLETE → is_active: False
        is_active = new_status != "OBSOLETE"

        return self.repository.update_from_dict(db_part, {
            "status": new_status,
            "is_active": is_active
        })

    # ==================== 승인 프로세스 ====================

    def update_approval_status(
        self,
        part_id: int,
        approval_status: str,
        approved_by: Optional[int] = None
    ) -> Part:
        """
        부품 승인 상태 변경

        Args:
            part_id: 부품 ID
            approval_status: 승인 상태 (DRAFT/PENDING/APPROVED/REJECTED)
            approved_by: 승인자 ID

        Returns:
            수정된 Part

        Raises:
            NotFoundException: 부품을 찾을 수 없는 경우
            ValidationException: 유효하지 않은 승인 상태
        """
        valid_statuses = ["DRAFT", "PENDING", "APPROVED", "REJECTED"]
        if approval_status not in valid_statuses:
            raise ValidationException(
                f"유효하지 않은 승인 상태입니다. 허용된 값: {', '.join(valid_statuses)}",
                field="approval_status"
            )

        db_part = self.get_or_raise(part_id)

        update_data = {"approval_status": approval_status}

        if approved_by:
            update_data["approved_by"] = approved_by

        if approval_status in ["APPROVED", "REJECTED"]:
            update_data["approved_at"] = datetime.now()

        return self.repository.update_from_dict(db_part, update_data)

    def submit_for_approval(self, part_id: int) -> Part:
        """승인 요청"""
        return self.update_approval_status(part_id, "PENDING")

    def approve(self, part_id: int, approved_by: int) -> Part:
        """승인"""
        return self.update_approval_status(part_id, "APPROVED", approved_by)

    def reject(self, part_id: int, approved_by: int) -> Part:
        """반려"""
        return self.update_approval_status(part_id, "REJECTED", approved_by)

    # ==================== 삭제 ====================

    def delete_part(self, part_id: int, force: bool = False) -> dict:
        """
        부품 삭제 (2단계 삭제 로직)

        1단계: 상태가 ACTIVE/INACTIVE인 경우 → OBSOLETE(단종)으로 변경
        2단계: 상태가 이미 OBSOLETE인 경우 → DB에서 완전 삭제

        Args:
            part_id: 부품 ID
            force: True인 경우 상태와 무관하게 강제 삭제 (관리자용)

        Returns:
            dict: {"action": "obsoleted" | "deleted", "message": str}

        Raises:
            NotFoundException: 부품을 찾을 수 없는 경우
            BusinessRuleException: 부품이 사용 중인 경우 (완전 삭제 시)
        """
        db_part = self.get_or_raise(part_id)

        # Force 삭제인 경우 (관리자용)
        if force:
            self._check_part_usage(db_part)
            self.repository.delete(db_part)
            return {
                "action": "deleted",
                "message": f"부품 '{db_part.part_number}'이(가) 완전히 삭제되었습니다."
            }

        # 2단계 삭제 로직
        if db_part.status != "OBSOLETE":
            # 1단계: 단종 처리
            self.repository.update_from_dict(db_part, {
                "status": "OBSOLETE",
                "is_active": False
            })
            return {
                "action": "obsoleted",
                "message": f"부품 '{db_part.part_number}'이(가) 단종 처리되었습니다. 완전 삭제하려면 한번 더 삭제를 요청하세요."
            }
        else:
            # 2단계: 완전 삭제
            self._check_part_usage(db_part)
            self.repository.delete(db_part)
            return {
                "action": "deleted",
                "message": f"부품 '{db_part.part_number}'이(가) 완전히 삭제되었습니다."
            }

    def _check_part_usage(self, part: Part) -> None:
        """
        부품 사용 여부 확인 (삭제 전 체크)

        BOM, 발주서, 작업지시서 등에서 사용 중인지 확인합니다.

        Raises:
            BusinessRuleException: 사용 중인 경우
        """
        from app.models.bom import BOM
        from app.models.purchase_order import PurchaseOrderItem
        from app.models.work_order import WorkOrderItem

        # BOM에서 사용 중인지 체크
        bom_count = self.db.query(BOM).filter(
            (BOM.parent_part_id == part.id) | (BOM.child_part_id == part.id)
        ).count()
        if bom_count > 0:
            raise BusinessRuleException(
                f"이 부품은 {bom_count}개의 BOM에서 사용 중입니다. BOM에서 먼저 제거해주세요."
            )

        # 발주서 항목에서 사용 중인지 체크
        po_item_count = self.db.query(PurchaseOrderItem).filter(
            PurchaseOrderItem.part_id == part.id
        ).count()
        if po_item_count > 0:
            raise BusinessRuleException(
                f"이 부품은 {po_item_count}개의 발주서 항목에서 사용 중입니다."
            )

        # 작업지시서 항목에서 사용 중인지 체크
        wo_item_count = self.db.query(WorkOrderItem).filter(
            WorkOrderItem.part_id == part.id
        ).count()
        if wo_item_count > 0:
            raise BusinessRuleException(
                f"이 부품은 {wo_item_count}개의 작업지시서 항목에서 사용 중입니다."
            )

        # 재고가 있는지 체크
        if part.inventory and part.inventory.quantity_on_hand > 0:
            raise BusinessRuleException(
                f"이 부품은 현재 재고({part.inventory.quantity_on_hand})가 있습니다. 재고를 0으로 조정한 후 삭제해주세요."
            )

    # ==================== UID 일괄 생성 ====================

    def generate_missing_uids(self) -> Dict[str, Any]:
        """
        UID가 없는 부품에 대해 일괄 UID 생성 (v0.12.0)

        Returns:
            dict: {
                "total_without_uid": int,  # UID 없는 총 부품 수
                "generated_count": int,     # 생성된 UID 수
                "failed_count": int,        # 실패한 수
                "parts": List[dict]         # 처리된 부품 목록
            }
        """
        # UID가 없는 부품 조회
        parts_without_uid = self.db.query(Part).filter(
            (Part.part_uid == None) | (Part.part_uid == "")
        ).all()

        total_without_uid = len(parts_without_uid)
        generated_count = 0
        failed_count = 0
        processed_parts = []

        for part in parts_without_uid:
            try:
                # 생성일 기준으로 UID 생성 (없으면 현재 시간)
                created_at = part.created_at or datetime.now()
                new_uid = generate_part_uid(part.part_number, created_at)

                # UID 업데이트
                part.part_uid = new_uid
                self.db.add(part)

                processed_parts.append({
                    "id": part.id,
                    "part_number": part.part_number,
                    "part_name": part.part_name,
                    "part_uid": new_uid,
                    "status": "success"
                })
                generated_count += 1
            except Exception as e:
                processed_parts.append({
                    "id": part.id,
                    "part_number": part.part_number,
                    "part_name": part.part_name,
                    "part_uid": None,
                    "status": "failed",
                    "error": str(e)
                })
                failed_count += 1

        # 커밋
        self.db.commit()

        return {
            "total_without_uid": total_without_uid,
            "generated_count": generated_count,
            "failed_count": failed_count,
            "parts": processed_parts
        }

    # ==================== 파일 관련 ====================

    def update_files(
        self,
        part_id: int,
        drawing_file: Optional[str] = None,
        photo_file: Optional[str] = None,
        document_files: Optional[List[Dict[str, Any]]] = None
    ) -> Part:
        """
        부품 파일 정보 업데이트

        Args:
            part_id: 부품 ID
            drawing_file: 도면 파일 경로
            photo_file: 사진 파일 경로
            document_files: 기타 문서 리스트

        Returns:
            수정된 Part
        """
        db_part = self.get_or_raise(part_id)

        update_data = {}
        if drawing_file is not None:
            update_data["drawing_file"] = drawing_file
        if photo_file is not None:
            update_data["photo_file"] = photo_file
        if document_files is not None:
            update_data["document_files"] = document_files

        if update_data:
            return self.repository.update_from_dict(db_part, update_data)
        return db_part
