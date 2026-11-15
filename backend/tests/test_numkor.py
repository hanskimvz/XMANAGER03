"""한글 금융 금액 변환 테스트"""

from decimal import Decimal

import pytest

from app.utils.numkor import num_to_korean, to_korean_amount


class TestNumToKorean:
    @pytest.mark.parametrize("n,expected", [
        (0, "영"),
        (1, "일"),
        (5, "오"),
        (9, "구"),
        (10, "일십"),
        (11, "일십일"),
        (99, "구십구"),
        (100, "일백"),
        (1000, "일천"),
        (10000, "일만"),
        (99999, "구만구천구백구십구"),
        (100000000, "일억"),
    ])
    def test_basic(self, n, expected):
        assert num_to_korean(n) == expected

    def test_153000(self):
        assert num_to_korean(153_000) == "일십오만삼천"

    def test_1234567(self):
        assert num_to_korean(1_234_567) == "일백이십삼만사천오백육십칠"

    def test_negative_prefixed(self):
        assert num_to_korean(-100).startswith("마이너스")

    def test_one_followed_by_zero_in_chunk(self):
        # 10001 = 1만 + 1 → 일만일
        assert num_to_korean(10_001) == "일만일"


class TestToKoreanAmount:
    @pytest.mark.parametrize("amount,expected", [
        (0, "일금영원整"),
        (1, "일금일원整"),
        (153_000, "일금일십오만삼천원整"),
        (1_000_000, "일금일백만원整"),
        (Decimal("153000"), "일금일십오만삼천원整"),
    ])
    def test_basic(self, amount, expected):
        assert to_korean_amount(amount) == expected

    def test_decimal_truncated(self):
        # 소수점 이하는 절사
        assert to_korean_amount(Decimal("153000.99")) == "일금일십오만삼천원整"

    def test_none_treated_as_zero(self):
        assert to_korean_amount(None) == "일금영원整"

    def test_custom_suffix(self):
        assert to_korean_amount(1000, suffix="원") == "일금일천원"
        assert to_korean_amount(1000, suffix="") == "일금일천"
