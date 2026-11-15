"""
해외영업 주문/수금/출고 현황의 선적일자를 CI에 매핑
"""
import psycopg2, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from openpyxl import load_workbook
from datetime import date, datetime

EXCEL_PATH = 'c:/X-MANAGER_R0.1/docs/2026 해외영업 주문 _ 수금 _ 출고 현황.xlsx'
DB_URL = 'postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8'

wb = load_workbook(EXCEL_PATH, data_only=True)
ws = wb.active

def parse_date(val):
    if isinstance(val, date): return val
    if isinstance(val, datetime): return val.date()
    if val:
        s = str(val).strip()
        try: return date.fromisoformat(s[:10])
        except: pass
    return None

# 엑셀에서 CI번호 → 선적일자 매핑 추출
ci_ship_map = {}
for r in range(5, ws.max_row + 1):
    ci = ws.cell(row=r, column=18).value  # R: CI
    ship = ws.cell(row=r, column=19).value  # S: 선적일자
    if ci and str(ci).strip():
        ci_str = str(ci).strip()
        ship_date = parse_date(ship)
        if ship_date:
            ci_ship_map[ci_str] = ship_date

print(f"엑셀 CI-선적일자 매핑: {len(ci_ship_map)}건")

# DB 업데이트
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# 현재 CI shipment_date 상태
cur.execute("SELECT count(*) FROM sales_document WHERE document_type='CI' AND shipment_date IS NOT NULL")
has_date = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM sales_document WHERE document_type='CI' AND shipment_date IS NULL")
no_date = cur.fetchone()[0]
print(f"\n현재 CI: 선적일자 있음={has_date}건, 없음={no_date}건")

# 매핑 실행
updated = 0
not_found = []
for ci_num, ship_date in ci_ship_map.items():
    cur.execute("UPDATE sales_document SET shipment_date = %s WHERE document_number = %s AND document_type = 'CI'",
        (ship_date, ci_num))
    if cur.rowcount > 0:
        updated += 1
    else:
        not_found.append(ci_num)

conn.commit()

print(f"\n매핑 결과: {updated}건 업데이트")
if not_found:
    print(f"DB에 없는 CI: {len(not_found)}건")
    for c in not_found[:10]:
        print(f"  {c}")

# 최종 확인
cur.execute("SELECT count(*) FROM sales_document WHERE document_type='CI' AND shipment_date IS NOT NULL")
has_date = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM sales_document WHERE document_type='CI' AND shipment_date IS NULL")
no_date = cur.fetchone()[0]
print(f"\n최종 CI: 선적일자 있음={has_date}건 (출고완료), 없음={no_date}건 (미출고)")

conn.close()
