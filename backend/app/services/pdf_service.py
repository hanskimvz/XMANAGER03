"""
PDF 생성 서비스

발주서, 작업지시서 등의 PDF 문서 생성 기능을 제공합니다.
발주서: 신규폼(A4 가로) 반영 (v0.99.0)
"""

from io import BytesIO
import os
import html as _html

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..core.config import settings
from ..models.purchase_order import PurchaseOrder


class PurchaseOrderPDFService:
    """발주서 PDF 생성 서비스 (신규폼, A4 가로)"""

    _W = 273 * mm  # 사용 폭(가로 A4 - 좌우여백)
    _GRAY = colors.Color(0.90, 0.90, 0.90)
    _ITEM_W = [16 * mm, 26 * mm, 111 * mm, 16 * mm, 22 * mm, 26 * mm, 33 * mm, 23 * mm]

    def __init__(self):
        self._register_korean_font()

    def _register_korean_font(self):
        """한글 폰트 등록 (맑은고딕 → 나눔고딕 폴백)."""
        font_paths = [
            "C:/Windows/Fonts/malgun.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            os.path.join(os.path.dirname(__file__), "..", "fonts", "NanumGothic.ttf"),
        ]
        registered = False
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont('Korean', fp))
                    bold = fp.replace("malgun.ttf", "malgunbd.ttf")
                    pdfmetrics.registerFont(TTFont('KoreanBold', bold if os.path.exists(bold) else fp))
                    registered = True
                    break
                except Exception:
                    continue
        if not registered:
            pdfmetrics.registerFont(TTFont('Korean', 'Helvetica'))
            pdfmetrics.registerFont(TTFont('KoreanBold', 'Helvetica-Bold'))

    # ==================== 생성 ====================
    def generate(self, purchase_order: PurchaseOrder) -> BytesIO:
        """발주서 PDF 생성 (신규폼: A4 가로)."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            leftMargin=12 * mm, rightMargin=12 * mm, topMargin=9 * mm, bottomMargin=9 * mm,
        )
        po = purchase_order
        elements = [
            self._po_title(),
            self._po_doc_info(po),
            self._po_supplier(po),
            self._po_items(po),
            self._po_total(po),
            self._po_remarks(po),
            Spacer(1, 4 * mm),
            self._po_signature(),
        ]
        doc.build(elements)
        buffer.seek(0)
        return buffer

    # -------- 유틸 --------
    @staticmethod
    def _fmt_num(v):
        try:
            f = float(v or 0)
        except (TypeError, ValueError):
            return ''
        return f'{int(f):,}' if f == int(f) else f'{f:,.2f}'

    @staticmethod
    def _fmt_date(d):
        return d.strftime('%Y.%m.%d') if d else ''

    def _label(self, text, size=9, bold=True, align=1, color=None):
        st = ParagraphStyle('L', fontName='KoreanBold' if bold else 'Korean', fontSize=size,
                            alignment=align, leading=size + 3)
        if color is not None:
            st.textColor = color
        return Paragraph(text, st)

    # -------- 섹션 --------
    def _po_title(self):
        st = ParagraphStyle('T', fontName='KoreanBold', fontSize=30, alignment=1, leading=34)
        t = Table([[Paragraph('발 주 서', st)]], colWidths=[self._W], rowHeights=[17 * mm])
        t.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return t

    def _po_doc_info(self, po):
        data = [
            [self._label('문서번호'), self._label(po.po_number or '', bold=False),
             self._label(f'TEL : {settings.COMPANY_TEL}', bold=False),
             self._label('발주일자'), self._label(self._fmt_date(po.order_date), bold=False)],
            [self._label('구매담당자'), self._label(settings.COMPANY_PURCHASE_MANAGER, bold=False),
             self._label(f'FAX : {settings.COMPANY_FAX}', bold=False),
             self._label('발주근거'), self._label('', bold=False)],
        ]
        t = Table(data, colWidths=[30 * mm, 78 * mm, 65 * mm, 30 * mm, 70 * mm])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (0, -1), self._GRAY),
            ('BACKGROUND', (3, 0), (3, -1), self._GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    def _po_supplier(self, po):
        sup = po.supplier

        def s(a):
            return _html.escape(str((getattr(sup, a, None) or '') if sup else ''))

        addr = Paragraph(s('address'), ParagraphStyle('A', fontName='Korean', fontSize=9, leading=11))
        tel = s('manager_tel') or s('tel')
        data = [
            [self._label('공급업체'), self._label('상   호'), self._label(s('partner_name'), bold=False, align=0),
             self._label('담 당 자'), self._label(s('manager_name'), bold=False, align=0)],
            ['', self._label('대 표 자'), self._label(s('representative'), bold=False, align=0),
             self._label('TEL'), self._label(tel, bold=False, align=0)],
            ['', self._label('주   소'), addr,
             self._label('FAX'), self._label(s('fax'), bold=False, align=0)],
        ]
        t = Table(data, colWidths=[20 * mm, 24 * mm, 129 * mm, 30 * mm, 70 * mm])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('SPAN', (0, 0), (0, 2)),
            ('BACKGROUND', (0, 0), (0, 2), self._GRAY),
            ('BACKGROUND', (1, 0), (1, 2), self._GRAY),
            ('BACKGROUND', (3, 0), (3, 2), self._GRAY),
            ('LEFTPADDING', (2, 0), (2, 2), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    def _po_items(self, po):
        header = [self._label(h, size=9) for h in ['No.', '품목번호', '품명/규격', '단위', '수량', '단가', '금액', '비고']]
        rows = [header]
        cell = ParagraphStyle('C', fontName='Korean', fontSize=9, leading=11, alignment=1)
        cell_l = ParagraphStyle('CL', fontName='Korean', fontSize=9, leading=11, alignment=0)
        cell_r = ParagraphStyle('CR', fontName='Korean', fontSize=9, leading=11, alignment=2)
        for idx, it in enumerate(list(po.items or []), 1):
            part = getattr(it, 'part', None)
            part_no = (getattr(part, 'part_number_display', None) or getattr(part, 'part_number', None)
                       or getattr(it, 'custom_product_code', None) or '')
            name = (getattr(part, 'part_name', None) or getattr(it, 'custom_product_name', None)
                    or getattr(it, 'custom_product_code', None) or '')
            spec = getattr(part, 'specification', None) or ''
            name_spec = name + (f'  ({spec})' if spec else '')
            u = getattr(it, 'unit', None)
            uom = getattr(u, 'name_ko', None) or getattr(u, 'name', None) or 'EA'
            amount = float(it.ordered_quantity or 0) * float(it.unit_price or 0)
            rows.append([
                Paragraph(str(idx), cell),
                Paragraph(_html.escape(str(part_no)), cell),
                Paragraph(_html.escape(str(name_spec)), cell_l),
                Paragraph(_html.escape(str(uom)), cell),
                Paragraph(self._fmt_num(it.ordered_quantity), cell_r),
                Paragraph(self._fmt_num(it.unit_price), cell_r),
                Paragraph(self._fmt_num(amount), cell_r),
                Paragraph(_html.escape(str(it.line_remarks or '')), cell_l),
            ])
        while len(rows) - 1 < 8:  # 최소 행 수(양식 높이 일관)
            rows.append(['', '', '', '', '', '', '', ''])
        t = Table(rows, colWidths=self._ITEM_W)
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), self._GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (2, 0), (2, -1), 5),
        ]))
        return t

    def _po_total(self, po):
        data = [[
            self._label('총   액'),
            self._label('화폐단위 (원)', bold=False),
            self._label(self._fmt_num(po.total_amount), size=13, align=2),
            self._label('VAT별도<br/>(최종가액)', size=8, bold=False),
        ]]
        t = Table(data, colWidths=[42 * mm, 175 * mm, 33 * mm, 23 * mm], rowHeights=[13 * mm])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (0, 0), self._GRAY),
            ('RIGHTPADDING', (2, 0), (2, 0), 5),
        ]))
        return t

    def _po_remarks(self, po):
        body_st = ParagraphStyle('RB', fontName='Korean', fontSize=8.5, leading=13)
        manual = (po.remarks or '').strip()
        lines = ['<b>&lt; 특이사항 &gt;</b>']
        if manual:
            lines.append(_html.escape(manual).replace('\n', '<br/>'))
        lines.append('1. 상기와 같이 발주 내역을 통보하오니, 납기 엄수하여 적기 공급 바랍니다.')
        lines.append('2. 본 발주서에 대하여 문의사항 또는 이의신청이 있을 시, 접수 후 4시간 이내에 당사로 통보하여 '
                     '주시기 바라며, 별도 통보가 없을 경우, 본 발주(변경)서 내용에 따라 공급하는 것으로 간주합니다.')
        para = Paragraph('<br/>'.join(lines), body_st)
        t = Table([[para]], colWidths=[self._W])
        t.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    def _po_signature(self):
        rep = ' '.join(list(settings.COMPANY_REPRESENTATIVE or ''))
        big = ParagraphStyle('SBig', fontName='KoreanBold', fontSize=22, alignment=1, leading=26)
        small = ParagraphStyle('SSm', fontName='Korean', fontSize=10, alignment=1, leading=14)
        note = ParagraphStyle('SNote', fontName='Korean', fontSize=8, alignment=1,
                              textColor=colors.Color(0.4, 0.4, 0.4), leading=11)
        data = [
            [Paragraph(f'엑스빔테크 주식회사  대표이사   {rep}', big)],
            [Paragraph('엑스빔테크 주식회사', small)],
            [Paragraph('본 발주서는 전자문서로 발행되어 서명을 생략합니다.', note)],
        ]
        t = Table(data, colWidths=[self._W])
        t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        return t
