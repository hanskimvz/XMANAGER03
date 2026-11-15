"""한글 금액 표기 유틸 — 견적서/PI 등에 사용.

예시: 153000 -> "일금일십오만삼천원整"
     1000000 -> "일금일백만원整"
     0 -> "일금영원整"

금융 문서 관습대로 '일십', '일백', '일천', '일만' 형태로 1을 항상 표기 (위변조 방지).
"""

from decimal import Decimal
from typing import Union

_DIGITS = "영일이삼사오육칠팔구"
_UNITS = ("", "십", "백", "천")
_BIG_UNITS = ("", "만", "억", "조", "경")


def _chunk_to_korean(chunk: int) -> str:
    """0~9999 범위 정수를 한글로 변환."""
    if chunk == 0:
        return ""
    parts = []
    n = chunk
    for u in range(4):
        d = n % 10
        n //= 10
        if d:
            # 1도 항상 표기 (일십·일백·일천 패턴)
            parts.append(_DIGITS[d] + _UNITS[u])
    return "".join(reversed(parts))


def num_to_korean(num: int) -> str:
    """정수를 금융 한글 표기로 변환."""
    if num == 0:
        return _DIGITS[0]
    if num < 0:
        return "마이너스" + num_to_korean(-num)

    chunks = []
    chunk_idx = 0
    while num > 0:
        chunk = num % 10000
        if chunk:
            chunks.append(_chunk_to_korean(chunk) + _BIG_UNITS[chunk_idx])
        num //= 10000
        chunk_idx += 1
    return "".join(reversed(chunks))


def to_korean_amount(amount: Union[int, Decimal, float], suffix: str = "원整") -> str:
    """금액을 '일금...원整' 형태로 변환. 소수점 이하는 절사."""
    if amount is None:
        return f"일금{_DIGITS[0]}{suffix}"
    int_part = int(Decimal(str(amount)))
    return f"일금{num_to_korean(int_part)}{suffix}"
