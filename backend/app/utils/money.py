"""통화별 금액 표기 유틸 (v0.81.0).

국제 통용 방식: 원화·엔·위안은 정수, 달러·유로 등은 소수 2자리. 모두 천 단위 콤마.
프론트 `price.ts`(formatAmount/currencyFractionDigits)와 동일 규칙.
"""

_ZERO_DECIMAL_CURRENCIES = {"KRW", "JPY", "CNY"}


def currency_fraction_digits(currency: str = "KRW") -> int:
    return 0 if (currency or "KRW").upper() in _ZERO_DECIMAL_CURRENCIES else 2


def excel_money_format(currency: str = "KRW") -> str:
    """openpyxl 셀 number_format 문자열 (천 단위 콤마 + 통화별 소수 자리)."""
    return "#,##0" if currency_fraction_digits(currency) == 0 else "#,##0.00"


def format_money(amount, currency: str = "KRW") -> str:
    """사람이 읽는 금액 문자열 (콤마 + 통화별 소수). 예: 1,234,000 / 1,234.56"""
    if amount is None:
        return ""
    digits = currency_fraction_digits(currency)
    return f"{float(amount):,.{digits}f}"
