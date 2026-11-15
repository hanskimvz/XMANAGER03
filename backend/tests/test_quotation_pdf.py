"""QuotationPdfService — PDF 생성 동작/에러/페이지 분할 테스트"""

from datetime import date
from decimal import Decimal

import pytest

# 패치 트리거 — weasyprint 직접 import 전 반드시 필요
import app.services.pdf  # noqa: F401

from app.schemas.quotation_pdf import (
    CompanyInfo,
    Currency,
    CustomerInfo,
    Language,
    QuotationLineItem,
    QuotationPdfData,
)
from app.services.pdf._sample import (
    sample_pi_overseas,
    sample_quotation_domestic,
    sample_quotation_overseas,
)
from app.services.pdf.quotation_pdf import (
    QuotationPdfRenderError,
    QuotationPdfService,
    get_default_service,
)


@pytest.fixture(scope="module")
def service():
    return QuotationPdfService()


class TestRenderBasic:
    def test_pdf_magic_number_overseas(self, service):
        pdf = service.render(sample_quotation_overseas())
        assert pdf[:5] == b"%PDF-"

    def test_pdf_magic_number_domestic(self, service):
        pdf = service.render(sample_quotation_domestic())
        assert pdf[:5] == b"%PDF-"

    def test_pdf_size_in_reasonable_range(self, service):
        pdf = service.render(sample_quotation_overseas())
        assert 30_000 < len(pdf) < 5_000_000  # 30KB ~ 5MB

    def test_lang_param_overrides_data_language(self, service):
        # 영문 데이터를 한글 템플릿으로
        data = sample_quotation_overseas()
        pdf_ko = service.render(data, lang="ko")
        pdf_en = service.render(data, lang="en")
        assert pdf_ko[:5] == b"%PDF-"
        assert pdf_en[:5] == b"%PDF-"
        assert pdf_ko != pdf_en


class TestRenderErrors:
    def test_none_data_raises(self, service):
        with pytest.raises(QuotationPdfRenderError, match="None"):
            service.render(None)

    def test_unsupported_lang_raises(self, service):
        with pytest.raises(QuotationPdfRenderError, match="지원하지 않는"):
            service.render(sample_quotation_overseas(), lang="jp")

    def test_pi_korean_combo_unsupported(self, service):
        # PI는 영문 전용 — pi_ko 템플릿 없음
        data = sample_pi_overseas()
        with pytest.raises(QuotationPdfRenderError, match="지원하지 않는"):
            service.render(data, lang="ko")

    def test_invalid_template_dir(self):
        with pytest.raises(QuotationPdfRenderError, match="템플릿 디렉토리가 없습니다"):
            QuotationPdfService(template_dir="/nonexistent/path")


class TestRenderPi:
    def test_pi_pdf_magic_number(self, service):
        pdf = service.render(sample_pi_overseas())
        assert pdf[:5] == b"%PDF-"

    def test_pi_pdf_size_reasonable(self, service):
        pdf = service.render(sample_pi_overseas())
        assert 30_000 < len(pdf) < 5_000_000

    def test_pi_distinct_from_quotation(self, service):
        # 동일 데이터 기반이지만 document_type만 다르면 다른 PDF가 나와야 함
        q_pdf = service.render(sample_quotation_overseas())
        pi_pdf = service.render(sample_pi_overseas())
        assert q_pdf != pi_pdf


class TestSingleton:
    def test_get_default_service_returns_same_instance(self):
        s1 = get_default_service()
        s2 = get_default_service()
        assert s1 is s2


def _build_data_with_n_items(n: int) -> QuotationPdfData:
    items = [
        QuotationLineItem(
            line_no=i + 1,
            part_number=f"HXB-{i:03d}",
            description=f"Spec line for item {i+1}",
            quantity=Decimal("1"),
            uom="EA",
            unit_price=Decimal("100"),
            amount=Decimal("100"),
        )
        for i in range(n)
    ]
    subtotal = Decimal("100") * n
    return QuotationPdfData(
        language=Language.EN,
        document_number="Q-MULTI-001",
        document_date=date(2026, 1, 1),
        company=CompanyInfo(
            name_ko="엑스빔테크㈜",
            name_en="X-Beam Tech Co.,Ltd.",
        ),
        customer=CustomerInfo(name="Test Customer"),
        items=items,
        currency=Currency.USD,
        subtotal=subtotal,
        total=subtotal,
    )


class TestMultiPage:
    def test_30_items_renders(self, service):
        """품목 30개 — 페이지 분할 발생해도 정상 렌더"""
        pdf = service.render(_build_data_with_n_items(30), lang="en")
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 50_000  # 한 페이지 분량 초과

    def test_50_items_renders(self, service):
        """품목 50개 — 다중 페이지"""
        pdf = service.render(_build_data_with_n_items(50), lang="en")
        assert pdf[:5] == b"%PDF-"
