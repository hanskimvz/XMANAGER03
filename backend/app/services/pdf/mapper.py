"""SalesDocument(DB) → QuotationPdfData(PDF 렌더) 매핑 어댑터

Phase 1: QUOTATION
Phase 2: PI 추가 (영문만)
CI 는 다음 Phase에서.
"""

from decimal import Decimal
from pathlib import Path
from typing import Optional

from app.models.sales_document import SalesDocument
from app.schemas.quotation_pdf import (
    BankInfo,
    Currency,
    CustomerInfo,
    Language,
    PriceTier,
    PackageDetails,
    PackageLine,
    QuotationLineItem,
    QuotationPdfData,
    QuotationTerms,
    ShipToInfo,
    default_company_info,
)


# 국내(KRW) 거래 시 부가세 10% — vat_excluded=True면 별도 표기, False면 합계에 포함
_DOMESTIC_VAT_RATE = Decimal("0.10")

_SUPPORTED_DOCUMENT_TYPES = ("QUOTATION", "PI", "CI", "INVOICE")

# CI 원산지 신고문(Statement of Origin) 회사 고정값 — 세관승인번호 등 변경 시 여기만 수정
# (향후 관리자 설정으로 이전 가능)
COMPANY_ORIGIN_STATEMENT = {
    "customs_auth_no": "010-23-200340",
    "origin_country": "KR",
    "place": "SEOUL",
    "coo_manager_title": "Certificate of Origin Manager",
    "sales_manager_title": "Sales Senior Manager",
    # 서명 이미지(assets/ 상대경로) — 실제 파일이 있을 때만 표기(없으면 빈칸)
    "coo_manager_sig": "assets/sig_coo_manager.png",
    "sales_manager_sig": "assets/sig_sales_manager.png",
}

# PDF assets 디렉토리 (app/templates/pdf/assets)
_PDF_ASSETS_DIR = Path(__file__).resolve().parents[2] / "templates" / "pdf" / "assets"


def _sig_if_exists(rel: Optional[str]) -> Optional[str]:
    """서명 이미지 상대경로 — 실제 파일이 있으면 그대로 반환, 없으면 None(빈칸)."""
    if not rel:
        return None
    fname = rel.replace("\\", "/").split("/")[-1]
    return rel if (_PDF_ASSETS_DIR / fname).exists() else None


def from_sales_document(
    document: SalesDocument,
    language: Language = Language.KO,
    vat_excluded: Optional[bool] = None,
) -> QuotationPdfData:
    """DB의 SalesDocument를 PDF 렌더 모델로 변환.

    QUOTATION / PI 지원. CI는 다음 Phase에서.

    document.customer 와 document.items 가 미리 로드되어 있어야 함
    (호출 측에서 joinedload 또는 selectinload 처리).

    vat_excluded:
        None  - 자동 (KRW면 True, 외화면 False)
        True  - "부가세별도" 표기 (총계는 부가세 포함값으로 별도 행 표시)
        False - VAT 합산 (외화 견적 표준)
    """
    if document.document_type not in _SUPPORTED_DOCUMENT_TYPES:
        raise ValueError(
            f"PDF 렌더는 {list(_SUPPORTED_DOCUMENT_TYPES)} 문서만 지원합니다. "
            f"(실제: {document.document_type})"
        )

    customer = _build_customer_info(document)
    ship_to = _build_ship_to(document)
    is_moq = bool(getattr(document, "is_moq", False))

    # MOQ 모드에서는 한 품목당 여러 수량 구간이 모두 같은 line_no로 저장돼 있을 수 있어
    # 렌더링 시점에 1,2,3 ... 순차 번호로 다시 부여한다.
    # 또한 같은 그룹(원래 line_no가 같은 행)의 두 번째 이후 행은 품번/설명을 비워
    # 고객 측 가독성 확보 (중복 표기 회피).
    sorted_items = sorted(document.items, key=lambda i: (i.line_no, i.id or 0))
    if is_moq:
        # MOQ 모드: 같은 line_no(원본)의 행들을 하나의 품목으로 묶음.
        # tier가 1개인 그룹은 단일 가격 품목으로(price_tiers=None) 렌더링되어
        # 같은 문서 안에서 단일/MOQ 혼합이 자연스럽게 표시된다.
        items = []
        groups: list[list] = []
        for raw in sorted_items:
            if groups and groups[-1][0].line_no == raw.line_no:
                groups[-1].append(raw)
            else:
                groups.append([raw])

        for seq, group_rows in enumerate(groups, start=1):
            head = group_rows[0]
            tiers = []
            for raw in group_rows:
                qty = raw.quantity or Decimal("0")
                up = raw.unit_price or Decimal("0")
                amt = raw.amount or Decimal("0")
                if not _item_has_tbd(raw) and (not amt or amt == Decimal("0")):
                    amt = (qty * up).quantize(Decimal("0.01"))
                tiers.append(PriceTier(
                    quantity=qty,
                    quantity_text=getattr(raw, "quantity_text", None),
                    uom=raw.uom or "EA",
                    unit_price=up,
                    unit_price_text=getattr(raw, "unit_price_text", None),
                    amount=amt,
                    amount_text=getattr(raw, "amount_text", None),
                ))
            first_tier = tiers[0]
            # tier가 2개 이상일 때만 price_tiers를 채워 스택 렌더링
            tier_field = tiers if len(tiers) >= 2 else None
            items.append(QuotationLineItem(
                line_no=seq,
                part_number=head.product_code or "",
                description=head.description,
                quantity=first_tier.quantity,
                quantity_text=first_tier.quantity_text,
                uom=first_tier.uom,
                unit_price=first_tier.unit_price,
                unit_price_text=first_tier.unit_price_text,
                amount=first_tier.amount,
                amount_text=first_tier.amount_text,
                line_remarks=head.line_remarks,
                price_tiers=tier_field,
            ))
    else:
        items = [_build_line_item(it) for it in sorted_items]

    # TBD(텍스트 오버라이드) 항목이 하나라도 있으면 합계 제외 처리 + 각주 표시
    has_tbd = any(_item_has_tbd(raw) for raw in sorted_items)

    # 혼합 견적 헤더 라벨 결정용 플래그
    has_multi_tier = any(it.price_tiers for it in items)
    has_single_tier_in_moq = is_moq and any(not it.price_tiers for it in items)

    currency = _coerce_currency(document.currency)
    # 합계:
    #  - 단일 tier 품목(price_tiers 없음): item.amount 더함 (TBD는 제외)
    #  - 멀티 tier 품목(MOQ): tier들의 합산은 의미가 모호하므로 합계에서 제외
    #  - 텍스트 오버라이드(TBD) 행은 모두 제외
    subtotal = sum(
        (
            it.amount
            for it in items
            if not it.price_tiers
            and not it.amount_text and not it.unit_price_text and not it.quantity_text
        ),
        start=Decimal("0"),
    )

    # 할인/배송비 반영 (NULL=미적용). 과세표준 = 소계 - 할인 + 배송비
    discount_amount = Decimal(str(getattr(document, "discount_amount", None) or "0"))
    shipping_fee = Decimal(str(getattr(document, "shipping_fee", None) or "0"))
    net = subtotal - discount_amount + shipping_fee
    if net < 0:
        net = Decimal("0")

    if vat_excluded is None:
        vat_excluded = currency == Currency.KRW

    if currency == Currency.KRW:
        vat_rate = _DOMESTIC_VAT_RATE
        vat_amount = (net * vat_rate).quantize(Decimal("0.01"))
    else:
        vat_rate = Decimal("0")
        vat_amount = Decimal("0")

    total = net + vat_amount

    def _fmt_ci_date(d):
        """CI 일자 표기 통일 (예: 08.APR.2025)."""
        try:
            return d.strftime('%d.%b.%Y').upper() if d else None
        except Exception:
            return None

    terms = QuotationTerms(
        payment_terms=document.payment_terms,
        delivery_terms=document.delivery_terms,
        valid_until=document.valid_until,
        country_of_origin=document.country_of_origin,
        hs_code=document.hs_code,
        remarks=document.remarks,
        # CI 전용 선적 정보
        ship_from=getattr(document, "ship_from", None),
        destination=getattr(document, "destination", None),
        transportation=getattr(document, "transportation", None),
        shipment_date=_fmt_ci_date(getattr(document, "shipment_date", None)),
    )

    # CI 원산지 신고문(Statement of Origin) — 문서에서 표기 선택 시에만
    if getattr(document, "show_statement_of_origin", False):
        cfg = COMPANY_ORIGIN_STATEMENT
        _so_date = _fmt_ci_date(getattr(document, "shipment_date", None)) or _fmt_ci_date(getattr(document, "document_date", None))
        terms.statement_of_origin = {
            "text": (
                f"The exporter of the products covered by this document "
                f"(customs authorization No {cfg['customs_auth_no']}) declares that, "
                f"except where otherwise clearly indicated, these products are of "
                f"{cfg['origin_country']} preferential origin."
            ),
            "place": cfg["place"],
            "date": _so_date,
            "coo_title": cfg["coo_manager_title"],
            "sales_title": cfg["sales_manager_title"],
            "coo_sig": _sig_if_exists(cfg.get("coo_manager_sig")),
            "sales_sig": _sig_if_exists(cfg.get("sales_manager_sig")),
        }

    # CI 전용: 포장 명세 / 연결 PI·PO 정보
    package = None
    pi_number = None
    pi_date = None
    po_date = _fmt_ci_date(getattr(document, "customer_po_date", None))
    po_number = getattr(document, "customer_po_number", None)
    if document.document_type == "CI":
        total_qty = sum((it.quantity for it in items if it.quantity), Decimal("0"))

        def _dims_from_box(b):
            parts = [b.get("length"), b.get("width"), b.get("height")]
            if all(x is not None for x in parts):
                def _n(x):
                    f = float(x)
                    return int(f) if f == int(f) else f
                return " x ".join(str(_n(x)) for x in parts)
            return None

        pl = getattr(document, "packing_list", None) or []
        if pl:
            # 박스별 packing list → 라인 + 합계
            lines = []
            tot_boxes = 0
            tot_gross = Decimal("0")
            tot_net = Decimal("0")
            for b in pl:
                qty = int(b.get("quantity") or 0) or 1
                gw = b.get("gross_weight")
                nw = b.get("net_weight")
                lines.append(PackageLine(
                    box_type=b.get("box_type"),
                    quantity=qty,
                    gross_weight=Decimal(str(gw)) if gw is not None else None,
                    net_weight=Decimal(str(nw)) if nw is not None else None,
                    dimensions=_dims_from_box(b),
                ))
                tot_boxes += qty
                if gw is not None:
                    tot_gross += Decimal(str(gw)) * qty
                if nw is not None:
                    tot_net += Decimal(str(nw)) * qty
            package = PackageDetails(
                boxes=tot_boxes or None,
                gross_weight=(tot_gross or None),
                net_weight=(tot_net or None),
                total_quantity=(total_qty or None),
                dimensions=(lines[0].dimensions if len(lines) == 1 else None),
                lines=lines,
            )
        else:
            # packing list 없으면 단일 요약 필드 사용(수동 입력)
            pkg_boxes = getattr(document, "packaging_boxes", None)
            pkg_dims = getattr(document, "packaging_dimensions", None)
            pkg_gross = getattr(document, "packaging_gross_weight", None)
            pkg_net = getattr(document, "packaging_net_weight", None)
            if pkg_boxes or pkg_dims or pkg_gross is not None or pkg_net is not None or total_qty:
                package = PackageDetails(
                    boxes=pkg_boxes,
                    dimensions=pkg_dims,
                    gross_weight=pkg_gross,
                    net_weight=pkg_net,
                    total_quantity=(total_qty or None),
                )
        # 연결된 PI(원본) 번호/일자 + PO 번호 — 합배송(여러 PI→1 CI)이면 각 PI/PO를 모두 표기
        try:
            links = list(getattr(document, "source_links", None) or [])
            sources = [ln.source for ln in links if getattr(ln, "source", None) is not None]
            if not sources:
                sd = getattr(document, "source_document", None)
                if sd is not None:
                    sources = [sd]
            # 링크 생성 순서 보장을 위해 문서번호로 정렬(안정적 표기)
            sources.sort(key=lambda s: getattr(s, "document_number", "") or "")
            pi_nums, po_nums = [], []
            for s in sources:
                if getattr(s, "document_type", None) != "PI":
                    continue
                num = (getattr(s, "document_number", None) or "").strip()
                if num and num not in pi_nums:
                    pi_nums.append(num)
                    if pi_date is None:
                        pi_date = _fmt_ci_date(getattr(s, "document_date", None))
                cpo = (getattr(s, "customer_po_number", None) or "").strip()
                if cpo and cpo not in po_nums:
                    po_nums.append(cpo)
            if pi_nums:
                pi_number = ", ".join(pi_nums)
            if po_nums:
                po_number = ", ".join(po_nums)
        except Exception:
            pass

    bank = _build_bank_info(document)

    return QuotationPdfData(
        language=language,
        document_type=document.document_type,
        document_number=document.document_number,
        document_date=document.document_date,
        version=document.version or 1,
        po_number=po_number,
        company=default_company_info(),
        customer=customer,
        ship_to=ship_to,
        items=items,
        is_moq=is_moq,
        has_multi_tier=has_multi_tier,
        has_single_tier_in_moq=has_single_tier_in_moq,
        has_tbd=has_tbd,
        currency=currency,
        subtotal=subtotal,
        discount_amount=discount_amount,
        discount_reason=getattr(document, "discount_reason", None),
        shipping_fee=shipping_fee,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        total=total,
        vat_excluded=vat_excluded,
        terms=terms,
        package=package,
        pi_number=pi_number,
        pi_date=pi_date,
        po_date=po_date,
        bank=bank,
        prepared_by=document.prepared_by,
        prepared_email=document.prepared_email,
        stamp_omitted=(language == Language.KO),  # 국내 양식 기본 직인생략
    )


def _build_customer_info(document: SalesDocument) -> CustomerInfo:
    bp = document.customer
    if bp is None:
        return CustomerInfo(name="-")

    address_parts = [getattr(bp, "address", None), getattr(bp, "address_detail", None)]
    address = " ".join(p for p in address_parts if p) or None

    # 문서에 지정된 담당자(v0.52.0) 우선, 없으면 거래처 기본 담당자(manager_name) 폴백
    contact = getattr(document, "customer_contact", None)
    contact_person = (contact.name if contact else None) or getattr(bp, "manager_name", None)

    # 연락처(전화/이메일): 지정 담당자 개별값 우선 → 거래처 기본 담당자(manager_*) → 회사 대표 연락처
    def _first(*vals):
        for v in vals:
            if v:
                return v
        return None

    tel = _first(
        getattr(contact, "tel_office", None) if contact else None,
        getattr(contact, "tel_mobile", None) if contact else None,
        getattr(bp, "manager_tel", None),
        getattr(bp, "manager_mobile", None),
        getattr(bp, "tel", None),
    )
    email = _first(
        getattr(contact, "email", None) if contact else None,
        getattr(bp, "manager_email", None),
        getattr(bp, "email", None),
    )

    # 거래처 VAT/TAX ID(사업자등록번호): 문서에서 표기 선택 시에만 노출
    tax_id = None
    if getattr(document, "show_customer_tax_id", False):
        tax_id = getattr(bp, "business_number", None) or None

    return CustomerInfo(
        name=bp.partner_name or "-",
        name_en=getattr(bp, "partner_name_en", None),
        contact_person=contact_person,
        address=address,
        country=getattr(bp, "country_name", None),
        tel=tel,
        email=email,
        tax_id=tax_id,
    )


def _build_ship_to(document: SalesDocument) -> ShipToInfo:
    """수령자(Ship-To) 매핑.
    1) 저장된 거래처 배송지(ship_to_address_id) 선택 시 그 주소
    2) 직접입력 ship_to_* 값
    3) 둘 다 없으면 same_as_buyer=True.
    """
    saved = getattr(document, "shipping_address", None)
    if saved is not None:
        return ShipToInfo(
            same_as_buyer=False,
            name=getattr(saved, "name", None) or getattr(saved, "label", None),
            address=getattr(saved, "address", None),
            contact=getattr(saved, "contact", None),
            phone=getattr(saved, "phone", None),
            email=getattr(saved, "email", None),
        )

    name = getattr(document, "ship_to_name", None)
    address = getattr(document, "ship_to_address", None)
    contact = getattr(document, "ship_to_contact", None)
    phone = getattr(document, "ship_to_phone", None)
    email = getattr(document, "ship_to_email", None)

    if not (name or address or contact or phone or email):
        return ShipToInfo(same_as_buyer=True)

    return ShipToInfo(
        same_as_buyer=False,
        name=name,
        address=address,
        contact=contact,
        phone=phone,
        email=email,
    )


def _build_line_item(item) -> QuotationLineItem:
    return QuotationLineItem(
        line_no=item.line_no,
        part_number=item.product_code,
        description=item.description,
        quantity=item.quantity or Decimal("0"),
        quantity_text=getattr(item, "quantity_text", None),
        uom=item.uom or "EA",
        unit_price=item.unit_price or Decimal("0"),
        unit_price_text=getattr(item, "unit_price_text", None),
        amount=item.amount or Decimal("0"),
        amount_text=getattr(item, "amount_text", None),
        line_remarks=item.line_remarks,
    )


def _item_has_tbd(item) -> bool:
    """원본 ORM 행에 텍스트 오버라이드가 하나라도 있으면 True (합계 제외 대상)."""
    return any(
        getattr(item, f, None)
        for f in ("quantity_text", "unit_price_text", "amount_text")
    )


def _build_bank_info(document: SalesDocument) -> Optional[BankInfo]:
    fields = (document.bank_name, document.swift_code, document.account_number)
    if not any(fields):
        return None
    return BankInfo(
        bank_name=document.bank_name,
        bank_address=document.bank_address,
        swift_code=document.swift_code,
        account_name=document.account_name,
        account_number=document.account_number,
    )


def _coerce_currency(value: Optional[str]) -> Currency:
    if not value:
        return Currency.USD
    try:
        return Currency(value.upper())
    except ValueError:
        return Currency.USD
