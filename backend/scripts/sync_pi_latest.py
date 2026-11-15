"""
해외영업 주문/수금/출고 현황 파일의 PI 칼럼 기준으로
is_latest 플래그를 정리합니다.
"""
import psycopg2, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from openpyxl import load_workbook

EXCEL_PATH = 'c:/X-MANAGER_R0.1/docs/2026 해외영업 주문 _ 수금 _ 출고 현황.xlsx'
DB_URL = 'postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8'

# 1. 엑셀에서 실제 PI 번호 추출
wb = load_workbook(EXCEL_PATH, data_only=True)
ws = wb.active

real_pi_numbers = set()
for r in range(5, ws.max_row + 1):
    pi = ws.cell(row=r, column=8).value  # H열: PI
    if pi and str(pi).strip() and str(pi).strip() != 'None':
        real_pi_numbers.add(str(pi).strip())

print(f"=== 엑셀 PI 목록: {len(real_pi_numbers)}건 ===")

# 2. DB의 모든 PI와 비교
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("SELECT id, document_number, is_latest, total_amount FROM sales_document WHERE document_type='PI' ORDER BY document_number")
all_pis = cur.fetchall()

in_excel = []      # 엑셀에 있음 = 최종본
not_in_excel = []   # 엑셀에 없음 = 이전 버전

for pid, doc_num, is_latest, amount in all_pis:
    if doc_num in real_pi_numbers:
        in_excel.append((pid, doc_num, is_latest, amount))
    else:
        not_in_excel.append((pid, doc_num, is_latest, amount))

print(f"\n=== 매칭 결과 ===")
print(f"  엑셀에 있음 (최종본): {len(in_excel)}건")
print(f"  엑셀에 없음 (이전본): {len(not_in_excel)}건")

# 3. 현재 is_latest 상태 확인
wrong_latest_true = [p for p in not_in_excel if p[2] == True]
wrong_latest_false = [p for p in in_excel if p[2] == False]

print(f"\n=== 수정 필요 ===")
print(f"  is_latest=true인데 이전본 (false로 변경 필요): {len(wrong_latest_true)}건")
for p in wrong_latest_true:
    print(f"    {p[1]} (${float(p[3]):,.0f})")

print(f"  is_latest=false인데 최종본 (true로 변경 필요): {len(wrong_latest_false)}건")
for p in wrong_latest_false:
    print(f"    {p[1]} (${float(p[3]):,.0f})")

# 4. 수정 실행
if wrong_latest_true:
    for pid, doc_num, _, _ in wrong_latest_true:
        cur.execute("UPDATE sales_document SET is_latest = false WHERE id = %s", (pid,))
    print(f"\n  -> {len(wrong_latest_true)}건 is_latest=false로 변경")

if wrong_latest_false:
    for pid, doc_num, _, _ in wrong_latest_false:
        cur.execute("UPDATE sales_document SET is_latest = true WHERE id = %s", (pid,))
    print(f"  -> {len(wrong_latest_false)}건 is_latest=true로 변경")

conn.commit()

# 5. 최종 확인
cur.execute("""SELECT is_latest, count(*), coalesce(sum(total_amount),0)
FROM sales_document WHERE document_type='PI' GROUP BY is_latest""")
print(f"\n=== 최종 PI 상태 ===")
for r in cur.fetchall():
    print(f"  is_latest={r[0]}: {r[1]}건, ${float(r[2]):,.0f}")

conn.close()
print("\n완료!")
