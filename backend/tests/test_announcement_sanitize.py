"""공지 본문 sanitize — 리치텍스트 에디터 서식은 보존, 위험 요소는 제거."""
from app.services.announcement_service import sanitize_html


def test_keeps_editor_formatting():
    html = (
        '<p><span style="color: #ff0000; font-size: 18px">a</span>'
        '<mark style="background-color: #fef08a">b</mark>'
        "<u>c</u><strong>d</strong></p>"
    )
    out = sanitize_html(html)
    assert "color" in out and "#ff0000" in out
    assert "font-size" in out and "18px" in out
    assert "<mark" in out and "background-color" in out
    assert "<u>c</u>" in out and "<strong>d</strong>" in out


def test_strips_other_style_properties():
    out = sanitize_html('<p><span style="color: red; position: fixed; background-image: url(x)">a</span></p>')
    assert "color" in out
    assert "position" not in out
    assert "background-image" not in out


def test_style_only_on_span_and_mark():
    out = sanitize_html('<p style="color: red">a</p>')
    assert "style" not in out


def test_keeps_base64_raster_image():
    out = sanitize_html('<img src="data:image/png;base64,AAAA" alt="x">')
    assert 'src="data:image/png;base64,AAAA"' in out


def test_strips_non_image_data_urls():
    assert "data:" not in sanitize_html('<a href="data:text/html;base64,AAAA">l</a>')
    assert "data:" not in sanitize_html('<img src="data:text/html;base64,AAAA">')
    assert "data:" not in sanitize_html('<img src="data:image/svg+xml;base64,AAAA">')


def test_still_strips_scripts_and_handlers():
    out = sanitize_html('<p onclick="x()">a</p><script>alert(1)</script><img src="x" onerror="y()">')
    assert "script" not in out
    assert "onclick" not in out
    assert "onerror" not in out


def test_keeps_legacy_blocks():
    out = sanitize_html("<h2>t</h2><ul><li>a</li></ul><blockquote>q</blockquote>")
    assert "<h2>" in out and "<li>" in out and "<blockquote>" in out
