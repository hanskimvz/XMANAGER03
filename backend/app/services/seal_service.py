"""
자동 도장 SVG 생성 서비스 (v0.33.0)

라이브러리 불필요 — 순수 문자열 SVG. 결정적(같은 입력=같은 출력).
설계노트 5장.
"""

from typing import List


def _resolve_chars(name: str) -> List[str]:
    """도장에 새길 글자 추출 (성 포함 최대 3글자, seal_text 가 4자면 4글자 허용)."""
    name = (name or "").strip()
    if not name:
        return []
    # seal_text 가 4글자면 2x2 배치를 위해 4글자 모두 사용, 그 외엔 뒤 3글자
    if len(name) == 4:
        return list(name)
    return list(name[-3:])


def _esc(text: str) -> str:
    """SVG 텍스트용 XML 이스케이프."""
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def make_seal_svg(name: str, approved_date: str, color: str = "#1456b8") -> str:
    """자동 도장 SVG 문자열 생성.

    Args:
        name: 도장 글자(우선순위: user.seal_text → 없으면 user.name)
        approved_date: 'YYYY-MM-DD' 또는 'YY.MM.DD' 문자열
        color: 도장 색(기본 빨강 #1456b8)

    글자수별 배치:
        2글자: 좌우 2칸
        3글자: 위 1 / 아래 2 (전통 인장)
        4글자: 2x2
        1글자/기타: 중앙 1글자
    """
    chars = _resolve_chars(name)
    color = color or "#1456b8"
    date_str = _esc(approved_date or "")

    # 글자 <text> 요소들 생성
    name_elems: List[str] = []

    def text_el(ch: str, x: int, y: int, size: int = 26) -> str:
        return (
            f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'text-anchor="middle" dominant-baseline="central" '
            f'font-family="serif" font-weight="bold">{_esc(ch)}</text>'
        )

    n = len(chars)
    if n == 0:
        pass
    elif n == 1:
        name_elems.append(text_el(chars[0], 50, 46, size=34))
    elif n == 2:
        # 좌우 2칸
        name_elems.append(text_el(chars[0], 34, 46))
        name_elems.append(text_el(chars[1], 66, 46))
    elif n == 3:
        # 위 1 / 아래 2 (전통 인장)
        name_elems.append(text_el(chars[0], 50, 32))
        name_elems.append(text_el(chars[1], 34, 58))
        name_elems.append(text_el(chars[2], 66, 58))
    else:  # 4글자: 2x2
        name_elems.append(text_el(chars[0], 34, 34))
        name_elems.append(text_el(chars[1], 66, 34))
        name_elems.append(text_el(chars[2], 34, 60))
        name_elems.append(text_el(chars[3], 66, 60))

    names_svg = "".join(name_elems)

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        'width="100" height="100">'
        f'<circle cx="50" cy="50" r="46" stroke="{color}" stroke-width="3" fill="none"/>'
        f'{names_svg}'
        f'<text x="50" y="88" font-size="9" fill="{color}" '
        f'text-anchor="middle" font-family="serif">{date_str}</text>'
        '</svg>'
    )


def make_seal_css(name: str, approved_date: str, color: str = "#1456b8") -> str:
    """WeasyPrint 호환용 HTML/CSS 도장(원 border-radius + 텍스트).

    SVG 와 동일한 모양을 호환 안전한 방식으로 제공(설계노트 5장 보조 함수).
    """
    chars = _resolve_chars(name)
    color = color or "#1456b8"
    name_text = _esc("".join(chars))
    date_str = _esc(approved_date or "")

    return (
        f'<div style="display:inline-block;width:64px;height:64px;'
        f'border:2px solid {color};border-radius:50%;text-align:center;'
        f'position:relative;font-family:serif;">'
        f'<div style="color:{color};font-weight:bold;font-size:18px;'
        f'line-height:48px;">{name_text}</div>'
        f'<div style="color:{color};font-size:7px;position:absolute;'
        f'bottom:3px;left:0;right:0;">{date_str}</div>'
        f'</div>'
    )
