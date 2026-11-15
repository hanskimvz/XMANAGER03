import psycopg2, sys, io
from datetime import date
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = psycopg2.connect('postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8')
cur = conn.cursor()

fixes = {
    'CI-IH260113': date(2026, 1, 14),
    'CI-IH260311': date(2026, 3, 12),
}

for ci, d in fixes.items():
    cur.execute('UPDATE sales_document SET shipment_date = %s WHERE document_number = %s', (d, ci))
    print(f'  {ci} -> {d}: {cur.rowcount}건')

conn.commit()

cur.execute("SELECT count(*) FROM sales_document WHERE document_type='CI' AND is_latest=true AND shipment_date IS NOT NULL")
shipped = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM sales_document WHERE document_type='CI' AND is_latest=true AND shipment_date IS NULL")
unshipped = cur.fetchone()[0]
print(f'\n최종: 출고완료={shipped}건, 미출고={unshipped}건')
conn.close()
