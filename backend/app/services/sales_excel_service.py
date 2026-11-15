"""
영업 문서 엑셀 생성 서비스 (템플릿 기반)

실제 양식 파일(docs/samples/sales-export/)을 복사한 뒤 데이터 셀만 채우는 방식.
로고, 서식, 병합, 테두리 등이 원본과 100% 동일합니다.

영업 담당자가 다운로드 후 편집(볼드, 색상 등)하여 PDF로 변환 후 고객 발송
"""

import os
from copy import copy
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Side

from app.models.sales_document import SalesDocument

# 템플릿 파일 경로 — docs/samples/sales-export/ 직접 참조
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "samples", "sales-export")

# 공통 스타일 상수
_FONT = Font(name="Arial Nova", size=9)
_FONT_BOLD = Font(name="Arial Nova", size=9, bold=True)
_ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
_ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")
_ALIGN_LEFT = Alignment(vertical="center")
_ALIGN_WRAP = Alignment(vertical="center", wrap_text=True)
_THIN = Side(style="thin")
_MEDIUM = Side(style="medium")

# 금액 표기: 국내 견적서는 원화 → 천 단위 콤마(정수). 해외 문서는 각 셀에서 #,##0.00 별도 지정.
_KRW_FMT = "#,##0"

# 품목 영역 컬럼 목록 (B~I, D는 빈 컬럼)
_ITEM_COLS = ["B", "C", "D", "E", "F", "G", "H", "I"]


class SalesExcelService:
    """영업 문서 엑셀 생성 (템플릿 복사 + 데이터 채움)"""

    def _is_domestic(self, doc: SalesDocument) -> bool:
        """고객사의 거래유형이 국내인지 확인"""
        if doc.customer and hasattr(doc.customer, 'trade_type'):
            return doc.customer.trade_type == "DOMESTIC"
        return False

    def generate(self, doc: SalesDocument) -> BytesIO:
        """문서 유형에 따라 적절한 템플릿으로 엑셀 생성"""
        is_domestic = self._is_domestic(doc)

        if is_domestic and doc.document_type in ("QUOTATION", "PI"):
            # 국내 고객: 국내 견적서 양식 사용
            template_path = os.path.join(TEMPLATE_DIR, "Q-DOMESTIC-TEMPLATE.xlsx")
            if not os.path.exists(template_path):
                template_path = os.path.join(TEMPLATE_DIR, "Q-TEMPLATE.xlsx")

            wb = load_workbook(template_path)
            ws = wb.active or wb.worksheets[0]
            self._fill_domestic_quotation(ws, doc)
        else:
            # 해외 고객: 기존 로직
            template_map = {
                "QUOTATION": "Q-TEMPLATE.xlsx",
                "PI": "PI-TEMPLATE.xlsx",
                "CI": "CI-TEMPLATE.xlsx",
            }
            template_name = template_map.get(doc.document_type, "Q-TEMPLATE.xlsx")
            template_path = os.path.join(TEMPLATE_DIR, template_name)

            if not os.path.exists(template_path):
                template_path = os.path.join(TEMPLATE_DIR, "Q-TEMPLATE.xlsx")

            wb = load_workbook(template_path)
            ws = wb.active or wb.worksheets[0]

            if doc.document_type == "CI":
                self._fill_ci(ws, doc)
            else:
                self._fill_quotation_pi(ws, doc)

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    # ====================================================================
    #  셀 클리어 & 스타일 헬퍼
    # ====================================================================

    def _clear_rows(self, ws, start_row: int, end_row: int):
        """지정 범위의 셀 값을 모두 지우고 테두리도 초기화"""
        for row in range(start_row, end_row + 1):
            for col in _ITEM_COLS:
                cell = ws[f"{col}{row}"]
                cell.value = None
                cell.border = Border()  # 테두리 제거

    def _apply_item_code_style(self, ws, row: int):
        """품목 코드 행 스타일 (B=line_no, C=product_code, F=qty, G=uom, H=price, I=amount)"""
        ws[f"B{row}"].font = _FONT
        ws[f"B{row}"].alignment = _ALIGN_CENTER
        ws[f"C{row}"].font = _FONT_BOLD
        ws[f"C{row}"].alignment = _ALIGN_LEFT
        ws[f"F{row}"].font = _FONT
        ws[f"F{row}"].alignment = _ALIGN_RIGHT
        ws[f"G{row}"].font = _FONT
        ws[f"G{row}"].alignment = Alignment(horizontal="left", vertical="center")
        ws[f"H{row}"].font = _FONT
        ws[f"H{row}"].alignment = _ALIGN_LEFT
        ws[f"H{row}"].number_format = "#,##0.00"
        ws[f"I{row}"].font = _FONT
        ws[f"I{row}"].alignment = _ALIGN_LEFT
        ws[f"I{row}"].number_format = "#,##0.00"

    def _apply_desc_style(self, ws, row: int):
        """Description 행 스타일"""
        ws[f"C{row}"].font = _FONT
        ws[f"C{row}"].alignment = _ALIGN_WRAP

    def _apply_total_border(self, ws, row: int):
        """TOTAL 행 테두리 (top=thin, bottom=medium)"""
        total_border = Border(top=_THIN, bottom=_MEDIUM)
        for col in _ITEM_COLS:
            ws[f"{col}{row}"].border = total_border

    def _apply_first_item_top_border(self, ws, row: int):
        """첫 품목 행 상단 테두리 (헤더와 구분)"""
        for col in _ITEM_COLS:
            cell = ws[f"{col}{row}"]
            cell.border = Border(top=_THIN)

    def _move_signature_image(self, ws, sign_row: int):
        """서명/도장 이미지를 동적 sign_row에 맞춰 이동 (고정 크기 유지)

        TwoCellAnchor → OneCellAnchor로 변환하여 행 높이에 관계없이
        원본 템플릿과 동일한 크기(6.11cm x 2.9cm)를 유지합니다.
        """
        from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, AnchorMarker
        from openpyxl.utils.units import cm_to_EMU
        from openpyxl.drawing.xdr import XDRPositiveSize2D

        for idx, img in enumerate(ws._images):
            anc = img.anchor
            if not hasattr(anc, '_from'):
                continue
            if anc._from.row < 20:  # 상단 로고 스킵
                continue

            # 원본 colOff 보존
            col_off = anc._from.colOff

            # 새 위치: sign_row + 2 (1-indexed) → sign_row + 1 (0-indexed)
            new_row = sign_row + 1  # 0-indexed

            # OneCellAnchor: 시작점 + 고정 크기 (원본 템플릿: 6.11cm x 2.9cm)
            marker = AnchorMarker(col=1, row=new_row, colOff=col_off, rowOff=0)
            size = XDRPositiveSize2D(cm_to_EMU(6.11), cm_to_EMU(2.9))
            img.anchor = OneCellAnchor(_from=marker, ext=size)

            break

    # ====================================================================
    #  Q / PI 채움
    # ====================================================================

    def _fill_quotation_pi(self, ws, doc: SalesDocument):
        """Q/PI 템플릿에 데이터 채움"""
        customer = doc.customer

        # === 문서 정보 (행 5~9) ===
        title_map = {"QUOTATION": "QUOTATION", "PI": "PROFORMA INVOICE"}
        prefix_map = {"QUOTATION": "Q", "PI": "PI"}
        prefix = prefix_map.get(doc.document_type, "Q")

        ws["B5"] = title_map.get(doc.document_type, doc.document_type)
        ws["B7"] = f"{prefix} No.:"
        ws["C7"] = doc.document_number
        ws["B8"] = f"{prefix} Date:"
        ws["C8"] = doc.document_date.strftime("%d.%b.%Y").upper() if doc.document_date else ""
        ws["E7"] = "Prepared by:"
        ws["F7"] = doc.prepared_by or ""
        ws["E8"] = "Email:"
        ws["F8"] = doc.prepared_email or ""

        if doc.document_type == "PI":
            ws["B9"] = "PO No.:"
            ws["C9"] = doc.customer_po_number or ""

        # === BUYER (행 11~17) ===
        ws["C12"] = (customer.partner_name_en or customer.partner_name) if customer else ""
        ws["C13"] = (customer.address or "") if customer else ""
        ws["C15"] = (customer.manager_name or "") if customer else ""
        ws["C16"] = (customer.tel or "") if customer else ""
        ws["C17"] = (customer.manager_email or "") if customer else ""

        ws["E12"] = doc.ship_to_name or "Same as Buyer"

        # === Terms & Conditions (행 20~24) ===
        ws["B20"] = f"Payment Terms: {doc.payment_terms or ''}"
        ws["B21"] = f"Delivery Terms: {doc.delivery_terms or ''}"
        ws["B22"] = f"HS Code: {doc.hs_code or ''}"
        ws["B23"] = f"Country of Origin: {doc.country_of_origin or ''}"
        ws["B24"] = f"Valid Until: {doc.valid_until or ''}"

        # === Bank Details (행 20~24) ===
        ws["E20"] = f"Bank: {doc.bank_name or ''}"
        ws["E21"] = f"Bank Address: {doc.bank_address or ''}"
        ws["E22"] = f"Swift Code: {doc.swift_code or ''}"
        ws["E23"] = f"Account Name: {doc.account_name or ''}"
        ws["E24"] = f"Account No.: {doc.account_number or ''}"

        # === 품목 영역: 28행부터 서명란까지 클리어 후 재작성 ===
        # 템플릿 구조: 28~36(품목) → 37(TOTAL) → 39(Signed) → 47(President)
        # 품목 수에 관계없이 동일한 양식을 유지

        sorted_items = sorted(doc.items, key=lambda x: x.line_no)

        # 28행 이후 모든 병합 셀 해제
        for mc in list(ws.merged_cells.ranges):
            if mc.min_row >= 28:
                ws.unmerge_cells(str(mc))

        # 28~60행 전체 클리어 (충분히 넓게, A~J 포함)
        for r in range(28, 61):
            for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
                cell = ws[f"{col}{r}"]
                cell.value = None
                cell.border = Border()

        # === 품목 데이터 쓰기 ===
        row = 28
        is_moq = getattr(doc, 'is_moq', False)

        if is_moq:
            # MOQ 모드: 같은 line_no끼리 그룹화
            from itertools import groupby
            grouped = {}
            for item in sorted_items:
                ln = item.line_no
                if ln not in grouped:
                    grouped[ln] = []
                grouped[ln].append(item)

            # Quantity 헤더를 MOQ로 변경 (27행)
            ws["E27"] = "Quantity"
            ws["E28"] = None  # 기존 값 클리어 (있으면)

            for ln in sorted(grouped.keys()):
                items = grouped[ln]
                first = items[0]

                if row == 28:
                    self._apply_first_item_top_border(ws, row)

                # 첫 행: Line No + product_code
                ws[f"B{row}"] = ln
                ws[f"C{row}"] = first.product_code
                ws[f"F{row}"] = float(items[0].quantity)
                ws[f"G{row}"] = items[0].uom or "pc"
                ws[f"H{row}"] = float(items[0].unit_price)
                # Amount 비움 (MOQ 견적)
                self._apply_item_code_style(ws, row)
                row += 1

                # 추가 MOQ 가격 행
                for extra in items[1:]:
                    ws[f"F{row}"] = float(extra.quantity)
                    ws[f"G{row}"] = extra.uom or "pc"
                    ws[f"H{row}"] = float(extra.unit_price)
                    ws[f"F{row}"].font = _FONT
                    ws[f"F{row}"].alignment = _ALIGN_RIGHT
                    ws[f"G{row}"].font = _FONT
                    ws[f"H{row}"].font = _FONT
                    ws[f"H{row}"].number_format = "#,##0.00"
                    row += 1

                # Description
                if first.description:
                    ws[f"C{row}"] = first.description
                    self._apply_desc_style(ws, row)
                row += 1

                # 빈 구분행
                row += 1
        else:
            # 일반 모드
            for item in sorted_items:
                if row == 28:
                    self._apply_first_item_top_border(ws, row)

                ws[f"B{row}"] = item.line_no
                ws[f"C{row}"] = item.product_code
                # TBD 등 텍스트 오버라이드가 있으면 숫자 대신 문자열 출력
                ws[f"F{row}"] = (item.quantity_text or float(item.quantity)) if getattr(item, "quantity_text", None) else float(item.quantity)
                ws[f"G{row}"] = item.uom or "pc"
                ws[f"H{row}"] = (item.unit_price_text or float(item.unit_price)) if getattr(item, "unit_price_text", None) else float(item.unit_price)
                amt_text = getattr(item, "amount_text", None)
                up_text = getattr(item, "unit_price_text", None)
                qty_text = getattr(item, "quantity_text", None)
                if amt_text or up_text or qty_text:
                    ws[f"I{row}"] = amt_text or "TBD"
                else:
                    ws[f"I{row}"] = float(item.amount)
                self._apply_item_code_style(ws, row)
                row += 1

                if item.description:
                    ws[f"C{row}"] = item.description
                    self._apply_desc_style(ws, row)
                row += 1

                # 빈 구분행
                row += 1

        # === 품목 마지막 행 하단 테두리 (TOTAL 위 구분선) ===
        pre_total_row = row - 1  # 마지막 빈 구분행
        for col in _ITEM_COLS:
            ws[f"{col}{pre_total_row}"].border = Border(bottom=_THIN)

        # === TOTAL 행 ===
        total_row = row
        ws.row_dimensions[total_row].height = 27
        ws[f"E{total_row}"] = "TOTAL"
        ws[f"E{total_row}"].font = _FONT_BOLD
        ws[f"E{total_row}"].alignment = _ALIGN_RIGHT
        if not is_moq:
            # TBD 항목은 합계에서 제외
            ws[f"F{total_row}"] = sum(
                float(item.quantity)
                for item in doc.items
                if not getattr(item, "quantity_text", None)
                and not getattr(item, "unit_price_text", None)
                and not getattr(item, "amount_text", None)
            )
        ws[f"F{total_row}"].font = _FONT_BOLD
        ws[f"F{total_row}"].alignment = _ALIGN_RIGHT
        ws[f"H{total_row}"] = doc.currency or "USD"
        ws[f"H{total_row}"].font = _FONT_BOLD
        ws[f"H{total_row}"].alignment = _ALIGN_RIGHT
        ws[f"I{total_row}"] = "-" if is_moq else float(doc.total_amount)
        ws[f"I{total_row}"].font = _FONT_BOLD
        ws[f"I{total_row}"].number_format = "#,##0.00"
        self._apply_total_border(ws, total_row)
        # A열, J열 외곽 닫기 (템플릿과 동일)
        ws[f"A{total_row}"].border = Border(bottom=_MEDIUM)
        ws[f"J{total_row}"].border = Border(bottom=_MEDIUM)

        # === 서명란 (템플릿과 동일한 서식) ===
        sign_row = total_row + 2
        # "Signed (The Seller)" / "Signed (The Buyer)"
        ws.merge_cells(f"B{sign_row}:C{sign_row}")
        ws[f"B{sign_row}"] = "Signed (The Seller)"
        ws[f"B{sign_row}"].font = _FONT_BOLD
        ws[f"B{sign_row}"].alignment = _ALIGN_LEFT
        ws[f"F{sign_row}"] = "Signed (The Buyer)"
        ws[f"F{sign_row}"].font = _FONT_BOLD
        ws[f"F{sign_row}"].alignment = _ALIGN_LEFT

        # "President..." / "Accepted..." (서명 이미지 아래, 6행 뒤)
        footer_row = sign_row + 6
        ws.merge_cells(f"B{footer_row}:C{footer_row}")
        ws[f"B{footer_row}"] = "President of X-Beam Tech Co.,Ltd."
        ws[f"B{footer_row}"].font = Font(name="Arial Nova", size=9, bold=True)
        ws[f"B{footer_row}"].alignment = _ALIGN_CENTER
        # footer top border (서명 하단 구분선)
        ws[f"B{footer_row}"].border = Border(top=_THIN)
        ws[f"C{footer_row}"].border = Border(top=_THIN)

        ws.merge_cells(f"F{footer_row}:I{footer_row}")
        ws[f"F{footer_row}"] = "Accepted by the Buyer"
        ws[f"F{footer_row}"].font = Font(name="Arial Nova", size=9, bold=True)
        ws[f"F{footer_row}"].alignment = _ALIGN_CENTER
        for c in ["F", "G", "H", "I"]:
            ws[f"{c}{footer_row}"].border = Border(top=_THIN)

        # === 서명 이미지 위치 이동 ===
        self._move_signature_image(ws, sign_row)

    # ====================================================================
    #  CI 채움
    # ====================================================================

    def _fill_ci(self, ws, doc: SalesDocument):
        """CI 템플릿에 데이터 채움

        템플릿 구조:
        Row 7-22: 헤더 (Shipper, Consignee, 문서정보)
        Row 24-25: 품목 헤더 (Line No. / Description / K=Qty / L=UOM / M=Unit Price / N=Amount)
        Row 25-31: 품목 영역 + 계산용 Q,R열
        Row 32: Package Details + Total Qty + Invoice Total
        Row 33-35: Package 상세 (병합 셀 있음)
        Row 46: Signed by
        Row 54: President of X-Beam Tech Co.,Ltd.
        """
        customer = doc.customer

        # === 문서 정보 (우측: J=라벨, L=값) ===
        ws["J8"] = doc.document_number
        ws["L8"] = doc.document_date.strftime("%d.%b.%Y").upper() if doc.document_date else ""
        # Customer PO No (J9 값, L9 날짜)
        ws["J10"] = doc.customer_po_number or ""
        ws["L9"] = doc.customer_po_date.strftime("%d.%b.%Y").upper() if doc.customer_po_date else ""
        # PI No (소스 문서에서)
        if doc.source_document:
            ws["J12"] = doc.source_document.document_number
            ws["L12"] = doc.source_document.document_date.strftime("%d.%b.%Y").upper() if doc.source_document.document_date else ""
        ws["L13"] = doc.ship_from or "Seoul, Korea"
        ws["L14"] = doc.destination or ""
        ws["L15"] = doc.transportation or ""
        ws["L16"] = doc.shipment_date.strftime("%d.%b.%Y").upper() if doc.shipment_date else ""
        ws["L18"] = doc.payment_terms or ""
        ws["L19"] = doc.delivery_terms or ""
        ws["L21"] = doc.country_of_origin or "Republic of Korea"
        ws["L22"] = doc.hs_code or ""

        # === CONSIGNEE (주소 자동 2줄 분할) ===
        if customer:
            ws["B14"] = customer.partner_name_en or customer.partner_name
            address = customer.address or ""
            # 주소가 길면 2줄로 분할 (60자 기준)
            if len(address) > 60:
                mid = address.rfind(",", 0, 60)
                if mid == -1:
                    mid = address.rfind(" ", 0, 60)
                if mid > 0:
                    ws["B15"] = address[:mid + 1].strip()
                    ws["B16"] = address[mid + 1:].strip()
                else:
                    ws["B15"] = address
            else:
                ws["B15"] = address
            ws["B17"] = f"Contact: {customer.manager_name or ''}"
            ws["B18"] = f"Phone: {customer.tel or ''}"
            ws["B19"] = f"Email: {customer.manager_email or ''}"

        # === 품목 영역 값만 클리어 (27~31행, 서식/테두리 유지) ===
        for r in range(27, 32):
            for col in ["B", "C", "K", "L", "M", "N"]:
                ws[f"{col}{r}"].value = None

        # === 품목 데이터 ===
        sorted_items = sorted(doc.items, key=lambda x: x.line_no)
        row = 27
        total_qty = 0
        total_amount = 0

        for item in sorted_items:
            ws[f"B{row}"] = item.line_no
            ws[f"B{row}"].font = _FONT
            ws[f"B{row}"].alignment = _ALIGN_CENTER
            ws[f"C{row}"] = item.product_code
            ws[f"C{row}"].font = _FONT_BOLD
            qty = float(item.quantity)
            uom = item.uom or "pc"
            price = float(item.unit_price) if item.unit_price else 0
            amount = float(item.amount) if item.amount else qty * price
            qty_text = getattr(item, "quantity_text", None)
            up_text = getattr(item, "unit_price_text", None)
            amt_text = getattr(item, "amount_text", None)
            ws[f"K{row}"] = qty_text or qty
            ws[f"K{row}"].font = _FONT
            ws[f"K{row}"].alignment = _ALIGN_RIGHT
            ws[f"L{row}"] = uom
            ws[f"L{row}"].font = _FONT
            if up_text:
                ws[f"M{row}"] = up_text
                ws[f"M{row}"].font = _FONT
            elif price > 0:
                ws[f"M{row}"] = price
                ws[f"M{row}"].font = _FONT
                ws[f"M{row}"].number_format = "#,##0.00"
            if amt_text or up_text or qty_text:
                ws[f"N{row}"] = amt_text or "TBD"
                ws[f"N{row}"].font = _FONT
            elif amount > 0:
                ws[f"N{row}"] = amount
                ws[f"N{row}"].font = _FONT
                ws[f"N{row}"].number_format = "#,##0.00"
            total_qty += qty
            total_amount += amount
            row += 1

            if item.description:
                ws.merge_cells(f"C{row}:I{row}")
                ws[f"C{row}"] = item.description
                ws[f"C{row}"].font = _FONT
                ws[f"C{row}"].alignment = _ALIGN_WRAP
            row += 1

            row += 1  # 빈 구분행

        # === Package Details (고정 32행) — 값만 교체 ===
        ws[f"K32"] = total_qty
        ws[f"N32"] = total_amount if total_amount > 0 else ""
        if total_amount > 0:
            ws[f"N32"].number_format = "#,##0.00"
        ws[f"N33"] = doc.currency or "USD"

        # 36~45행 높이 축소 (서명까지 간격 줄이기, 인쇄 1페이지 맞춤)
        for r in range(36, 46):
            ws.row_dimensions[r].height = 6

        # Package 데이터 (고정 35행) — 값만 교체
        ws[f"B35"] = f"{doc.packaging_boxes} Box" if doc.packaging_boxes else ""
        ws[f"C35"] = float(doc.packaging_gross_weight) if doc.packaging_gross_weight else ""
        ws[f"D35"] = float(doc.packaging_net_weight) if doc.packaging_net_weight else ""
        if doc.packaging_dimensions and "x" in doc.packaging_dimensions:
            dims = doc.packaging_dimensions.split("x")
            if len(dims) >= 3:
                ws[f"E35"] = dims[0].strip()
                ws[f"F35"] = dims[1].strip()
                ws[f"G35"] = dims[2].strip()

    # ====================================================================
    #  국내 견적서 채움
    # ====================================================================

    def _fill_domestic_quotation(self, ws, doc: SalesDocument):
        """국내 견적서 템플릿에 데이터 채움

        템플릿 구조:
        Row 3:  수신 (고객사)
        Row 5:  견적번호, 상호, 대표이사
        Row 6:  견적일자, 주소
        Row 7:  유효기간, 업종, 업태
        Row 8:  참조, 대표전화, 팩스
        Row 9:  결제조건, 담당자
        Row 11: 견적금액 합계
        Row 13: 헤더 (No, Description, Q'ty, Unit, Unit Price, Total Price, Remark)
        Row 14+: 품목 (각 품목 1행)
        합계행: 부가세별도
        총계행: 부가세합계
        """
        customer = doc.customer

        # 수신
        ws["A3"] = f"수신 : {customer.partner_name} 귀중" if customer else "수신 :"

        # 견적 정보
        ws["A5"] = f"1. 견적번호 : {doc.document_number}"
        if doc.document_date:
            d = doc.document_date
            ws["A6"] = f"2. 견적일자 : {d.year}년 {d.month}월 {d.day}일"
        ws["A7"] = f"3. 유효기간 : {doc.valid_until or '견적일로 부터 4주'}"
        ws["A8"] = f"4. 참      조 : {doc.remarks or ''}"
        ws["A9"] = f"5. 결제조건 : {doc.payment_terms or '현금 결제'}"

        # 담당자
        prepared = doc.prepared_by or ""
        email = doc.prepared_email or ""
        if prepared or email:
            ws["D9"] = f"      담당 : {prepared}, {email}" if email else f"      담당 : {prepared}"

        # === 품목 영역 ===
        # Row 13: 헤더 (고정)
        # Row 14+: 품목 데이터

        sorted_items = sorted(doc.items, key=lambda x: x.line_no)
        row = 14

        # 기존 샘플 데이터 클리어 (14~16행)
        for r in range(14, 20):
            for col in ['A', 'B', 'C', 'D', 'E', 'H', 'K']:
                cell = ws[f"{col}{r}"]
                if not isinstance(cell, type(None)):
                    try:
                        cell.value = None
                    except AttributeError:
                        pass  # merged cell

        # 품목 쓰기
        for item in sorted_items:
            ws[f"A{row}"] = item.line_no
            # Description: product_code + description 결합
            desc_text = f"  {item.product_code}"
            if item.description:
                desc_text += f"\n  {item.description}"
            ws[f"B{row}"] = desc_text
            qty_text = getattr(item, "quantity_text", None)
            up_text = getattr(item, "unit_price_text", None)
            amt_text = getattr(item, "amount_text", None)
            ws[f"C{row}"] = qty_text or float(item.quantity)
            ws[f"D{row}"] = item.uom or "EA"
            ws[f"E{row}"] = up_text or float(item.unit_price)
            ws[f"E{row}"].number_format = _KRW_FMT  # 단가: 천 단위 콤마(국내=원화)
            if amt_text or up_text or qty_text:
                ws[f"H{row}"] = amt_text or "TBD"
            else:
                ws[f"H{row}"] = float(item.amount)
            ws[f"H{row}"].number_format = _KRW_FMT  # 금액
            row += 1

        # 합계행
        total_row = row
        ws[f"A{total_row}"] = "합     계"
        ws[f"E{total_row}"] = "부가세별도"
        ws[f"H{total_row}"] = float(doc.total_amount)
        ws[f"H{total_row}"].number_format = _KRW_FMT

        # 총계행 (부가세 포함) — round로 부동소수 노이즈 제거
        total_vat_row = total_row + 1
        ws[f"A{total_vat_row}"] = "총     계"
        ws[f"E{total_vat_row}"] = "부가세합계"
        ws[f"H{total_vat_row}"] = round(float(doc.total_amount) * 1.1)
        ws[f"H{total_vat_row}"].number_format = _KRW_FMT
