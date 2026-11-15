"""
해외영업 주문/수금/출고 현황 vs X-Manager DB 비교
"""
import psycopg2, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from openpyxl import load_workbook
from decimal import Decimal

EXCEL_PATH = 'c:/X-MANAGER_R0.1/docs/2026 해외영업 주문 _ 수금 _ 출고 현황.xlsx'
DB_URL = 'postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8'

wb = load_workbook(EXCEL_PATH, data_only=True)
ws = wb.active

# 엑셀 데이터 추출
excel_pis = {}  # PI번호 → 금액
excel_cis = {}  # CI번호 → 금액
excel_total = Decimal('0')

for r in range(5, ws.max_row + 1):
    seq = ws.cell(row=r, column=2).value
    if not seq:
        continue
    pi = ws.cell(row=r, column=8).value  # H: PI
    ci = ws.cell(row=r, column=18).value  # R: CI
    amount = ws.cell(row=r, column=11).value  # K: 총 주문 금액

    amt = Decimal(str(amount)) if amount else Decimal('0')
    excel_total += amt

    if pi and str(pi).strip():
        pi_str = str(pi).strip()
        if pi_str not in excel_pis:
            excel_pis[pi_str] = Decimal('0')
        excel_pis[pi_str] += amt

    if ci and str(ci).strip():
        ci_str = str(ci).strip()
        if ci_str not in excel_cis:
            excel_cis[ci_str] = Decimal('0')
        excel_cis[ci_str] += amt

print(f"=== 해외영업 현황 엑셀 ===")
print(f"  총 주문금액 합계: ${excel_total:,.2f}")
print(f"  PI 수: {len(excel_pis)}건")
print(f"  CI 수: {len(excel_cis)}건")

# DB 데이터
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("SELECT document_number, total_amount FROM sales_document WHERE document_type='PI' AND is_latest=true")
db_pis = {r[0]: r[1] for r in cur.fetchall()}

cur.execute("SELECT document_number, total_amount FROM sales_document WHERE document_type='CI' AND is_latest=true")
db_cis = {r[0]: r[1] for r in cur.fetchall()}

db_pi_total = sum(float(v) for v in db_pis.values())
db_ci_total = sum(float(v) for v in db_cis.values())

print(f"\n=== X-Manager DB ===")
print(f"  PI 최종본: {len(db_pis)}건, ${db_pi_total:,.2f}")
print(f"  CI 최종본: {len(db_cis)}건, ${db_ci_total:,.2f}")

# PI 비교
print(f"\n=== PI 비교 ===")
excel_pi_set = set(excel_pis.keys())
db_pi_set = set(db_pis.keys())

missing_in_db = excel_pi_set - db_pi_set
extra_in_db = db_pi_set - excel_pi_set

print(f"  엑셀에만 있음 (DB 미등록): {len(missing_in_db)}건")
for p in sorted(missing_in_db):
    print(f"    {p}: ${excel_pis[p]:,.2f}")

if extra_in_db:
    print(f"  DB에만 있음 (엑셀에 없음): {len(extra_in_db)}건")
    for p in sorted(extra_in_db)[:10]:
        print(f"    {p}: ${float(db_pis[p]):,.2f}")

# 금액 불일치
print(f"\n  금액 불일치:")
matched = excel_pi_set & db_pi_set
mismatch_count = 0
for p in sorted(matched):
    excel_amt = float(excel_pis[p])
    db_amt = float(db_pis[p])
    if abs(excel_amt - db_amt) > 0.01:
        print(f"    {p}: 엑셀 ${excel_amt:,.2f} vs DB ${db_amt:,.2f} (차이: ${excel_amt - db_amt:,.2f})")
        mismatch_count += 1
if mismatch_count == 0:
    print(f"    없음")

# CI 비교
print(f"\n=== CI 비교 ===")
excel_ci_set = set(excel_cis.keys())
db_ci_set = set(db_cis.keys())

missing_ci_in_db = excel_ci_set - db_ci_set
print(f"  엑셀에만 있음 (DB 미등록): {len(missing_ci_in_db)}건")
for c in sorted(missing_ci_in_db):
    print(f"    {c}: ${excel_cis[c]:,.2f}")

# 총액 차이
missing_pi_total = sum(float(excel_pis[p]) for p in missing_in_db)
missing_ci_total = sum(float(excel_cis[c]) for c in missing_ci_in_db)
print(f"\n=== 차이 요약 ===")
print(f"  엑셀 총 주문금액: ${excel_total:,.2f}")
print(f"  DB PI 최종본 합계: ${db_pi_total:,.2f}")
print(f"  DB CI 최종본 합계: ${db_ci_total:,.2f}")
print(f"  미등록 PI 금액: ${missing_pi_total:,.2f}")
print(f"  미등록 CI 금액: ${missing_ci_total:,.2f}")

conn.close()
