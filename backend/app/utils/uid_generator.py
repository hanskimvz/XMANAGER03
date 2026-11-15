"""
UID 생성 유틸리티
각 엔티티별 고유 ID를 생성합니다.

v0.12.0: Part UID 추가
- 형식: PT-XXXXXXXX (8자리 대문자 16진수)
- 품번 + 생성시간 기반 해시
- 생성 후 변경 불가 (바코드/QR용)
"""

import hashlib
from datetime import datetime
from typing import Optional


def generate_part_uid(part_number: str, created_at: Optional[datetime] = None) -> str:
    """
    부품 고유 ID 생성 (Part UID)

    품번과 생성시간을 조합하여 고유한 ID를 생성합니다.
    생성된 UID는 변경되지 않으며, 바코드/QR 코드에 사용됩니다.

    Args:
        part_number: 품번 (예: "HB01DCP00101A6NK")
        created_at: 생성 시간 (없으면 현재 시간 사용)

    Returns:
        str: 고유 ID (예: "PT-3F7A2B1C")

    Examples:
        >>> generate_part_uid("HB01DCP00101A6NK")
        'PT-3F7A2B1C'
    """
    if created_at is None:
        created_at = datetime.now()

    # 품번 + ISO 형식 타임스탬프를 시드로 사용
    seed = f"{part_number}:{created_at.isoformat()}"

    # SHA256 해시 생성 후 앞 8자리 추출
    hash_value = hashlib.sha256(seed.encode('utf-8')).hexdigest()[:8].upper()

    return f"PT-{hash_value}"


def generate_uid_with_prefix(prefix: str, seed_value: str, timestamp: Optional[datetime] = None) -> str:
    """
    범용 UID 생성 함수

    다른 엔티티에도 확장 가능한 UID 생성 함수입니다.

    Args:
        prefix: 접두사 (예: "PT", "PO", "WO", "BP")
        seed_value: 해시 생성에 사용할 값
        timestamp: 타임스탬프 (없으면 현재 시간)

    Returns:
        str: 고유 ID (예: "PO-A1B2C3D4")

    Usage:
        # 발주서 UID
        generate_uid_with_prefix("PO", order_number)

        # 작업지시서 UID
        generate_uid_with_prefix("WO", work_order_number)

        # 거래처 UID
        generate_uid_with_prefix("BP", partner_code)
    """
    if timestamp is None:
        timestamp = datetime.now()

    seed = f"{seed_value}:{timestamp.isoformat()}"
    hash_value = hashlib.sha256(seed.encode('utf-8')).hexdigest()[:8].upper()

    return f"{prefix}-{hash_value}"


# UID 접두사 상수 정의
class UIDPrefix:
    """UID 접두사 상수"""
    PART = "PT"              # 부품
    PURCHASE_ORDER = "PO"    # 발주서
    WORK_ORDER = "WO"        # 작업지시서
    BUSINESS_PARTNER = "BP"  # 거래처
    INVENTORY_LOT = "LT"     # 재고 LOT
