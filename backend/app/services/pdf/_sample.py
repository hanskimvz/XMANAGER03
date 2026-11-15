"""Step 3-7 개발 중 빠른 PDF 렌더 검증용 샘플 픽스처.

운영 코드에서 import 금지 — 모듈명 prefix `_`로 사적 표시.
"""

from datetime import date
from decimal import Decimal

from app.schemas.quotation_pdf import (
    BankInfo,
    Currency,
    CustomerInfo,
    Language,
    QuotationLineItem,
    QuotationPdfData,
    QuotationTerms,
    ShipToInfo,
    default_company_info,
)


def sample_quotation_overseas() -> QuotationPdfData:
    """해외 견적 샘플 — Q-TEMPLATE.pdf 기반, 영문 양식."""
    items = [
        QuotationLineItem(
            line_no=1,
            part_number="HXB17AS-PSD-B-OE-S1-D55-SA-020/30",
            description=(
                "-ConnA: -Plug with Dust Cap\n"
                "-[[Aluminium alloy]], Black hard anodizing\n"
                "-{{14 CH}}, __9 μm core Singlemode fiber__\n"
                "-for out diameter 5.5mm Outdoor cable\n"
                "-ConnB: same as Conn A\n"
                "-L1 : 020 m\n"
                "-L2 : 30 cm"
            ),
            quantity=Decimal("2"),
            uom="pc",
            unit_price=Decimal("268.00"),
            amount=Decimal("536.00"),
        ),
        QuotationLineItem(
            line_no=2,
            part_number="HXB15-RJS-B-O6-S1-D55",
            description=None,
            quantity=Decimal("2"),
            uom="pc",
            unit_price=Decimal("254.00"),
            amount=Decimal("508.00"),
        ),
        QuotationLineItem(
            line_no=3,
            part_number="HXB13-PSD-B-O2-M2-D55",
            description=(
                "-Plug with Dust Cap\n"
                "-Aluminium alloy, Black hard anodizing\n"
                "-{{2 CH}}, __50 μm core Multimode fiber__\n"
                "-for out diameter 5.5mm Outdoor cable"
            ),
            quantity=Decimal("10"),
            uom="pc",
            unit_price=Decimal("145.00"),
            amount=Decimal("1450.00"),
        ),
    ]
    subtotal = sum((it.amount for it in items), start=Decimal("0"))

    return QuotationPdfData(
        language=Language.EN,
        document_number="Q-xx260108",
        document_date=date(2026, 1, 8),
        version=1,
        company=default_company_info(),
        customer=CustomerInfo(
            name="Sample Customer",
            name_en="Sample Customer Inc.",
            email="name@mail.com",
        ),
        ship_to=ShipToInfo(same_as_buyer=True),
        items=items,
        currency=Currency.USD,
        subtotal=subtotal,
        vat_rate=Decimal("0"),
        vat_amount=Decimal("0"),
        total=subtotal,
        vat_excluded=False,
        terms=QuotationTerms(
            payment_terms="100% T/T in advance",
            delivery_terms="EXW Seoul",
            valid_until="Within a month after issued date",
            country_of_origin="Republic of Korea",
            hs_code="8536.70-1000",
        ),
        bank=BankInfo(
            bank_name="KEB HANA BANK, HEAD OFFICE",
            bank_address="35, EULJI-RO, JUNG-GU, SEOUL, KOREA",
            swift_code="KOEXKRSE",
            account_name="XBEAMTECH CO., LTD.",
            account_number="332-910005-81138",
        ),
        prepared_by="MJ Kim",
        prepared_email="kmj@xbeamtech.co.kr",
        stamp_omitted=False,
    )


def sample_quotation_domestic() -> QuotationPdfData:
    """국내 견적 샘플 — Q-DOMESTIC-TEMPLATE.pdf 기반, 한글 양식."""
    items = [
        QuotationLineItem(
            line_no=1,
            part_number="STSAS-XS-O4-S1-D55-SA-50 (릴 포함)",
            description=(
                "- ST to ST 케이블 조립체\n"
                "- 커넥터 A : [[ST/PC]] 커넥터\n"
                "- 커넥터 B : [[ST/PC]] 커넥터\n"
                "- {{광 4 채널}}, __OM3 멀티모드__\n"
                "- ø 5.5mm 옥외용 케이블\n"
                "- L1 총길이 __50 m__\n"
                "\n"
                "케이블 릴\n"
                "- 300m 용 케이블 릴\n"
                "- 재질 : 폴리카보네이트, PE"
            ),
            quantity=Decimal("1"),
            uom="EA",
            unit_price=Decimal("153000"),
            amount=Decimal("153000"),
        ),
    ]
    subtotal = sum((it.amount for it in items), start=Decimal("0"))
    vat_rate = Decimal("0.10")
    vat_amount = (subtotal * vat_rate).quantize(Decimal("1"))

    return QuotationPdfData(
        language=Language.KO,
        document_number="20250109-1",
        document_date=date(2025, 1, 9),
        version=1,
        company=default_company_info(),
        customer=CustomerInfo(name="사운더스"),
        items=items,
        currency=Currency.KRW,
        subtotal=subtotal,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        total=subtotal + vat_amount,
        vat_excluded=True,
        terms=QuotationTerms(
            payment_terms="현금 결제",
            valid_until="견적일로 부터 4주",
            remarks="* 비고\n1. 직인생략",
        ),
        prepared_by="김민정 차장",
        prepared_email="kmj@xbeamtech.co.kr",
        stamp_omitted=True,
    )


# 호환성: 기존 코드가 sample_quotation_data() 호출
def sample_quotation_data(language: Language = Language.KO) -> QuotationPdfData:
    return (
        sample_quotation_domestic() if language == Language.KO
        else sample_quotation_overseas()
    )


def sample_pi_overseas() -> QuotationPdfData:
    """해외 PI 샘플 — PI-TEMPLATE.pdf 기반.

    Q와 거의 동일한 데이터 + document_type="PI" + po_number 추가.
    """
    base = sample_quotation_overseas()
    return base.model_copy(update={
        "document_type": "PI",
        "document_number": "PI-xx260108",
        "po_number": "#01",
    })
