"""
부품명 헬퍼 함수 (v0.21.0)

부품명이 없거나 "부품"인 경우, 설명(description)에서 "/" 기준으로
처음 3개 항목을 추출하여 부품명으로 사용

예: "HXB11 / 리셉터클 / 벡쉘L/로우 / 기본모델 / AL6061 / 없음 / 부품"
    → "HXB11 리셉터클 벡쉘L/로우"
"""

import re
from typing import Optional


def is_valid_part_name(part_name: Optional[str]) -> bool:
    """
    부품명이 유효한지 확인
    빈 값이거나 "부품"인 경우 무효
    """
    if not part_name:
        return False
    trimmed = part_name.strip()
    return trimmed != '' and trimmed != '부품'


def extract_part_name_from_description(description: Optional[str]) -> Optional[str]:
    """
    설명에서 부품명 추출 (/ 기준 처음 3개)

    Args:
        description: 설명 문자열

    Returns:
        추출된 부품명 또는 None
    """
    if not description:
        return None

    # " / " 또는 "/" 기준으로 분리 (앞뒤 공백 제거)
    parts = re.split(r'\s*/\s*', description)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return None

    # 처음 3개 항목을 공백으로 연결
    result = ' '.join(parts[:3])
    return result if result else None


def get_part_name(
    part_name: Optional[str],
    description: Optional[str],
    fallback: Optional[str] = None
) -> str:
    """
    유효한 부품명 반환

    1. part_name이 유효하면 그대로 사용
    2. 아니면 description에서 추출
    3. 그것도 없으면 fallback 사용

    Args:
        part_name: 원래 부품명
        description: 설명 필드
        fallback: 대체값 (예: 품번)

    Returns:
        유효한 부품명
    """
    # 부품명이 유효하면 그대로 사용
    if is_valid_part_name(part_name):
        return part_name

    # 설명에서 부품명 추출 시도
    extracted = extract_part_name_from_description(description)
    if extracted:
        return extracted

    # fallback 사용
    if fallback:
        return fallback

    # 원래 부품명 반환 (빈 값 또는 "부품")
    return part_name or ''
