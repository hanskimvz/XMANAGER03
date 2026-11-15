"""
품번 파싱 유틸리티 (v0.21.0)

직접 입력된 품번을 파싱하여 각 구성요소의 ID를 자동으로 매핑합니다.

품번 구조 예시:
- HB05-PLP-FSO-01-S6-HB [C]
- COTS-SO-S31-06-NB-NN [R]

파싱 규칙:
1. 하이픈(-)으로 구분
2. 마지막에 [레벨코드] 형식으로 레벨 표시 (선택)
3. 구성요소: 제품라인-품목군-품목코드앞3-품목코드뒤2-재질-후처리 [레벨]
"""

import re
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session


def parse_part_number(
    db: Session,
    part_number: str
) -> Dict[str, Any]:
    """
    품번을 파싱하여 각 구성요소의 ID를 반환합니다.

    Args:
        db: 데이터베이스 세션
        part_number: 파싱할 품번 (예: HB05-PLP-FSO-01-S6-HB [C])

    Returns:
        Dict containing:
        - success: 파싱 성공 여부
        - product_line_id: 제품라인 ID (또는 None)
        - part_group_id: 품목군 ID (또는 None)
        - item_code: 품목코드 5자리 (또는 None)
        - material_id: 재질 ID (또는 None)
        - treatment_id: 후처리 ID (또는 None)
        - level_id: 레벨 ID (또는 None)
        - errors: 파싱 실패 항목 목록
    """
    from app.models.code_master import ProductLine, PartGroup, Material, Treatment, Level

    result = {
        'success': False,
        'product_line_id': None,
        'part_group_id': None,
        'item_code': None,
        'material_id': None,
        'treatment_id': None,
        'level_id': None,
        'errors': []
    }

    if not part_number:
        result['errors'].append('품번이 비어있습니다.')
        return result

    # 레벨 추출 (대괄호 안의 값)
    level_match = re.search(r'\[([A-Za-z0-9]+)\]', part_number)
    level_code = None
    if level_match:
        level_code = level_match.group(1).upper()
        # 레벨 부분 제거
        part_number_clean = re.sub(r'\s*\[[A-Za-z0-9]+\]', '', part_number).strip()
    else:
        part_number_clean = part_number.strip()

    # 하이픈으로 분리
    parts = part_number_clean.split('-')

    # 최소 6개 구성요소 필요: 제품라인-품목군-품목코드앞-품목코드뒤-재질-후처리
    if len(parts) < 6:
        result['errors'].append(f'품번 구성요소가 부족합니다. (필요: 6개, 현재: {len(parts)}개)')
        return result

    # 각 구성요소 추출
    product_line_code = parts[0].upper()
    part_group_code = parts[1].upper()
    item_code_prefix = parts[2].upper()
    item_code_suffix = parts[3].zfill(2)  # 2자리로 패딩
    material_code = parts[4].upper()
    treatment_code = parts[5].upper()

    # 품목코드 결합 (앞 3자리 + 뒤 2자리)
    item_code = f"{item_code_prefix}{item_code_suffix}"

    matched_count = 0

    # 제품라인 ID 조회
    product_line = db.query(ProductLine).filter(
        ProductLine.code == product_line_code,
        ProductLine.is_active == True
    ).first()
    if product_line:
        result['product_line_id'] = product_line.id
        matched_count += 1
    else:
        result['errors'].append(f'제품라인 코드 "{product_line_code}"를 찾을 수 없습니다.')

    # 품목군 ID 조회
    part_group = db.query(PartGroup).filter(
        PartGroup.code == part_group_code,
        PartGroup.is_active == True
    ).first()
    if part_group:
        result['part_group_id'] = part_group.id
        matched_count += 1
    else:
        result['errors'].append(f'품목군 코드 "{part_group_code}"를 찾을 수 없습니다.')

    # 품목코드 저장
    if len(item_code_prefix) >= 2 and len(item_code_suffix) == 2:
        result['item_code'] = item_code
        matched_count += 1
    else:
        result['errors'].append(f'품목코드 형식이 올바르지 않습니다. (앞: {item_code_prefix}, 뒤: {item_code_suffix})')

    # 재질 ID 조회
    material = db.query(Material).filter(
        Material.code == material_code,
        Material.is_active == True
    ).first()
    if material:
        result['material_id'] = material.id
        matched_count += 1
    else:
        result['errors'].append(f'재질 코드 "{material_code}"를 찾을 수 없습니다.')

    # 후처리 ID 조회
    treatment = db.query(Treatment).filter(
        Treatment.code == treatment_code,
        Treatment.is_active == True
    ).first()
    if treatment:
        result['treatment_id'] = treatment.id
        matched_count += 1
    else:
        result['errors'].append(f'후처리 코드 "{treatment_code}"를 찾을 수 없습니다.')

    # 레벨 ID 조회 (있는 경우)
    if level_code:
        level = db.query(Level).filter(
            Level.code == level_code,
            Level.is_active == True
        ).first()
        if level:
            result['level_id'] = level.id
            matched_count += 1
        else:
            result['errors'].append(f'레벨 코드 "{level_code}"를 찾을 수 없습니다.')

    # 최소 4개 이상 매칭되면 성공으로 간주
    result['success'] = matched_count >= 4

    return result


def parse_excel_part_number(
    db: Session,
    product_line_code: str,
    part_group_code: str,
    item_code_prefix: str,
    item_code_suffix: str,
    material_code: str,
    treatment_code: str,
    level_code: str
) -> Dict[str, Any]:
    """
    엑셀에서 분리된 품번 구성요소를 ID로 변환합니다.

    Args:
        db: 데이터베이스 세션
        product_line_code: 제품라인 코드 (예: HB05)
        part_group_code: 품목군 코드 (예: PLP)
        item_code_prefix: 품목코드 앞 3자리 (예: FSO)
        item_code_suffix: 품목코드 뒤 2자리 (예: 01)
        material_code: 재질 코드 (예: S6)
        treatment_code: 후처리 코드 (예: HB)
        level_code: 레벨 코드 (예: C)

    Returns:
        Dict containing parsed IDs and errors
    """
    from app.models.code_master import ProductLine, PartGroup, Material, Treatment, Level

    result = {
        'success': False,
        'product_line_id': None,
        'part_group_id': None,
        'item_code': None,
        'material_id': None,
        'treatment_id': None,
        'level_id': None,
        'errors': []
    }

    matched_count = 0

    # 제품라인 ID 조회
    if product_line_code:
        product_line = db.query(ProductLine).filter(
            ProductLine.code == product_line_code.strip().upper(),
            ProductLine.is_active == True
        ).first()
        if product_line:
            result['product_line_id'] = product_line.id
            matched_count += 1
        else:
            result['errors'].append(f'제품라인 코드 "{product_line_code}"를 찾을 수 없습니다.')

    # 품목군 ID 조회
    if part_group_code:
        part_group = db.query(PartGroup).filter(
            PartGroup.code == part_group_code.strip().upper(),
            PartGroup.is_active == True
        ).first()
        if part_group:
            result['part_group_id'] = part_group.id
            matched_count += 1
        else:
            result['errors'].append(f'품목군 코드 "{part_group_code}"를 찾을 수 없습니다.')

    # 품목코드 결합
    if item_code_prefix and item_code_suffix:
        prefix = item_code_prefix.strip().upper()
        suffix = str(item_code_suffix).strip().zfill(2)
        result['item_code'] = f"{prefix}{suffix}"
        matched_count += 1

    # 재질 ID 조회
    if material_code:
        material = db.query(Material).filter(
            Material.code == material_code.strip().upper(),
            Material.is_active == True
        ).first()
        if material:
            result['material_id'] = material.id
            matched_count += 1
        else:
            result['errors'].append(f'재질 코드 "{material_code}"를 찾을 수 없습니다.')

    # 후처리 ID 조회
    if treatment_code:
        treatment = db.query(Treatment).filter(
            Treatment.code == treatment_code.strip().upper(),
            Treatment.is_active == True
        ).first()
        if treatment:
            result['treatment_id'] = treatment.id
            matched_count += 1
        else:
            result['errors'].append(f'후처리 코드 "{treatment_code}"를 찾을 수 없습니다.')

    # 레벨 ID 조회
    if level_code:
        level = db.query(Level).filter(
            Level.code == level_code.strip().upper(),
            Level.is_active == True
        ).first()
        if level:
            result['level_id'] = level.id
            matched_count += 1
        else:
            result['errors'].append(f'레벨 코드 "{level_code}"를 찾을 수 없습니다.')

    # 최소 4개 이상 매칭되면 성공으로 간주
    result['success'] = matched_count >= 4

    return result
