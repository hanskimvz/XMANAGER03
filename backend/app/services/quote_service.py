"""견적 자동산출 서비스 (Phase 1).

사양서(docs/견적기능/Phase1_견적산출_사양서.md) §2·§6·§7 파이프라인:
  오더코드 파싱 → 원가 조회(+인상률) → 조립체 계산 → 마진·통화·국내프리미엄 → 단가

핵심 원칙(틀리기 쉬움):
  - 마진: 판매가 = 원가 / (1 − 마진율)   (원가×(1+마진) 아님)
  - 마진 결정 = 모델 C: clamp(채널기준(채널) + 고객델타, 하한). resolve_margin 한 곳에 집중.
  - 국내(원화): 합계 × 1.3 후 ₩1,000 올림. USD: 프리미엄 없이 $1 올림.
  - 가격 인상률: 비율(%)로만, 상수 가산 금지.
  - 부츠(D55/S20/S09) 가격 무관. 엔드페이스 = 채널수×1,500. SA면 커넥터B=커넥터A.
"""
import math
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from app.services.quote_cost_source import get_interim_cost_source

logger = logging.getLogger(__name__)

# 채널 기준 마진(%) — 모델 C 기본(§7). 관리자 설정(app_setting)으로 override.
DEFAULT_CHANNEL_MARGINS: Dict[int, float] = {2: 60.0, 4: 55.0, 6: 56.0}
MARGIN_FLOOR: Dict[int, float] = {6: 56.0}   # 6ch 하한
DEFAULT_EXCHANGE_RATE = 1100.0
DEFAULT_DOMESTIC_PREMIUM = 1.3

_FORMS = {"PSD", "RJS", "RJN", "RJL", "RQS", "RQN", "RQL", "PRD", "RRD"}
_ENDFACES = {"LC", "SC", "PC", "APC", "FC", "ST"}
_HEX_CH = {"A": 10, "C": 12, "E": 14, "G": 16}


@dataclass
class QuoteConfig:
    channel_margins: Dict[int, float] = field(default_factory=lambda: dict(DEFAULT_CHANNEL_MARGINS))
    exchange_rate: float = DEFAULT_EXCHANGE_RATE
    domestic_premium: float = DEFAULT_DOMESTIC_PREMIUM
    price_increase_global: float = 0.0                       # 전역 인상률(%)
    price_increase_by_item: Dict[str, float] = field(default_factory=dict)  # 오더코드별 인상률(%)


@dataclass
class ParsedCode:
    size: Optional[str] = None
    form: Optional[str] = None
    material: Optional[str] = None
    core: Optional[str] = None       # 'O2'
    channel: Optional[int] = None    # 2
    mode: Optional[str] = None       # 'S'/'M'
    is_sa: bool = False
    endface: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def parse_order_code(code: str) -> ParsedCode:
    """오더코드 → 토큰(사이즈·형태·재질·채널·모드·SA·엔드페이스). 사양서 §4.
    실패는 예외 없이 warnings로 반환(수기 단가 허용)."""
    p = ParsedCode()
    raw = (code or "").strip().upper()
    if not raw:
        p.warnings.append("오더코드가 비어 있습니다.")
        return p
    segs = [s for s in raw.replace(" ", "").split("-") if s]
    # SA 플래그(양단 동일) 분리
    p.is_sa = any(s == "SA" for s in segs)
    segs = [s for s in segs if s != "SA"]
    # PRODUCT: HXB13AS → AS(조립표시) 제거
    if segs:
        prod = segs[0]
        if prod.endswith("AS"):
            prod = prod[:-2]
        p.size = prod
    # FORM
    if len(segs) > 1 and segs[1] in _FORMS:
        p.form = segs[1]
    # MATERIAL (B=Al / S=SUS)
    if len(segs) > 2 and segs[2] in ("B", "S"):
        p.material = segs[2]
    # CHANNEL (Oxx) — 뒤 세그먼트에서 첫 'O?' 2자리
    for s in segs[3:]:
        if len(s) == 2 and s[0] == "O":
            p.core = s
            last = s[1]
            if last.isdigit():
                p.channel = int(last)
            elif last in _HEX_CH:
                p.channel = _HEX_CH[last]
            break
    # MODE (S?/M? 2자리, 부츠 S20/D55 등과 구분)
    for s in segs[3:]:
        if s == p.core:
            continue
        if len(s) == 2 and s[0] in ("S", "M") and s[1].isdigit():
            p.mode = s[0]
            break
    # ENDFACE (있으면)
    for s in segs:
        if s in _ENDFACES:
            p.endface = s
            break
    if not p.size:
        p.warnings.append("사이즈(HXB..) 인식 실패")
    if not p.form:
        p.warnings.append("형태(PSD/RJS..) 인식 실패")
    if not p.channel:
        p.warnings.append("채널(Oxx) 인식 실패")
    if not p.mode:
        p.warnings.append("모드(S/M) 인식 실패")
    return p


def resolve_margin(customer, channel: int, config: QuoteConfig) -> float:
    """모델 C(§7): clamp(채널기준(채널) + 고객델타, 하한). 반환 = 소수(예 0.60).

    ②(고객×채널 override)로 확장 시 이 함수 내부 + 오버라이드 표만 추가 — 호출부 불변.
    """
    base = config.channel_margins.get(channel)
    if base is None:
        base = 55.0  # 미정 채널 기본(8/10/12/16ch는 Phase1 범위 밖)
    delta = 0.0
    if customer is not None:
        adj = getattr(customer, "margin_adjustment", None)
        if adj is not None:
            try:
                delta = float(adj)
            except (ValueError, TypeError):
                delta = 0.0
    applied = base + delta
    floor = MARGIN_FLOOR.get(channel)
    if floor is not None:
        applied = max(applied, floor)
    return applied / 100.0


def _roundup(x: float, ndigits: int = 0) -> float:
    """ROUNDUP(엑셀): 위로 올림. ndigits=-3 → 1,000단위 올림, 0 → 정수($1) 올림."""
    factor = 10 ** (-ndigits)
    return math.ceil(x / factor) * factor


def _parsed_dict(p: ParsedCode) -> Dict[str, Any]:
    return {"size": p.size, "form": p.form, "material": p.material, "core": p.core,
            "channel": p.channel, "mode": p.mode, "is_sa": p.is_sa, "endface": p.endface}


def suggest_price(*, order_code: str, length_m: float, quantity: int, currency: str,
                  customer=None, config: Optional[QuoteConfig] = None, cost_source=None,
                  overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """견적 단가 자동산출. 백엔드 권위 계산.

    반환: unit_price, amount, currency, cost_breakdown, applied, warnings, parsed.
    unit_price=None 이면 산출 불가(수기 입력 필요) — warnings 참조.

    overrides(상세 산출 패널): 사용자가 손댄 값으로 재계산(서버 권위 유지). 미지정 항목은 자동값.
      margin_rate(%), base_cost_krw, price_increase_pct, connector_a, connector_b,
      cable, cable_rate, assembly, assembly_stages, option_delta, domestic_premium,
      exchange_rate, extra_items=[{label, amount}].  (최종 컴포넌트값 지정 시 그 값이 우선)
    """
    config = config or QuoteConfig()
    cost_source = cost_source or get_interim_cost_source()
    currency = (currency or "KRW").upper()
    length_m = float(length_m or 0)
    quantity = int(quantity or 1)
    ov = overrides or {}

    parsed = parse_order_code(order_code)
    warnings = list(parsed.warnings)

    def _fail(msg: str):
        return {"unit_price": None, "amount": None, "currency": currency,
                "cost_breakdown": {}, "applied": {}, "warnings": warnings + [msg],
                "parsed": _parsed_dict(parsed)}

    def _ov(key):
        """오버라이드 숫자값(없거나 파싱불가면 None)."""
        if key in ov and ov[key] is not None and ov[key] != "":
            try:
                return float(ov[key])
            except (ValueError, TypeError):
                return None
        return None

    # ① 가격 결정 우선순위: 고객 합의가(계약 price list) — Phase1 자리만 마련(추후 §2.1)
    #    agreed = get_agreed_price(customer, order_code) → 있으면 계산 없이 그대로 사용.

    ex = _ov("exchange_rate") or config.exchange_rate

    # ② 마진(모델 C) — 오버라이드(%) 우선
    ov_margin = _ov("margin_rate")
    if ov_margin is not None:
        margin = ov_margin / 100.0
        margin_source = "override"
    elif parsed.channel:
        margin = resolve_margin(customer, parsed.channel, config)
        margin_source = "auto"
    else:
        margin = None
        margin_source = "auto"

    # 원가 + 인상률(비율만) — 오더코드별 우선, 없으면 전역
    ov_base = _ov("base_cost_krw")
    if ov_base is not None:
        base_cost = ov_base
    elif parsed.size and parsed.form and parsed.core and parsed.mode:
        base_cost = cost_source.get_connector_cost(parsed.size, parsed.form, parsed.core, parsed.mode)
    else:
        base_cost = None
    ov_inc = _ov("price_increase_pct")
    inc = ov_inc if ov_inc is not None else \
        config.price_increase_by_item.get((order_code or "").strip().upper(), config.price_increase_global)
    adj_cost = base_cost * (1 + inc / 100.0) if base_cost is not None else None

    # 커넥터A 판매가 = 원가 / (1 − 마진).  USD는 원가(₩)/환율 후 마진.
    ov_connA = _ov("connector_a")
    if ov_connA is not None:
        connA = ov_connA
    elif adj_cost is not None and margin is not None and margin < 1:
        connA = (adj_cost / ex) / (1 - margin) if currency == "USD" else adj_cost / (1 - margin)
    else:
        return _fail("커넥터 원가·마진을 확정할 수 없습니다 — 원가/마진을 직접 입력하세요.")

    # 커넥터B: SA면 커넥터A, 아니면 채널수 × 엔드페이스단가
    endface_rate = cost_source.get_endface_rate(currency)
    ov_connB = _ov("connector_b")
    if ov_connB is not None:
        connB = ov_connB
    elif parsed.is_sa:
        connB = connA
    elif parsed.channel:
        connB = parsed.channel * endface_rate
    else:
        connB = 0.0
        warnings.append("채널 미인식 — 커넥터B 0(직접 입력 권장)")

    # 케이블 = 미터수 × 미터당단가(모드,채널)
    ov_cable = _ov("cable")
    ov_cable_rate = _ov("cable_rate")
    if ov_cable is not None:
        cable = ov_cable
        cable_rate = ov_cable_rate
    else:
        if ov_cable_rate is not None:
            cable_rate = ov_cable_rate
        elif parsed.mode and parsed.channel:
            cable_rate = cost_source.get_cable_rate(parsed.mode, parsed.channel, currency)
        else:
            cable_rate = None
        if cable_rate is None:
            warnings.append("케이블 단가 미확정 — 0")
            cable_rate = 0.0
        cable = length_m * cable_rate
        if length_m <= 0:
            warnings.append("미터수 미입력 — 케이블 0")

    # 조립비: SA→2단, 아니면 1단(오버라이드 가능)
    ov_stages = ov.get("assembly_stages")
    try:
        stages = int(ov_stages) if ov_stages not in (None, "") else (2 if parsed.is_sa else 1)
    except (ValueError, TypeError):
        stages = 2 if parsed.is_sa else 1
    ov_asm = _ov("assembly")
    if ov_asm is not None:
        assembly = ov_asm
    elif parsed.channel:
        assembly = cost_source.get_assembly_cost(parsed.channel, stages, currency)
        if assembly is None:
            warnings.append("조립비 미등록 — 0 처리")
            assembly = 0.0
    else:
        assembly = 0.0
        warnings.append("채널 미인식 — 조립비 0(직접 입력 권장)")

    option_delta = _ov("option_delta") or 0.0  # SUS 등 옵션 델타

    # 기타 항목(특수케이블 등 수기 추가)
    extras: List[Dict[str, Any]] = []
    for it in (ov.get("extra_items") or []):
        if not isinstance(it, dict):
            continue
        try:
            amt = float(it.get("amount") or 0)
        except (ValueError, TypeError):
            amt = 0.0
        if not amt:
            continue
        extras.append({"label": str(it.get("label") or "기타"), "amount": amt})
    extra_total = sum(e["amount"] for e in extras)

    subtotal = connA + connB + cable + assembly + option_delta + extra_total

    ov_prem = _ov("domestic_premium")
    premium_val = ov_prem if ov_prem is not None else config.domestic_premium
    if currency == "USD":
        unit = _roundup(subtotal, 0)              # $1 올림, 프리미엄 없음
        premium_applied = 1.0
    else:
        unit = _roundup(subtotal * premium_val, -3)  # ×프리미엄, ₩1,000 올림
        premium_applied = premium_val

    return {
        "unit_price": unit,
        "amount": unit * quantity,
        "currency": currency,
        "cost_breakdown": {
            "connector_a": round(connA, 2),
            "connector_b": round(connB, 2),
            "cable": round(cable, 2),
            "assembly": round(assembly, 2),
            "option_delta": round(option_delta, 2),
            "extra_items": extras,
            "extra_total": round(extra_total, 2),
            "subtotal": round(subtotal, 2),
            "base_cost_krw": base_cost,
            "adjusted_cost_krw": round(adj_cost, 2) if adj_cost is not None else None,
            "cable_rate": cable_rate,
        },
        "applied": {
            "margin_rate": round(margin, 4) if margin is not None else None,
            "margin_source": margin_source,
            "exchange_rate": ex,
            "domestic_premium": premium_applied,
            "price_increase_pct": inc,
            "assembly_stages": stages,
        },
        "warnings": warnings,
        "parsed": _parsed_dict(parsed),
    }


def config_to_dict(config: QuoteConfig) -> Dict[str, Any]:
    """QuoteConfig → 프론트/응답용 dict (관리자 설정 화면)."""
    return {
        "channel_margins": {str(k): v for k, v in config.channel_margins.items()},
        "exchange_rate": config.exchange_rate,
        "domestic_premium": config.domestic_premium,
        "price_increase_global": config.price_increase_global,
        "price_increase_by_item": config.price_increase_by_item,
    }


def save_config(db, data: Dict[str, Any]) -> Dict[str, Any]:
    """관리자 견적 설정 저장 — app_setting 4개 키에 기록(패널이 전체 값을 보냄).

    load_config가 읽는 키와 동일: quote_channel_margins / quote_exchange_rate /
    quote_domestic_premium / quote_price_increase({global, by_item}).
    """
    from app.models.app_setting import AppSetting
    data = data or {}

    def _set(key: str, value):
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value

    # 채널 기준 마진(%) — {채널: %}
    cm: Dict[str, float] = {}
    for k, v in (data.get("channel_margins") or {}).items():
        try:
            cm[str(int(k))] = float(v)
        except (ValueError, TypeError):
            continue
    _set("quote_channel_margins", cm)

    # 환율 / 국내 프리미엄
    try:
        ex = float(data.get("exchange_rate"))
    except (ValueError, TypeError):
        ex = DEFAULT_EXCHANGE_RATE
    _set("quote_exchange_rate", ex if ex > 0 else DEFAULT_EXCHANGE_RATE)
    try:
        prem = float(data.get("domestic_premium"))
    except (ValueError, TypeError):
        prem = DEFAULT_DOMESTIC_PREMIUM
    _set("quote_domestic_premium", prem if prem > 0 else DEFAULT_DOMESTIC_PREMIUM)

    # 가격 인상률(%) — 전역 + 품목별
    try:
        inc_global = float(data.get("price_increase_global") or 0.0)
    except (ValueError, TypeError):
        inc_global = 0.0
    by_item: Dict[str, float] = {}
    for k, v in (data.get("price_increase_by_item") or {}).items():
        code = str(k).strip().upper()
        if not code:
            continue
        try:
            by_item[code] = float(v)
        except (ValueError, TypeError):
            continue
    _set("quote_price_increase", {"global": inc_global, "by_item": by_item})

    db.commit()
    return config_to_dict(load_config(db))


def load_config(db) -> QuoteConfig:
    """app_setting 에서 견적 설정을 읽어 QuoteConfig 구성(없으면 기본값)."""
    from app.models.app_setting import AppSetting
    cfg = QuoteConfig()

    def _get(key):
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        return row.value if row else None

    cm = _get("quote_channel_margins")
    if isinstance(cm, dict) and cm:
        try:
            cfg.channel_margins = {int(k): float(v) for k, v in cm.items()}
        except (ValueError, TypeError):
            pass
    ex = _get("quote_exchange_rate")
    if isinstance(ex, (int, float)) and ex:
        cfg.exchange_rate = float(ex)
    pr = _get("quote_domestic_premium")
    if isinstance(pr, (int, float)) and pr:
        cfg.domestic_premium = float(pr)
    inc = _get("quote_price_increase")
    if isinstance(inc, dict):
        try:
            cfg.price_increase_global = float(inc.get("global", 0) or 0)
            by = inc.get("by_item") or {}
            cfg.price_increase_by_item = {str(k).upper(): float(v) for k, v in by.items()}
        except (ValueError, TypeError):
            pass
    return cfg
