"""
품번 자동생성 유틸리티 (v0.20.0)
부품의 분류 정보를 기반으로 품번을 자동 생성합니다.

품번 구조 (v0.20.0):
[대분류(4)]-[소분류(3)]-[품목코드(5)]-[재질(2)]-[후처리(2)]-[레벨(1)]

예시:
- 시스템용: HB01DCP00101A6NKR (하이픈 없음)
- 표시용:   HB01-DCP-001-01-A6-NK [R] (하이픈 포함, 레벨은 공백 + 대괄호)

품목코드 (5자리):
- 앞 3자리: 사용자 입력 (item_code_prefix) - 예: 001, 002
- 뒤 2자리: 자동 채번 (동일 대분류+소분류+prefix 내에서 01~99)

레벨 (1자리, 필수):
- R: 원자재/단품 (Row Component)
- M: 내부공정 (Manufacturing)
- O: 외주공정 (Outsourcing)
- C: 조합부품 (Composite)
- S: 서브어셈블리 (Sub-assembly)
- P: 패키지 (Package)
- K: 키트 (Kit)
- F: 최종품 (Finished Good)
"""

from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.parts import Part
from app.models.code_master import (
    ProductLine, PartGroup, Material, Treatment, Level,
    MajorCategory, MiddleCategory, MinorCategory  # Legacy
)
from app.core.config import settings


def generate_part_number_v2(
    db: Session,
    product_line_id: int,
    part_group_id: int,
    item_code_prefix: str,  # 사용자 입력 3자리
    level_id: int,  # 레벨 ID (필수, v0.20.0)
    material_id: Optional[int] = None,
    treatment_id: Optional[int] = None,
    item_code_suffix: Optional[str] = None,  # 사용자 직접 입력 2자리 (v0.19.2)
    exclude_part_id: Optional[int] = None,  # 중복 체크 시 제외할 부품 ID (수정 시)
) -> Tuple[str, str, str]:
    """
    품번 자동생성 (v0.20.0 - 레벨 필수 추가)

    Args:
        db: 데이터베이스 세션
        product_line_id: 대분류/제품라인 ID (필수)
        part_group_id: 소분류/품목군 ID (필수)
        item_code_prefix: 품목코드 앞 3자리 (사용자 입력, 필수)
        level_id: 레벨 ID (필수, v0.20.0)
        material_id: 재질 ID (선택, 미선택 시 XX)
        treatment_id: 후처리 ID (선택, 미선택 시 NN)
        item_code_suffix: 품목코드 뒤 2자리 (직접 입력, 비워두면 자동생성)
        exclude_part_id: 중복 체크 시 제외할 부품 ID (수정 시)

    Returns:
        (part_number, part_number_display, item_code):
        - part_number: 시스템용 품번 (하이픈 없음)
        - part_number_display: 표시용 품번 (하이픈 포함)
        - item_code: 품목코드 5자리 (prefix 3자리 + suffix 2자리)

    Raises:
        ValueError: 분류 코드를 찾을 수 없거나 prefix가 유효하지 않은 경우

    Example:
        >>> generate_part_number_v2(db, 1, 1, "001", 1, 1, 1)
        ('HB01DCP00101A6NKR', 'HB01-DCP-001-01-A6-NK [R]', '00101')
    """

    # 0. item_code_prefix 검증 (3자리 숫자 또는 영숫자)
    if not item_code_prefix or len(item_code_prefix) != 3:
        raise ValueError(f"품목코드 앞 3자리는 필수입니다 (입력값: {item_code_prefix})")

    # 숫자만 허용하는 경우 활성화
    # if not item_code_prefix.isdigit():
    #     raise ValueError(f"품목코드 앞 3자리는 숫자여야 합니다 (입력값: {item_code_prefix})")

    # 1. 분류 코드 조회
    product_line = db.query(ProductLine).filter(ProductLine.id == product_line_id).first()
    if not product_line:
        raise ValueError(f"대분류(제품라인) ID {product_line_id}를 찾을 수 없습니다")

    part_group = db.query(PartGroup).filter(PartGroup.id == part_group_id).first()
    if not part_group:
        raise ValueError(f"소분류(품목군) ID {part_group_id}를 찾을 수 없습니다")

    # 재질 코드 (선택, 미선택 시 XX)
    material_code = "XX"
    if material_id:
        material = db.query(Material).filter(Material.id == material_id).first()
        if material:
            material_code = material.code

    # 후처리 코드 (선택, 미선택 시 NN)
    treatment_code = "NN"
    if treatment_id:
        treatment = db.query(Treatment).filter(Treatment.id == treatment_id).first()
        if treatment:
            treatment_code = treatment.code

    # 레벨 코드 (필수, v0.20.0)
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise ValueError(f"레벨 ID {level_id}를 찾을 수 없습니다")
    level_code = level.code  # 예: "R", "M", "O", "C", "S", "P", "K", "F"

    # 2. 코드 추출
    product_line_code = product_line.code  # 예: "HB01"
    part_group_code = part_group.code      # 예: "DCP"

    # 3. 품목코드 suffix 처리
    if item_code_suffix and len(item_code_suffix) == 2:
        # 사용자가 직접 입력한 suffix 사용 - 중복 체크 필요
        item_code = f"{item_code_prefix}{item_code_suffix}"

        # 중복 체크: 동일한 품번 구성요소가 이미 존재하는지 확인
        # (제품라인 + 품목군 + 품목코드 + 재질 + 후처리 + 레벨이 모두 같아야 중복)
        existing_query = db.query(Part)\
            .filter(Part.product_line_id == product_line_id)\
            .filter(Part.part_group_id == part_group_id)\
            .filter(Part.item_code == item_code)\
            .filter(Part.material_id == material_id)\
            .filter(Part.treatment_id == treatment_id)\
            .filter(Part.level_id == level_id)

        # 수정 모드일 때 자기 자신은 제외
        if exclude_part_id:
            existing_query = existing_query.filter(Part.id != exclude_part_id)

        existing_part = existing_query.first()
        if existing_part:
            raise ValueError(f"품목코드 '{item_code}'가 이미 존재합니다. (품번: {existing_part.part_number_display})")

        final_suffix = item_code_suffix
    else:
        # 자동 생성: 해당 대분류+소분류+prefix 내 최대 품목코드(뒤 2자리) 조회
        max_item_code = db.query(func.max(Part.item_code))\
            .filter(Part.product_line_id == product_line_id)\
            .filter(Part.part_group_id == part_group_id)\
            .filter(Part.item_code.like(f"{item_code_prefix}%"))\
            .scalar()

        # 4. 새 품목코드(뒤 2자리) 생성
        if max_item_code and len(max_item_code) == 5:
            try:
                # 뒤 2자리 추출하여 +1
                suffix_num = int(max_item_code[3:]) + 1
                if suffix_num > 99:
                    raise ValueError(f"품목코드 자동채번 범위 초과 (prefix: {item_code_prefix}, 최대: 99)")
            except ValueError as e:
                if "범위 초과" in str(e):
                    raise
                suffix_num = 1
        else:
            suffix_num = 1

        final_suffix = str(suffix_num).zfill(2)  # 2자리
        item_code = f"{item_code_prefix}{final_suffix}"  # 5자리 (3 + 2)

    # 5. 품번 생성 (v0.20.0 - 레벨 코드 추가)
    # 시스템용: HB01DCP00101A6NKR (하이픈 없음)
    part_number = f"{product_line_code}{part_group_code}{item_code}{material_code}{treatment_code}{level_code}"
    # 표시용: HB01-DCP-001-01-A6-NK [R] (하이픈 포함, 레벨은 공백 + 대괄호로 표시)
    part_number_display = f"{product_line_code}-{part_group_code}-{item_code_prefix}-{final_suffix}-{material_code}-{treatment_code} [{level_code}]"

    return part_number, part_number_display, item_code


def validate_part_number_v2(part_number: str) -> bool:
    """
    품번 형식 검증 (v0.10.0)

    Args:
        part_number: 검증할 품번 (시스템용 또는 표시용)

    Returns:
        bool: 유효한 품번이면 True
    """
    if not part_number:
        return False

    # 하이픈 제거 (표시용 품번 처리)
    clean_number = part_number.replace("-", "")

    # 최소 길이 체크 (대분류3 + 소분류2 + 품목코드5 + 재질2 + 후처리2 = 14자리)
    if len(clean_number) < 14:
        return False

    # 최대 길이 체크 (소분류가 3자리인 경우 = 15자리)
    if len(clean_number) > 16:
        return False

    return True


def parse_part_number_v2(part_number: str) -> dict:
    """
    품번 파싱 (v0.10.0)

    Args:
        part_number: 파싱할 품번 (예: HB1DCP00001A6NK 또는 HB1-DCP-00001-A6-NK)

    Returns:
        dict: {
            'product_line': 'HB1',
            'part_group': 'DCP',
            'item_code': '00001',
            'material': 'A6',
            'treatment': 'NK'
        }
    """
    # 표시용 품번인 경우 하이픈으로 분리
    if "-" in part_number:
        parts = part_number.split("-")
        if len(parts) == 5:
            return {
                "product_line": parts[0],
                "part_group": parts[1],
                "item_code": parts[2],
                "material": parts[3],
                "treatment": parts[4]
            }

    # 시스템용 품번 파싱 (고정 길이 기준)
    # 대분류(3) + 소분류(2~3) + 품목코드(5) + 재질(2) + 후처리(2)
    if len(part_number) >= 14:
        return {
            "product_line": part_number[:3],
            "part_group": part_number[3:-9],  # 가변 길이
            "item_code": part_number[-9:-4],
            "material": part_number[-4:-2],
            "treatment": part_number[-2:]
        }

    raise ValueError(f"유효하지 않은 품번입니다: {part_number}")


# ============================================================================
# Legacy 함수 (하위 호환성 유지)
# ============================================================================

def generate_part_number(
    db: Session,
    major_category_id: int,
    middle_category_id: int,
    minor_category_id: int
) -> tuple:
    """
    [Legacy] 품번 자동생성

    v0.10.0 이전 버전 호환용.
    신규 코드에서는 generate_part_number_v2()를 사용하세요.

    Args:
        db: 데이터베이스 세션
        major_category_id: 대분류 ID
        middle_category_id: 중분류 ID (optional)
        minor_category_id: 소분류 ID

    Returns:
        (part_number, part_number_display): 시스템용 품번, 표시용 품번

    Raises:
        ValueError: 분류 코드를 찾을 수 없는 경우
    """

    # 1. 분류 코드 조회
    major = db.query(MajorCategory).filter(MajorCategory.id == major_category_id).first()
    if not major:
        raise ValueError(f"대분류 ID {major_category_id}를 찾을 수 없습니다")

    middle = None
    if middle_category_id:
        middle = db.query(MiddleCategory).filter(MiddleCategory.id == middle_category_id).first()
        if not middle:
            raise ValueError(f"중분류 ID {middle_category_id}를 찾을 수 없습니다")

    minor = db.query(MinorCategory).filter(MinorCategory.id == minor_category_id).first()
    if not minor:
        raise ValueError(f"소분류 ID {minor_category_id}를 찾을 수 없습니다")

    # 2. 코드 조합 (대분류 + 중분류 + 소분류)
    major_code = major.code  # 예: "A"
    middle_code = middle.code if middle else "00"  # 예: "01" 또는 "00" (없을 경우)
    minor_code = minor.code  # 예: "01"

    # 3. 해당 분류의 마지막 일련번호 조회
    prefix = f"{major_code}{middle_code}{minor_code}"

    # 같은 분류의 마지막 부품 조회
    last_part = db.query(Part)\
        .filter(Part.part_number.like(f"{prefix}%"))\
        .order_by(desc(Part.part_number))\
        .first()

    # 4. 일련번호 생성
    if last_part:
        # 마지막 품번에서 일련번호 추출 (예: A010001 -> 0001)
        last_serial = last_part.part_number[len(prefix):]
        try:
            serial_number = int(last_serial) + 1
        except ValueError:
            # 파싱 실패 시 1부터 시작
            serial_number = 1
    else:
        # 첫 번째 부품
        serial_number = 1

    # 5. 품번 생성
    serial_str = f"{serial_number:04d}"  # 4자리 일련번호 (0001, 0002, ...)
    part_number = f"{prefix}{serial_str}"  # 시스템용 (하이픈 없음)
    part_number_display = f"{major_code}{middle_code}-{minor_code}-{serial_str}"  # 표시용

    return part_number, part_number_display


def validate_part_number(part_number: str) -> bool:
    """
    [Legacy] 품번 형식 검증

    Args:
        part_number: 검증할 품번

    Returns:
        bool: 유효한 품번이면 True
    """
    if not part_number:
        return False

    # 최소 길이 체크 (대분류1 + 중분류2 + 소분류2 + 일련번호4 = 9자리)
    if len(part_number) < 9:
        return False

    # 영문자 + 숫자 조합 체크
    if not part_number[0].isalpha():
        return False

    if not part_number[1:].isdigit():
        return False

    return True


def parse_part_number(part_number: str) -> dict:
    """
    [Legacy] 품번 파싱

    Args:
        part_number: 파싱할 품번 (예: A010001)

    Returns:
        dict: {major: "A", middle: "01", minor: "00", serial: "01"}
    """
    if not validate_part_number(part_number):
        raise ValueError(f"유효하지 않은 품번입니다: {part_number}")

    return {
        "major": part_number[0],
        "middle": part_number[1:3],
        "minor": part_number[3:5],
        "serial": part_number[5:]
    }
