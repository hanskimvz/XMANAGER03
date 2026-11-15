import psycopg2, sys, io
from datetime import date
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = psycopg2.connect('postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8')
cur = conn.cursor()

# CI-BI260303 → 선적일자 2026-02-06으로 수정
cur.execute("UPDATE sales_document SET shipment_date = %s WHERE document_number = 'CI-BI260303'", (date(2026, 2, 6),))
print(f'CI-BI260303 선적일자 -> 2026-02-06: {cur.rowcount}건')

conn.commit()

# 전체 CI 출고 현황
cur.execute("SELECT document_number, shipment_date FROM sales_document WHERE document_type='CI' AND is_latest=true ORDER BY document_number")
shipped = 0
unshipped = 0
for r in cur.fetchall():
    if r[1]:
        shipped += 1
    else:
        unshipped += 1
        print(f'  미출고: {r[0]}')

print(f'\n출고완료: {shipped}건, 미출고: {unshipped}건')
conn.close()
