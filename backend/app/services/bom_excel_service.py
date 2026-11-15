"""
BOM 엑셀 업로드 서비스 v2

v0.23.0: 초기 구현
v0.23.1 (v2): 다중 L1 지원, 미등록 품번 자동 생성, 기존 BOM 덮어쓰기, 자동 전개, 부분 성공

엑셀 양식 (v2):
  - 1행: 컬럼 헤더 (레벨, 품번, 품명, 규격, 수량, 단위, 비고)
  - 2행~: 데이터 (L1이 상위 부품, L2~가 하위 부품)
  - L1이 여러 번 나타나면 각각 별도의 BOM 트리로 처리
"""

import re
import hashlib
from io import BytesIO
from typing import List, Optional, Tuple, Dict, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.parts import Part
from app.models.bom import BOM
from app.models.code_master import Unit, Level
from app.repositories.bom_repository import BOMRepository
from app.schemas.bom import (
    BOMExcelValidationItem,
    BOMUploadValidateResponse,
    BOMUploadResult,
)


# 품번 접미사 → 레벨 코드 매핑
SUFFIX_TO_LEVEL_CODE = {
    "U": "F",   # Unit → Finished Good (비슷한 역할)
    "F": "F",   # Finished Good
    "K": "K",   # Kit
    "P": "P",   # Package
    "S": "S",   # Sub-Assembly
    "C": "C",   # Combination
    "R": "R",   # Raw Component
    "O": "O",   # Outsourcing
    "M": "M",   # Manufacturing
}


class BOMExcelService:
    """BOM 엑셀 업로드 서비스 v2"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = BOMRepository(db)
        # 캐시
        self._level_cache: Dict[str, Level] = {}
        self._unit_cache: Dict[str, int] = {}

    def parse_excel(self, file_content: bytes) -> Tuple[Dict[str, Any], List[Dict]]:
        """
        엑셀 파일 파싱 (v2: 헤더 없는 형식)

        Returns:
            (header_info, rows) 튜플
            - header_info: {} (v2에서는 빈 dict, 호환성 유지)
            - rows: [{row_number, level, part_number_display, part_name, specification, quantity, unit_name, remark}]
        """
        import openpyxl

        wb = openpyxl.load_workbook(BytesIO(file_content), read_only=True, data_only=True)
        ws = wb.active

        header_info: Dict[str, Any] = {}

        # 1행이 헤더인지 데이터인지 자동 감지
        first_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
        start_row = 1
        if first_row and first_row[0]:
            first_cell = str(first_row[0]).strip().upper()
            # 첫 셀이 L+숫자 또는 U (Unit) 패턴이면 데이터 → 1행부터 읽기
            # 그렇지 않으면 헤더 → 2행부터 읽기
            if not re.search(r'^(L\d+|U)$', first_cell, re.IGNORECASE):
                start_row = 2

        # 1차 파싱: U가 사용되는지 감지
        raw_rows = []
        has_unit_level = False
        for row_idx, row in enumerate(ws.iter_rows(min_row=start_row, values_only=True), start=start_row):
            if not row or not row[0]:
                continue

            level_str = str(row[0]).strip()

            # U (Unit) 레벨 감지
            if re.match(r'^U$', level_str, re.IGNORECASE):
                has_unit_level = True
                raw_rows.append((row_idx, 0, row))  # U → level 0
                continue

            level_match = re.search(r'L(\d+)', level_str, re.IGNORECASE)
            if not level_match:
                continue

            level = int(level_match.group(1))
            raw_rows.append((row_idx, level, row))

        # 2차 변환: U가 있으면 레벨 재매핑 (U→1, L1→2, L2→3, ...)
        rows = []
        for row_idx, level, row in raw_rows:
            if has_unit_level:
                level = level + 1  # U(0)→1, L1→2, L2→3, ...

            part_number_display = str(row[1] or '').strip()
            if not part_number_display:
                continue

            rows.append({
                "row_number": row_idx,
                "level": level,
                "part_number_display": part_number_display,
                "part_name": str(row[2] or '').strip() if len(row) > 2 and row[2] else None,
                "specification": str(row[3] or '').strip() if len(row) > 3 and row[3] else None,
                "quantity": float(row[4]) if len(row) > 4 and row[4] else 1.0,
                "unit_name": str(row[5] or '').strip() if len(row) > 5 and row[5] else None,
                "remark": str(row[6] or '').strip() if len(row) > 6 and row[6] else None,
            })

        wb.close()
        return header_info, rows

    # ==================== 품번/단위 조회 ====================

    def _resolve_part(self, part_number_display: str) -> Optional[Part]:
        """품번으로 부품 조회 (다양한 매칭 시도)"""
        import logging
        logger = logging.getLogger(__name__)

        # 1. part_number_display 정확 매칭
        part = self.db.query(Part).filter(
            Part.part_number_display == part_number_display
        ).first()
        if part:
            return part

        # 2. bracket suffix 제거 후 매칭
        stripped = re.sub(r'\s*\[.*?\]\s*$', '', part_number_display).strip()
        if stripped != part_number_display:
            part = self.db.query(Part).filter(
                Part.part_number_display == stripped
            ).first()
            if part:
                return part

        # 3. 하이픈 제거 후 part_number 매칭
        no_hyphen = stripped.replace("-", "")
        part = self.db.query(Part).filter(
            Part.part_number == no_hyphen
        ).first()
        if part:
            return part

        # 4. bracket suffix에서 레벨코드 추출 → 하이픈 제거 + 레벨코드 붙여서 매칭
        level_code = self._extract_level_code_from_suffix(part_number_display)
        if level_code:
            no_hyphen_with_code = no_hyphen + level_code
            part = self.db.query(Part).filter(
                Part.part_number == no_hyphen_with_code
            ).first()
            if part:
                return part

        # 5. ILIKE 매칭 (공백/대소문자 차이 허용)
        part = self.db.query(Part).filter(
            Part.part_number_display.ilike(part_number_display.strip())
        ).first()
        if part:
            return part

        logger.warning(f"품번 매칭 실패: '{part_number_display}' (stripped='{stripped}', no_hyphen='{no_hyphen}')")
        return None

    def _resolve_unit(self, unit_name: str) -> Optional[int]:
        """단위명으로 unit_id 조회 (캐시)"""
        if not unit_name:
            return None
        if unit_name in self._unit_cache:
            return self._unit_cache[unit_name]

        unit = self.db.query(Unit).filter(Unit.name_ko == unit_name).first()
        if not unit:
            unit = self.db.query(Unit).filter(Unit.code == unit_name.upper()).first()
        if unit:
            self._unit_cache[unit_name] = unit.id
            return unit.id
        return None

    def _get_level_by_code(self, code: str) -> Optional[Level]:
        """레벨 코드로 Level 조회 (캐시)"""
        if code in self._level_cache:
            return self._level_cache[code]
        level = self.db.query(Level).filter(Level.code == code).first()
        if level:
            self._level_cache[code] = level
        return level

    def _extract_level_code_from_suffix(self, part_number_display: str) -> Optional[str]:
        """품번 접미사에서 레벨 코드 추출: 'HB05-PLP-BBO-01-A6-HB [C]' → 'C'"""
        match = re.search(r'\[(\w+)\]\s*$', part_number_display)
        if match:
            suffix = match.group(1).upper()
            return SUFFIX_TO_LEVEL_CODE.get(suffix)
        return None

    # ==================== 검증 ====================

    def validate(
        self,
        header_info: Dict[str, Any],
        rows: List[Dict],
        parent_part_id: Optional[int] = None,
        mode: str = "replace"
    ) -> BOMUploadValidateResponse:
        """
        엑셀 데이터 검증 (v2)

        - L1 = 상위 부품 (여러 개 가능, 각각 별도 BOM 트리)
        - L2~ = 하위 부품
        - 미등록 품번: warning (자동 생성 가능)
        - 기존 BOM 충돌: warning (덮어쓰기)
        - 부분 성공 허용: error 건은 스킵
        """
        # 첫 행이 L1인지 확인
        if rows and rows[0]["level"] != 1:
            return BOMUploadValidateResponse(
                is_valid=False,
                total_rows=len(rows),
                error_count=1,
                items=[BOMExcelValidationItem(
                    row_number=rows[0]["row_number"], level=rows[0]["level"],
                    part_number_display=rows[0]["part_number_display"],
                    status="error",
                    messages=["L1(상위품번)이 먼저 필요합니다"]
                )]
            )

        validation_items: List[BOMExcelValidationItem] = []
        # 스택: [(level, part_id_or_display)] - 트리 구조 추적용
        stack: List[Tuple[int, Any]] = []
        prev_level = 0
        detected_parents: List[dict] = []
        overwrite_set: Set[str] = set()  # "parent_id:child_display" 중복 방지

        for row in rows:
            item = BOMExcelValidationItem(
                row_number=row["row_number"],
                level=row["level"],
                part_number_display=row["part_number_display"],
                part_name=row.get("part_name"),
                specification=row.get("specification"),
                quantity=row.get("quantity", 1.0),
                unit_name=row.get("unit_name"),
                remark=row.get("remark"),
            )

            # L1: 상위 부품 (새 BOM 시작)
            if row["level"] == 1:
                stack = []  # 스택 초기화
                prev_level = 0

                part = self._resolve_part(row["part_number_display"])
                if part:
                    item.part_id = part.id
                    item.resolved_part_name = part.part_name
                    detected_parents.append({
                        "part_id": part.id,
                        "part_number": part.part_number_display or part.part_number,
                        "part_name": part.part_name,
                    })
                    stack.append((1, part.id))
                else:
                    # L1이 미등록이면 에러 (상위 부품은 반드시 존재해야 함)
                    item.status = "error"
                    item.messages.append(f"미등록 상위 품번: {row['part_number_display']}")

                prev_level = 1
                validation_items.append(item)
                continue

            # L2~: 하위 부품
            # 레벨 점프 검증 (한 단계 초과 증가만 불가)
            if row["level"] > prev_level + 1:
                item.status = "error"
                item.messages.append(
                    f"레벨 점프 불가: L{prev_level} → L{row['level']} (L{prev_level + 1}이 누락)"
                )
                validation_items.append(item)
                prev_level = row["level"]
                continue

            # 스택 없으면 (이전 L1이 에러) 스킵
            if not stack:
                item.status = "error"
                item.messages.append("상위 부품이 없습니다 (이전 L1 에러)")
                validation_items.append(item)
                prev_level = row["level"]
                continue

            # 품번 조회
            part = self._resolve_part(row["part_number_display"])
            if not part:
                # 미등록 품번: warning (자동 생성 가능)
                item.is_new_part = True
                item.status = "warning"
                item.messages.append(f"미등록 품번 (자동 생성 대상)")
            else:
                item.part_id = part.id
                item.resolved_part_name = part.part_name

            # 스택에서 현재 레벨의 부모 결정
            while len(stack) > 0 and stack[-1][0] >= row["level"]:
                stack.pop()

            current_parent_id = stack[-1][1] if stack else None
            if current_parent_id:
                item.resolved_parent_part_id = current_parent_id

            # 자기참조 체크 (part_id가 있을 때만)
            if part and current_parent_id and part.id == current_parent_id:
                item.status = "error"
                item.messages.append("자기 자신을 하위 부품으로 등록할 수 없습니다.")
                validation_items.append(item)
                stack.append((row["level"], part.id))
                prev_level = row["level"]
                continue

            # 기존 BOM 충돌 체크 (부모와 자식 모두 기존 부품일 때만)
            if part and current_parent_id:
                existing = self.repository.get_by_parent_and_child(current_parent_id, part.id)
                if existing:
                    item.has_existing_bom = True
                    if item.status != "warning":
                        item.status = "warning"
                    item.messages.append("기존 BOM 존재 (덮어쓰기)")

            # 순환참조 체크
            if part and current_parent_id:
                if self.repository.check_circular_reference(current_parent_id, part.id):
                    item.status = "error"
                    item.messages.append("순환 참조가 감지되었습니다.")

            # 수량 검증
            if row.get("quantity", 1.0) <= 0:
                item.status = "error"
                item.messages.append("수량은 0보다 커야 합니다.")

            # 스택에 추가 (part_id가 있으면 part_id, 없으면 품번 문자열 사용)
            stack_value = part.id if part else row["part_number_display"]
            stack.append((row["level"], stack_value))
            prev_level = row["level"]
            validation_items.append(item)

        # 결과 집계
        valid_count = sum(1 for i in validation_items if i.status == "valid")
        warning_count = sum(1 for i in validation_items if i.status == "warning")
        error_count = sum(1 for i in validation_items if i.status == "error")
        new_part_count = sum(1 for i in validation_items if i.is_new_part)
        overwrite_count = sum(1 for i in validation_items if i.has_existing_bom)

        return BOMUploadValidateResponse(
            is_valid=True,  # v2: error가 있어도 부분 성공 가능 → 항상 true (프론트에서 판단)
            total_rows=len(validation_items),
            valid_count=valid_count,
            warning_count=warning_count,
            error_count=error_count,
            new_part_count=new_part_count,
            overwrite_count=overwrite_count,
            items=validation_items,
            parent_parts=detected_parents,
        )

    # ==================== 실행 ====================

    def execute(
        self,
        header_info: Dict[str, Any],
        rows: List[Dict],
        parent_part_id: Optional[int] = None,
        mode: str = "replace"
    ) -> BOMUploadResult:
        """
        검증 후 BOM 일괄 등록 (v2)

        - L1 = 상위 부품 (여러 개 처리)
        - 미등록 품번 자동 생성
        - 기존 BOM 덮어쓰기
        - 오류 건 스킵 (부분 성공)
        """
        created_count = 0
        skipped_count = 0
        overwrite_count = 0
        new_part_count = 0
        error_count = 0
        errors = []
        parent_part_ids: List[int] = []
        sort_counters: Dict[int, int] = {}

        # 스택: [(level, part_id)]
        stack: List[Tuple[int, int]] = []
        current_l1_part_id: Optional[int] = None

        for row in rows:
            try:
                # L1: 상위 부품
                if row["level"] == 1:
                    part = self._resolve_part(row["part_number_display"])
                    if not part:
                        error_count += 1
                        errors.append({
                            "row": row["row_number"],
                            "part_no": row["part_number_display"],
                            "error": "미등록 상위 품번"
                        })
                        stack = []
                        current_l1_part_id = None
                        continue

                    current_l1_part_id = part.id
                    if part.id not in parent_part_ids:
                        parent_part_ids.append(part.id)

                    # replace 모드: 해당 L1의 기존 BOM 삭제
                    if mode == "replace":
                        self._delete_tree_recursive(part.id)

                    stack = [(1, part.id)]
                    sort_counters = {}
                    continue

                # L2~: 하위 부품
                if not stack or current_l1_part_id is None:
                    error_count += 1
                    errors.append({
                        "row": row["row_number"],
                        "part_no": row["part_number_display"],
                        "error": "상위 부품 없음"
                    })
                    continue

                # 레벨 점프 체크
                current_stack_level = stack[-1][0] if stack else 0
                if row["level"] > current_stack_level + 1:
                    error_count += 1
                    errors.append({
                        "row": row["row_number"],
                        "part_no": row["part_number_display"],
                        "error": f"레벨 점프: L{current_stack_level} → L{row['level']}"
                    })
                    continue

                # 품번 조회 또는 자동 생성
                part = self._resolve_part(row["part_number_display"])
                if not part:
                    # 미등록 품번 자동 생성
                    part = self._auto_create_part(row)
                    if part:
                        new_part_count += 1
                    else:
                        error_count += 1
                        errors.append({
                            "row": row["row_number"],
                            "part_no": row["part_number_display"],
                            "error": "품번 자동 생성 실패"
                        })
                        continue

                # 스택에서 부모 결정
                while len(stack) > 0 and stack[-1][0] >= row["level"]:
                    stack.pop()

                current_parent_id = stack[-1][1] if stack else current_l1_part_id

                # 자기참조 스킵
                if part.id == current_parent_id:
                    error_count += 1
                    errors.append({
                        "row": row["row_number"],
                        "part_no": row["part_number_display"],
                        "error": "자기 참조"
                    })
                    continue

                # 기존 BOM 처리
                existing = self.repository.get_by_parent_and_child(current_parent_id, part.id)
                if existing:
                    if mode == "append":
                        skipped_count += 1
                        stack.append((row["level"], part.id))
                        continue
                    else:
                        # replace: 이미 삭제되었지만 혹시 남아있으면 삭제
                        self.db.delete(existing)
                        self.db.flush()
                        overwrite_count += 1

                # 단위 조회
                unit_id = self._resolve_unit(row.get("unit_name", ""))

                # 정렬순서
                if current_parent_id not in sort_counters:
                    sort_counters[current_parent_id] = 0
                sort_counters[current_parent_id] += 1

                # BOM 생성
                bom = BOM(
                    parent_part_id=current_parent_id,
                    child_part_id=part.id,
                    quantity=row.get("quantity", 1.0),
                    unit_id=unit_id,
                    bom_level=row["level"] - 1,  # L2→bom_level=1, L3→bom_level=2
                    sort_order=sort_counters[current_parent_id],
                    remark=row.get("remark"),
                    is_active=True,
                )
                self.db.add(bom)
                self.db.flush()
                created_count += 1

                stack.append((row["level"], part.id))

            except Exception as e:
                error_count += 1
                errors.append({
                    "row": row["row_number"],
                    "part_no": row["part_number_display"],
                    "error": str(e)
                })

        # 커밋
        if created_count > 0 or overwrite_count > 0 or new_part_count > 0:
            self.db.commit()

        # 원가 재계산
        if created_count > 0:
            try:
                from app.services.bom_service import BOMService
                bom_service = BOMService(self.db)
                for pid in parent_part_ids:
                    bom_service._recalculate_parent_costs(pid)
            except Exception:
                pass

        total = created_count + skipped_count + error_count
        msg_parts = [f"{created_count}개 BOM 등록"]
        if new_part_count > 0:
            msg_parts.append(f"신규 품번 {new_part_count}개 생성")
        if overwrite_count > 0:
            msg_parts.append(f"{overwrite_count}개 덮어쓰기")
        if skipped_count > 0:
            msg_parts.append(f"{skipped_count}개 건너뜀")
        if error_count > 0:
            msg_parts.append(f"{error_count}개 오류")

        return BOMUploadResult(
            success=created_count > 0,
            message=", ".join(msg_parts),
            total=total,
            created_count=created_count,
            skipped_count=skipped_count,
            overwrite_count=overwrite_count,
            new_part_count=new_part_count,
            error_count=error_count,
            errors=errors,
            parent_part_ids=parent_part_ids,
        )

    # ==================== 미등록 품번 자동 생성 ====================

    def _auto_create_part(self, row: Dict) -> Optional[Part]:
        """
        미등록 품번 자동 생성

        기본값:
        - 품명: 엑셀의 part_name 또는 품번과 동일
        - 단위: EA (공정은 LOT)
        - 상태: ACTIVE
        - 레벨: 품번 접미사에서 추출
        """
        try:
            display = row["part_number_display"]
            stripped = re.sub(r'\s*\[.*?\]\s*$', '', display).strip()
            part_number = stripped.replace("-", "")

            # 이미 존재하면 리턴
            existing = self.db.query(Part).filter(Part.part_number == part_number).first()
            if existing:
                return existing

            # 레벨 결정 (접미사에서 추출)
            level_code = self._extract_level_code_from_suffix(display)
            level_id = None
            if level_code:
                level_obj = self._get_level_by_code(level_code)
                if level_obj:
                    level_id = level_obj.id

            # 단위 결정
            unit_id = None
            if level_code == "O":
                unit_id = self._resolve_unit("LOT")
            if not unit_id:
                unit_id = self._resolve_unit("EA")

            # part_uid 생성
            uid_hash = hashlib.md5(f"{part_number}{datetime.now().isoformat()}".encode()).hexdigest()[:8].upper()
            part_uid = f"PT-{uid_hash}"

            part = Part(
                part_number=part_number,
                part_number_display=stripped,
                part_name=row.get("part_name") or stripped,
                specification=row.get("specification"),
                part_uid=part_uid,
                level_id=level_id,
                unit_id=unit_id,
                is_active=True,
            )
            self.db.add(part)
            self.db.flush()
            return part
        except Exception:
            return None

    # ==================== 삭제 ====================

    def _delete_tree_recursive(self, parent_part_id: int) -> None:
        """상위 부품의 직접 하위 BOM만 삭제 (재귀 삭제 제거 - 참조 구조 보존)"""
        self.repository.delete_by_parent(parent_part_id)
