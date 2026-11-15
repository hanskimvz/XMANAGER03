"""
퇴사 연차 정산 엑셀 생성 (v0.45.x)

이미지 양식 기준: 입사/퇴사 + 연도별 사용내역 + 입사일 기준 발생내역 + 정산 요약(사용·잔여까지).
임금/연차수당 금액은 산출하지 않는다(사용자 요청).
"""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

_THIN = Side(style="thin", color="BBBBBB")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_HEAD_FILL = PatternFill("solid", fgColor="DDEBF7")
_SUM_FILL = PatternFill("solid", fgColor="D9D9D9")
_HILITE = PatternFill("solid", fgColor="FFF2CC")
_CENTER = Alignment(horizontal="center", vertical="center")
_LEFT = Alignment(horizontal="left", vertical="center")
_RIGHT = Alignment(horizontal="right", vertical="center")
_BOLD = Font(bold=True)


def _cell(ws, r, c, val, *, fill=None, bold=False, align=_CENTER, border=True):
    cell = ws.cell(row=r, column=c, value=val)
    if fill:
        cell.fill = fill
    if bold:
        cell.font = _BOLD
    cell.alignment = align
    if border:
        cell.border = _BORDER
    return cell


def _year_table(ws, base_row, title_rows: dict, head_label: str):
    """연도별(부여/사용/수당) 2열 표를 좌/우 번갈아 배치. Returns 마지막 행."""
    last = base_row
    for yi, (fy, items) in enumerate(sorted(title_rows.items(), reverse=True)):
        c = 1 if yi % 2 == 0 else 4
        base = base_row + (yi // 2) * 14
        _cell(ws, base, c, f"{fy}년", fill=_HEAD_FILL, bold=True)
        _cell(ws, base, c + 1, head_label, fill=_HEAD_FILL, bold=True)
        rr = base + 1
        total = 0.0
        for it in items:
            _cell(ws, rr, c, it["label"], align=_LEFT)
            _cell(ws, rr, c + 1, it["days"])
            total += it["days"]
            rr += 1
        _cell(ws, rr, c, "합계", fill=_SUM_FILL, bold=True)
        _cell(ws, rr, c + 1, round(total, 1), fill=_SUM_FILL, bold=True)
        last = max(last, rr)
    return last


def _usage_table_dated(ws, base_row, usage_by_year: dict) -> int:
    """사용 내역을 연도별로 [구분 | 날짜·기간 | 사용일수] 3열 표로(위→아래) 렌더. Returns 마지막 행."""
    rr = base_row
    for fy, items in sorted(usage_by_year.items(), reverse=True):
        _cell(ws, rr, 1, f"{fy}년 · 휴가구분", fill=_HEAD_FILL, bold=True)
        _cell(ws, rr, 2, "휴가기간", fill=_HEAD_FILL, bold=True)
        _cell(ws, rr, 3, "사용일수", fill=_HEAD_FILL, bold=True)
        rr += 1
        total = 0.0
        for it in items:
            _cell(ws, rr, 1, it["label"], align=_LEFT)
            _cell(ws, rr, 2, it.get("date", ""), align=_LEFT)
            _cell(ws, rr, 3, it["days"])
            total += it["days"]
            rr += 1
        _cell(ws, rr, 1, "합계", fill=_SUM_FILL, bold=True)
        _cell(ws, rr, 2, "", fill=_SUM_FILL)
        _cell(ws, rr, 3, round(total, 1), fill=_SUM_FILL, bold=True)
        rr += 2
    return rr - 2


def build_settlement_xlsx(user, st: dict, usage_by_year: dict, breakdown: list, allowance_by_year: dict = None, adjust_by_year: dict = None) -> BytesIO:
    allowance_by_year = allowance_by_year or {}
    adjust_by_year = adjust_by_year or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "연차정산"
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 11
    ws.column_dimensions["D"].width = 24
    ws.column_dimensions["E"].width = 14

    # 제목
    _cell(ws, 1, 1, f"연차 정산 — {user.name}", bold=True, align=_LEFT, border=False)
    ws.cell(row=1, column=1).font = Font(bold=True, size=13)
    # 입사/퇴사
    _cell(ws, 2, 1, "입사일", fill=_HILITE, bold=True)
    _cell(ws, 2, 2, st.get("hire_date") or "-")
    _cell(ws, 3, 1, "퇴사일", fill=_HILITE, bold=True)
    _cell(ws, 3, 2, st.get("asof") or "-")

    # ── 사용 내역(연도별) ──
    r0 = 5
    _cell(ws, r0, 1, "■ 휴가 사용 내역(연도별 · 날짜 포함)", bold=True, align=_LEFT, border=False)
    if usage_by_year:
        end_used = _usage_table_dated(ws, r0 + 1, usage_by_year)
    else:
        _cell(ws, r0 + 1, 1, "사용 내역 없음", align=_LEFT, border=False)
        end_used = r0 + 1

    # ── 발생 내역(입사일 기준) ──
    r1 = end_used + 2
    _cell(ws, r1, 1, "■ 휴가 발생 내역(입사일 기준·근로기준법)", bold=True, align=_LEFT, border=False)
    _cell(ws, r1 + 1, 1, "휴가 발생일", fill=_HEAD_FILL, bold=True)
    _cell(ws, r1 + 1, 2, "휴가일수", fill=_HEAD_FILL, bold=True)
    rr = r1 + 2
    btotal = 0.0
    for row in breakdown:
        _cell(ws, rr, 1, row["desc"], align=_LEFT)
        _cell(ws, rr, 2, row["days"])
        btotal += row["days"]
        rr += 1
    _cell(ws, rr, 1, "합계", fill=_SUM_FILL, bold=True)
    _cell(ws, rr, 2, round(btotal, 1), fill=_SUM_FILL, bold=True)

    # ── 연차수당 지급 내역(연도별·일수) ──
    r1b = rr + 2
    _cell(ws, r1b, 1, "■ 연차수당 지급 내역(연도별·일수)", bold=True, align=_LEFT, border=False)
    if allowance_by_year:
        end_allow = _year_table(ws, r1b + 1, allowance_by_year, "지급일수")
    else:
        _cell(ws, r1b + 1, 1, "연차수당 지급 내역 없음", align=_LEFT, border=False)
        end_allow = r1b + 1

    # ── 수동 조정 내역(연도별, ±부호 유지) ──
    r1c = end_allow + 2
    _cell(ws, r1c, 1, "■ 수동 조정 내역(도입 초기값/관리자 가감)", bold=True, align=_LEFT, border=False)
    if adjust_by_year:
        end_adjust = _year_table(ws, r1c + 1, adjust_by_year, "조정(±)")
    else:
        _cell(ws, r1c + 1, 1, "수동 조정 내역 없음", align=_LEFT, border=False)
        end_adjust = r1c + 1

    # ── 정산 요약 ──
    r2 = end_adjust + 2
    legal = st.get("legal_entitlement") or 0
    adjust = st.get("adjust") or 0
    used = st.get("used") or 0
    paid = st.get("allowance_paid") or 0
    remain = st.get("unsettled_days")
    if remain is None:
        remain = round(legal + adjust - used - paid, 1)
    _cell(ws, r2, 1, "■ 정산 요약", bold=True, align=_LEFT, border=False)
    _cell(ws, r2 + 1, 1, "총 휴가 발생일(법정)", bold=True)
    _cell(ws, r2 + 1, 2, legal)
    _cell(ws, r2 + 2, 1, "수동 조정(±)", bold=True)
    _cell(ws, r2 + 2, 2, adjust)
    _cell(ws, r2 + 3, 1, "총 휴가 사용일", bold=True)
    _cell(ws, r2 + 3, 2, used)
    _cell(ws, r2 + 4, 1, "연차수당 기지급(일)", bold=True)
    _cell(ws, r2 + 4, 2, paid)
    _cell(ws, r2 + 5, 1, "잔여(미정산) 휴가일수", fill=_HILITE, bold=True)
    _cell(ws, r2 + 5, 2, remain, fill=_HILITE, bold=True)
    _cell(ws, r2 + 6, 1, "※ 잔여 = 발생(법정) + 수동조정 − 사용 − 연차수당 기지급. 금액은 임금 미보유로 미산출(잔여일수 × 통상임금으로 별도 계산).", align=_LEFT, border=False)

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out
