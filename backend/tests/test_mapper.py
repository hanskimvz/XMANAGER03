"""SalesDocument(DB) → QuotationPdfData 매퍼 테스트"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.schemas.quotation_pdf import (
    Currency,
    Language,
    QuotationPdfData,
)
from app.services.pdf.mapper import from_sales_document


def _customer(**overrides):
    base = dict(
        partner_name="고객사",
        partner_name_en="Customer Inc.",
        manager_name="김담당",
        address="서울시",
        address_detail="강남구",
        country_name="Republic of Korea",
        tel="02-1234-5678",
        email="contact@customer.com",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _item(line_no=1, code="HXB-001", qty="1", price="100", desc=None, remarks=None):
    q = Decimal(qty)
    p = Decimal(price)
    return SimpleNamespace(
        line_no=line_no,
        product_code=code,
        description=desc,
        quantity=q,
        uom="EA",
        unit_price=p,
        amount=q * p,
        line_remarks=remarks,
    )


def _doc(**overrides):
    base = dict(
        document_type="QUOTATION",
        document_number="Q-TEST-001",
        document_date=date(2026, 1, 1),
        version=1,
        currency="USD",
        customer=_customer(),
        items=[_item()],
        prepared_by="MJ Kim",
        prepared_email="kmj@xbeamtech.co.kr",
        payment_terms="100% T/T",
        delivery_terms="EXW Seoul",
        valid_until="30 days",
        country_of_origin="Republic of Korea",
        hs_code="8536.70",
        remarks=None,
        ship_to_name=None,
        ship_to_address=None,
        ship_to_contact=None,
        bank_name=None,
        bank_address=None,
        swift_code=None,
        account_name=None,
        account_number=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestBasicMapping:
    def test_returns_quotation_pdf_data(self):
        data = from_sales_document(_doc())
        assert isinstance(data, QuotationPdfData)

    def test_basic_fields_carried_over(self):
        data = from_sales_document(_doc())
        assert data.document_number == "Q-TEST-001"
        assert data.document_date == date(2026, 1, 1)
        assert data.version == 1
        assert data.prepared_by == "MJ Kim"

    def test_subtotal_summed_from_items(self):
        items = [
            _item(line_no=1, qty="2", price="50"),   # 100
            _item(line_no=2, qty="3", price="70"),   # 210
        ]
        data = from_sales_document(_doc(items=items))
        assert data.subtotal == Decimal("310")

    def test_items_sorted_by_line_no(self):
        items = [
            _item(line_no=3, code="C"),
            _item(line_no=1, code="A"),
            _item(line_no=2, code="B"),
        ]
        data = from_sales_document(_doc(items=items))
        assert [it.part_number for it in data.items] == ["A", "B", "C"]


class TestDocumentTypeGuard:
    @pytest.mark.parametrize("doc_type", ["CI", "DRAFT", "INVALID"])
    def test_unsupported_raises(self, doc_type):
        with pytest.raises(ValueError, match="QUOTATION"):
            from_sales_document(_doc(document_type=doc_type))

    def test_quotation_accepted(self):
        data = from_sales_document(_doc(document_type="QUOTATION"))
        assert data.document_type == "QUOTATION"

    def test_pi_accepted(self):
        data = from_sales_document(_doc(document_type="PI"))
        assert data.document_type == "PI"


class TestPiSpecificFields:
    def test_po_number_mapped_from_customer_po_number(self):
        doc = _doc(document_type="PI")
        doc.customer_po_number = "#42"
        data = from_sales_document(doc)
        assert data.po_number == "#42"

    def test_po_number_none_when_attribute_missing(self):
        doc = _doc(document_type="PI")
        # SimpleNamespace는 customer_po_number 속성 없음 (getattr default 사용)
        data = from_sales_document(doc)
        assert data.po_number is None

    def test_quotation_can_also_carry_po_number(self):
        doc = _doc(document_type="QUOTATION")
        doc.customer_po_number = "#X"
        data = from_sales_document(doc)
        # Q도 모델 필드는 가지지만 템플릿에서 표시 안 함
        assert data.po_number == "#X"


class TestVatHandling:
    def test_krw_applies_10_percent(self):
        data = from_sales_document(_doc(currency="KRW"))
        assert data.vat_rate == Decimal("0.10")
        assert data.vat_amount == Decimal("10.00")  # subtotal=100
        assert data.total == Decimal("110.00")

    def test_usd_no_vat(self):
        data = from_sales_document(_doc(currency="USD"))
        assert data.vat_rate == Decimal("0")
        assert data.vat_amount == Decimal("0")
        assert data.total == Decimal("100")

    def test_eur_no_vat(self):
        data = from_sales_document(_doc(currency="EUR"))
        assert data.vat_rate == Decimal("0")

    def test_vat_excluded_auto_true_for_krw(self):
        data = from_sales_document(_doc(currency="KRW"))
        assert data.vat_excluded is True

    def test_vat_excluded_auto_false_for_usd(self):
        data = from_sales_document(_doc(currency="USD"))
        assert data.vat_excluded is False

    def test_vat_excluded_explicit_override(self):
        data = from_sales_document(_doc(currency="KRW"), vat_excluded=False)
        assert data.vat_excluded is False


class TestShipTo:
    def test_default_same_as_buyer(self):
        data = from_sales_document(_doc())
        assert data.ship_to.same_as_buyer is True

    def test_explicit_ship_to(self):
        data = from_sales_document(_doc(
            ship_to_name="다른 수령인",
            ship_to_address="부산시",
        ))
        assert data.ship_to.same_as_buyer is False
        assert data.ship_to.name == "다른 수령인"
        assert data.ship_to.address == "부산시"


class TestBankInfo:
    def test_none_when_all_empty(self):
        data = from_sales_document(_doc())
        assert data.bank is None

    def test_present_when_bank_name_set(self):
        data = from_sales_document(_doc(
            bank_name="HANA",
            swift_code="KOEXKRSE",
            account_number="123-456",
        ))
        assert data.bank is not None
        assert data.bank.bank_name == "HANA"
        assert data.bank.swift_code == "KOEXKRSE"


class TestCurrencyCoercion:
    def test_unknown_falls_back_to_usd(self):
        data = from_sales_document(_doc(currency="JPY"))
        assert data.currency == Currency.USD

    def test_lowercase_coerced(self):
        data = from_sales_document(_doc(currency="usd"))
        assert data.currency == Currency.USD

    def test_none_falls_back(self):
        data = from_sales_document(_doc(currency=None))
        assert data.currency == Currency.USD


class TestCustomerEdgeCases:
    def test_no_customer_yields_dash_name(self):
        data = from_sales_document(_doc(customer=None))
        assert data.customer.name == "-"

    def test_address_concat_from_two_fields(self):
        c = _customer(address="서울시", address_detail="강남구")
        data = from_sales_document(_doc(customer=c))
        assert "서울시 강남구" == data.customer.address


class TestStampAndLanguage:
    def test_korean_default_stamp_omitted(self):
        data = from_sales_document(_doc(), language=Language.KO)
        assert data.stamp_omitted is True

    def test_english_default_stamp_shown(self):
        data = from_sales_document(_doc(), language=Language.EN)
        assert data.stamp_omitted is False
