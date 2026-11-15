"""견적서 PDF 생성 서비스 (Phase 1 Step 5)

Usage:
    service = QuotationPdfService()
    pdf_bytes = service.render(data, lang="ko")  # 또는 lang 생략 → data.language 사용

또는 모듈 캐시된 인스턴스를 재사용:
    pdf_bytes = get_default_service().render(data)
"""

from pathlib import Path
from typing import Literal, Optional

import weasyprint
from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateNotFound,
    select_autoescape,
)

from app.schemas.quotation_pdf import Language, QuotationPdfData
from app.services.pdf.fonts import verify_fonts
from app.services.pdf.highlight import register_jinja_filter
from app.utils.numkor import to_korean_amount


# 기본 템플릿 디렉토리 — backend/app/templates/pdf
DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "pdf"

# (문서타입, 언어) → 템플릿 파일 매핑
_TEMPLATE_BY_TYPE_LANG = {
    ("QUOTATION", "ko"): "quotation_ko.html",
    ("QUOTATION", "en"): "quotation_en.html",
    ("PI", "en"): "pi_en.html",
    ("CI", "en"): "ci_en.html",
    ("INVOICE", "en"): "invoice_en.html",
    # ("PI", "ko") / ("CI", "ko") / ("INVOICE", "ko"): 미지원 — 영문 전용
}


class QuotationPdfRenderError(Exception):
    """PDF 렌더링 오류 — 폰트/템플릿/데이터/마크업 등 모든 단계의 실패를 포괄."""


class QuotationPdfService:
    """견적서 PDF 생성기.

    HTML 템플릿(Jinja2) → WeasyPrint → PDF bytes.
    Jinja2 환경은 인스턴스 생성 시 1회 초기화하여 재사용.
    스레드 안전 — 동시 render() 호출 가능.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        self._template_dir = Path(template_dir) if template_dir else DEFAULT_TEMPLATE_DIR

        if not self._template_dir.is_dir():
            raise QuotationPdfRenderError(
                f"템플릿 디렉토리가 없습니다: {self._template_dir}"
            )

        missing = verify_fonts(self._template_dir)
        if missing:
            raise QuotationPdfRenderError(
                f"필수 폰트 파일 누락 ({len(missing)}개): {', '.join(missing)}\n"
                f"  위치: {self._template_dir / 'assets' / 'fonts'}"
            )

        self._env = self._build_env()

    def _build_env(self) -> Environment:
        env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(["html"]),
        )
        register_jinja_filter(env)
        return env

    def render(
        self,
        data: QuotationPdfData,
        lang: Optional[Literal["ko", "en"]] = None,
    ) -> bytes:
        """견적서 PDF 바이트 생성.

        Args:
            data: 렌더 데이터.
            lang: 'ko' 또는 'en'. 생략 시 data.language 사용.

        Returns:
            PDF 바이너리 (b'%PDF-...').

        Raises:
            QuotationPdfRenderError: 데이터/템플릿/렌더 실패 시 단일 타입으로 래핑.
        """
        if data is None:
            raise QuotationPdfRenderError("data가 None입니다.")

        lang_value = lang or data.language.value
        template_name = _TEMPLATE_BY_TYPE_LANG.get((data.document_type, lang_value))
        if template_name is None:
            supported = sorted(_TEMPLATE_BY_TYPE_LANG.keys())
            raise QuotationPdfRenderError(
                f"지원하지 않는 (문서타입, 언어) 조합: "
                f"({data.document_type!r}, {lang_value!r}) — 지원: {supported}"
            )

        try:
            template = self._env.get_template(template_name)
        except TemplateNotFound as exc:
            raise QuotationPdfRenderError(
                f"템플릿을 찾을 수 없습니다: {template_name}"
            ) from exc

        # 한글 양식에서만 사용되지만 모든 컨텍스트에 안전하게 포함
        amount_in_korean = (
            to_korean_amount(data.subtotal) if lang_value == "ko" else ""
        )

        def _render_html(compact: bool) -> str:
            try:
                return template.render(
                    data=data, amount_in_korean=amount_in_korean, compact=compact
                )
            except Exception as exc:
                raise QuotationPdfRenderError(
                    f"템플릿 렌더 실패 ({template_name}): {exc}"
                ) from exc

        base = str(self._template_dir)
        try:
            doc = weasyprint.HTML(string=_render_html(False), base_url=base).render()
            # 아슬아슬하게 2페이지로 넘친 경우(예: 서명 블록만 다음 장으로) → 컴팩트 모드로
            # 1페이지 시도. 진짜 품목이 많아 컴팩트로도 2페이지면 그대로 2페이지 유지.
            if len(doc.pages) == 2:
                compact_doc = weasyprint.HTML(
                    string=_render_html(True), base_url=base
                ).render()
                if len(compact_doc.pages) == 1:
                    return compact_doc.write_pdf()
            return doc.write_pdf()
        except QuotationPdfRenderError:
            raise
        except Exception as exc:
            raise QuotationPdfRenderError(f"PDF 생성 실패: {exc}") from exc


_default_service: Optional[QuotationPdfService] = None


def get_default_service() -> QuotationPdfService:
    """기본 템플릿 디렉토리 기반 캐시 인스턴스 반환 (모듈 단일 싱글턴)."""
    global _default_service
    if _default_service is None:
        _default_service = QuotationPdfService()
    return _default_service
