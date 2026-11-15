"""강조 마크업 변환 + XSS 방어 + Jinja2 필터 통합 테스트"""

import pytest
from jinja2 import Environment
from markupsafe import Markup

from app.services.pdf.highlight import apply_highlights, register_jinja_filter


class TestApplyHighlights:
    def test_critical_double_brackets(self):
        result = apply_highlights("HXB-[[SM9/125]]-FA")
        assert str(result) == 'HXB-<span class="highlight-critical">SM9/125</span>-FA'

    def test_warning_double_braces(self):
        result = apply_highlights("Plated: {{Cadmium}}")
        assert str(result) == 'Plated: <span class="highlight-warning">Cadmium</span>'

    def test_spec_double_underscore(self):
        result = apply_highlights("Temp: __-55C ~ +125C__")
        assert str(result) == 'Temp: <span class="highlight-spec">-55C ~ +125C</span>'

    def test_combined_three_types(self):
        result = apply_highlights("[[A]] {{B}} __C__")
        assert str(result) == (
            '<span class="highlight-critical">A</span> '
            '<span class="highlight-warning">B</span> '
            '<span class="highlight-spec">C</span>'
        )

    def test_returns_markup_type(self):
        assert isinstance(apply_highlights("text"), Markup)


class TestXssDefense:
    def test_script_tag_escaped(self):
        result = str(apply_highlights("<script>alert(1)</script>"))
        assert result == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_script_inside_critical_neutralized(self):
        result = str(apply_highlights("[[<script>x</script>]]"))
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_html_entity_amp_escaped(self):
        result = str(apply_highlights("A & B [[C]]"))
        assert "&amp;" in result
        assert "<span class=\"highlight-critical\">C</span>" in result

    def test_attribute_injection_blocked(self):
        # 속성 인젝션 시도 — `"` 이스케이프됨
        result = str(apply_highlights('[[" onclick="alert(1)]]'))
        assert "&quot;" in result
        assert "onclick=" not in result or "&quot;" in result


class TestEdgeCases:
    def test_none_returns_empty(self):
        assert str(apply_highlights(None)) == ""

    def test_empty_string_returns_empty(self):
        assert str(apply_highlights("")) == ""

    def test_unclosed_critical_left_as_text(self):
        # 닫는 ]] 없으면 매칭 안 함
        assert str(apply_highlights("[[unclosed text")) == "[[unclosed text"

    def test_unclosed_warning_left_as_text(self):
        assert str(apply_highlights("{{unclosed text")) == "{{unclosed text"

    def test_empty_brackets_not_converted(self):
        # [[]] 안에 .+? 매칭 대상 없음
        assert "highlight" not in str(apply_highlights("[[]]"))

    def test_priority_critical_over_warning_when_nested(self):
        # 우선순위: [[]] 먼저 → {{}}는 그 안에서 처리됨
        result = str(apply_highlights("[[outer {{inner}} tail]]"))
        assert "highlight-critical" in result
        assert "highlight-warning" in result

    def test_dotall_preserves_newlines(self):
        result = str(apply_highlights("[[A\nB]]"))
        assert "A\nB" in result

    def test_non_string_input_coerced(self):
        result = str(apply_highlights(123))
        assert result == "123"


class TestBoldAndColors:
    """Phase 4 확장 — 단순 굵게 + 색상 7종"""

    def test_simple_bold(self):
        result = str(apply_highlights("**중요**"))
        assert result == "<strong>중요</strong>"

    def test_bold_inline_with_text(self):
        result = str(apply_highlights("This is **bold** text"))
        assert result == "This is <strong>bold</strong> text"

    @pytest.mark.parametrize("color", [
        "red", "orange", "green", "blue", "indigo", "purple", "gray",
    ])
    def test_color_each(self, color):
        result = str(apply_highlights(f"{{{color}:hello}}"))
        assert result == f'<span class="text-color-{color}">hello</span>'

    def test_unknown_color_left_as_text(self):
        # white 같은 미등록 색은 매칭 안 함 (보안: 화이트리스트만)
        result = str(apply_highlights("{white:test}"))
        assert "text-color-white" not in result
        assert "{white:test}" in result

    def test_color_does_not_collide_with_warning(self):
        # {{...}}는 색상보다 우선 처리되어 warning 으로 변환됨
        result = str(apply_highlights("{{Cadmium}}"))
        assert "highlight-warning" in result
        assert "text-color" not in result

    def test_combined_all_features(self):
        result = str(apply_highlights("[[A]] {{B}} __C__ **D** {blue:E}"))
        assert '<span class="highlight-critical">A</span>' in result
        assert '<span class="highlight-warning">B</span>' in result
        assert '<span class="highlight-spec">C</span>' in result
        assert "<strong>D</strong>" in result
        assert '<span class="text-color-blue">E</span>' in result

    def test_xss_inside_color_neutralized(self):
        result = str(apply_highlights("{red:<script>alert(1)</script>}"))
        assert "<script>" not in result
        assert '<span class="text-color-red">' in result
        assert "&lt;script&gt;" in result


class TestJinjaFilter:
    def test_filter_registers(self):
        env = Environment(autoescape=True)
        register_jinja_filter(env)
        assert "highlight" in env.filters

    def test_no_double_escape_in_autoescape_env(self):
        env = Environment(autoescape=True)
        register_jinja_filter(env)
        tmpl = env.from_string("PN: {{ pn | highlight }}")
        result = tmpl.render(pn="HXB-[[SM9]]-FA & <script>")
        assert result == 'PN: HXB-<span class="highlight-critical">SM9</span>-FA &amp; &lt;script&gt;'
