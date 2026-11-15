# -*- coding: utf-8 -*-
"""견적 자동산출 서비스 검증.

docs/견적기능/인터림_원가데이터/검증결과.md 의 산출 검증 4건(원화, 조립체)을
반드시 통과해야 한다. 마진 = 엑셀 기준(2·4ch=60%, 6ch=56%).
"""
import pytest

from app.services.quote_service import suggest_price, QuoteConfig, parse_order_code


# 엑셀 기준 마진(과거 실제) — 검증용
EXCEL_CFG = QuoteConfig(channel_margins={2: 60.0, 4: 60.0, 6: 56.0})

VALIDATION_CASES = [
    ("HXB13AS-RJS-B-O2-S1-S20", 2, 357000),
    ("HXB13AS-PSD-B-O2-S1-D55", 3, 367000),
    ("HXB15AS-RJS-B-O4-M3-S20", 2, 476000),
    ("HXB15AS-PSD-B-O4-M3-D55", 3, 481000),
]


@pytest.mark.parametrize("code,length_m,expected", VALIDATION_CASES)
def test_validation_cases(code, length_m, expected):
    r = suggest_price(order_code=code, length_m=length_m, quantity=1, currency="KRW", config=EXCEL_CFG)
    assert r["unit_price"] == expected, f"{code}: 기대 {expected}, 산출 {r['unit_price']}"


def test_component_breakdown_case1():
    """1번 케이스 컴포넌트 단위(사양서 §77)."""
    r = suggest_price(order_code="HXB13AS-RJS-B-O2-S1-S20", length_m=2, quantity=1, currency="KRW", config=EXCEL_CFG)
    bd = r["cost_breakdown"]
    assert bd["connector_a"] == pytest.approx(194006.25)  # 77602.5 / 0.4
    assert bd["connector_b"] == pytest.approx(3000.0)      # 2 × 1500
    assert bd["cable"] == pytest.approx(5600.0)            # 2 × 2800
    assert bd["assembly"] == pytest.approx(72000.0)        # 2ch 1단
    assert bd["subtotal"] == pytest.approx(274606.25)
    assert r["applied"]["margin_rate"] == pytest.approx(0.60)


def test_model_c_default_4ch():
    """모델 C 기본(4ch=55%)이면 4ch 케이스는 440,000(사양서 §79 정상)."""
    r = suggest_price(order_code="HXB15AS-RJS-B-O4-M3-S20", length_m=2, quantity=1, currency="KRW",
                      config=QuoteConfig())  # 기본 = 2:60/4:55/6:56
    assert r["unit_price"] == 440000


def test_parse_order_code():
    p = parse_order_code("HXB13AS-RJS-B-O2-S1-S20")
    assert p.size == "HXB13" and p.form == "RJS" and p.material == "B"
    assert p.core == "O2" and p.channel == 2 and p.mode == "S" and p.is_sa is False


def test_parse_failure_returns_warnings():
    r = suggest_price(order_code="깨진코드", length_m=1, quantity=1, currency="KRW", config=EXCEL_CFG)
    assert r["unit_price"] is None
    assert r["warnings"]


def test_override_extra_item():
    """상세 산출 패널: 특수케이블 등 기타 항목을 더하면 소계·단가에 반영."""
    r = suggest_price(order_code="HXB13AS-RJS-B-O2-S1-S20", length_m=2, quantity=1, currency="KRW",
                      config=EXCEL_CFG, overrides={"extra_items": [{"label": "특수케이블", "amount": 100000}]})
    assert r["cost_breakdown"]["extra_total"] == pytest.approx(100000.0)
    assert r["cost_breakdown"]["subtotal"] == pytest.approx(374606.25)
    assert r["unit_price"] == 487000  # 374606.25 × 1.3 = 486988.125 → ROUNDUP(-3)


def test_override_margin_and_assembly():
    """마진·조립비 직접 지정 시 서버가 그 값으로 재계산."""
    r = suggest_price(order_code="HXB13AS-RJS-B-O2-S1-S20", length_m=2, quantity=1, currency="KRW",
                      config=EXCEL_CFG, overrides={"margin_rate": 50, "assembly": 80000})
    bd = r["cost_breakdown"]
    assert bd["connector_a"] == pytest.approx(155205.0)  # 77602.5 / 0.5
    assert bd["assembly"] == pytest.approx(80000.0)
    assert r["applied"]["margin_source"] == "override"
    # 155205 + 3000 + 5600 + 80000 = 243805 → ×1.3 = 316946.5 → ROUNDUP(-3)
    assert r["unit_price"] == 317000
