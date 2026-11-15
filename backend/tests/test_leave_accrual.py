"""연차 발생 엔진 단위 테스트 (v0.45.0) — 엑셀 예시·법정 검산."""
from datetime import date
from app.services.leave_accrual_service import ceil_half, compute_grant, legal_entitlement


def test_ceil_half():
    assert ceil_half(5.0) == 5.0
    assert ceil_half(12.5) == 12.5
    assert ceil_half(12.3) == 12.5
    assert ceil_half(12.6) == 13.0
    assert ceil_half(1.25) == 1.5


def test_compute_grant_sep_hire():
    """2025.09 입사 → FY 3 / 13.5 / 15 (비례분 일수 기준)."""
    h = date(2025, 9, 1)
    assert compute_grant(h, 2024) == 0
    assert compute_grant(h, 2025) == 3        # 10·11·12월
    # 다음해 = 비례(15×122일/365=5.01→반차올림 5.5) + 월차8 = 13.5
    assert compute_grant(h, 2026) == 13.5
    assert compute_grant(h, 2027) == 15      # n=2, 가산 0
    assert compute_grant(h, 2030) == 16      # n=5, 근속가산 +1 ((n-2)//2)


def test_compute_grant_jan_hire():
    h = date(2025, 1, 1)
    assert compute_grant(h, 2025) == 11       # 2~12월
    assert compute_grant(h, 2026) == 15       # 비례(15×365/365=15) + 월차0, 상한 15


def test_compute_grant_seniority_bonus():
    """3년차+ 회계연도 발생 = 15 + 근속가산 (가산=(n−2)//2, n=fy−HY, 상한 25)."""
    h = date(2020, 3, 1)
    assert compute_grant(h, 2023) == 15   # n=3, 가산 0
    assert compute_grant(h, 2024) == 16   # n=4, +1 (완성근속 3년)
    assert compute_grant(h, 2026) == 17   # n=6, +2
    assert compute_grant(h, 2042) == 25   # n=22, 상한
    assert compute_grant(h, 2045) == 25


def test_compute_grant_proportional_days():
    """비례분은 전년 재직일수 기준(상한 15·반차 올림)."""
    # 3월 입사: 재직 306일 → 15×306/365=12.57→13.0, +월차2 = 15.0
    assert compute_grant(date(2025, 3, 1), 2026) == 15.0
    # 12월 입사: 재직 31일 → 15×31/365=1.27→1.5, +월차11 = 12.5
    assert compute_grant(date(2025, 12, 1), 2026) == 12.5
    # 윤년 1월 입사: 366일이어도 상한 15
    assert compute_grant(date(2024, 1, 1), 2025) == 15


def test_legal_one_year_is_26():
    """1년 만근 = 월차11 + 연차15 = 26 (근로기준법 canonical)."""
    assert legal_entitlement(date(2025, 9, 1), date(2026, 9, 1)) == 26


def test_legal_seniority_bonus():
    """3년차 근속가산 +1 (15→16)."""
    h = date(2025, 9, 1)
    # 만3년: 월차11 + y1 15 + y2 15 + y3 16 = 57
    assert legal_entitlement(h, date(2028, 9, 1)) == 57
