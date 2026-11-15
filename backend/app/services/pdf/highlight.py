"""견적서 PDF용 강조 마크업 변환 유틸 (Phase 1+)

영업담당자가 part_number / description 입력 시 사용 가능한 마크업 문법을
PDF 렌더용 HTML span으로 변환합니다.

기존 강조 (3종):
    [[텍스트]]   →  <span class="highlight-critical">텍스트</span>   (빨간 굵게)
    {{텍스트}}   →  <span class="highlight-warning">텍스트</span>   (노란 하이라이트)
    __텍스트__   →  <span class="highlight-spec">텍스트</span>      (빨간 밑줄)

추가 (Phase 4 확장):
    **텍스트**         →  <strong>텍스트</strong>                    (단순 굵게)
    {color:텍스트}     →  <span class="text-color-{color}">..</span> (색상 7종)
        지원 색명: red / orange / green / blue / indigo / purple / gray

처리 순서: HTML escape → [[]] → {{}} → __...__ → **...** → {color:} → markupsafe.Markup
HTML escape를 먼저 수행하므로 사용자 입력의 <script> 등은 무력화됩니다 (XSS 방지).
{{...}} 가 {...:...} 보다 먼저 처리되므로 우선순위 충돌 없음.

CSS 클래스 정의는 templates/pdf/styles/common.css 참고.
"""

import html
import re
from typing import Optional

from markupsafe import Markup


_PATTERN_CRITICAL = re.compile(r"\[\[(.+?)\]\]", re.DOTALL)
_PATTERN_WARNING = re.compile(r"\{\{(.+?)\}\}", re.DOTALL)
_PATTERN_SPEC = re.compile(r"__(.+?)__", re.DOTALL)
_PATTERN_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)

# 색상 마크업 — {colorname:text} 형태. 화이트리스트 색만 매칭.
_COLOR_NAMES = ("red", "orange", "green", "blue", "indigo", "purple", "gray")
_PATTERN_COLOR = re.compile(
    r"\{(" + "|".join(_COLOR_NAMES) + r"):(.+?)\}",
    re.DOTALL,
)

# 인라인 이미지 — {img:data:...} (붙여넣기 이미지, data URI만 허용)
_PATTERN_IMAGE = re.compile(r"\{img:(data:[^}]+)\}", re.DOTALL)


def _color_replace(match: re.Match) -> str:
    color = match.group(1)
    inner = match.group(2)
    return f'<span class="text-color-{color}">{inner}</span>'


def apply_highlights(text: Optional[str]) -> Markup:
    """마크업 문법을 강조 표시 HTML span으로 치환.

    None / 빈 문자열은 빈 Markup 반환. 입력이 str이 아니면 str()로 강제 변환.
    """
    if text is None:
        return Markup("")
    if not isinstance(text, str):
        text = str(text)

    escaped = html.escape(text)

    # 이미지 먼저(base64 data URI는 html.escape 영향 없음)
    escaped = _PATTERN_IMAGE.sub(
        r'<img src="\1" class="markup-img" />', escaped
    )

    escaped = _PATTERN_CRITICAL.sub(
        r'<span class="highlight-critical">\1</span>', escaped
    )
    escaped = _PATTERN_WARNING.sub(
        r'<span class="highlight-warning">\1</span>', escaped
    )
    escaped = _PATTERN_SPEC.sub(
        r'<span class="highlight-spec">\1</span>', escaped
    )
    escaped = _PATTERN_BOLD.sub(r'<strong>\1</strong>', escaped)
    escaped = _PATTERN_COLOR.sub(_color_replace, escaped)

    return Markup(escaped)


def strip_markup(text: Optional[str]) -> str:
    """강조 마크업 문법을 제거하고 순수 텍스트만 반환.

    품번/코드처럼 식별자로 쓰이는 값에서 마크업이 새어 들어간 경우 정리용.
    [[x]]/{{x}}/__x__/**x** → x, {color:x} → x, {img:...} → '' (제거).
    apply_highlights 와 동일한 문법을 대상으로 함.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    text = _PATTERN_IMAGE.sub("", text)
    text = _PATTERN_CRITICAL.sub(r"\1", text)
    text = _PATTERN_WARNING.sub(r"\1", text)
    text = _PATTERN_SPEC.sub(r"\1", text)
    text = _PATTERN_BOLD.sub(r"\1", text)
    text = _PATTERN_COLOR.sub(r"\2", text)
    return text


def register_jinja_filter(jinja_env) -> None:
    """Jinja2 Environment에 `highlight` 커스텀 필터 등록.

    템플릿 사용: {{ item.part_number | highlight }}
    """
    jinja_env.filters["highlight"] = apply_highlights
