import psycopg2, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = psycopg2.connect('postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8')
cur = conn.cursor()

# ID 확인
cur.execute("SELECT id, partner_code, partner_name FROM business_partner WHERE partner_code IN ('DT','DTHK') ORDER BY partner_code")
for r in cur.fetchall():
    print(f"  id={r[0]} | {r[1]} | {r[2]}")

cur.execute("SELECT id FROM business_partner WHERE partner_code = 'DT'")
dt_id = cur.fetchone()[0]
cur.execute("SELECT id FROM business_partner WHERE partner_code = 'DTHK'")
dthk_id = cur.fetchone()[0]
print(f"\nDT id={dt_id} -> DTHK id={dthk_id}")

# DT 연결 데이터 이관
tables = [
    ("sales_document", "customer_id"),
    ("sales_activity", "customer_id"),
    ("production_request", "customer_id"),
    ("work_order", "customer_id"),
    ("purchase_order", "supplier_id"),
    ("business_partner_contact", "partner_id"),
    ("partner_note", "partner_id"),
    ("partner_balance_transaction", "partner_id"),
]

for table, col in tables:
    cur.execute(f"UPDATE {table} SET {col} = %s WHERE {col} = %s", (dthk_id, dt_id))
    if cur.rowcount > 0:
        print(f"  {table}.{col}: {cur.rowcount}건 이관")

# sales_activity.customer_name도 업데이트
cur.execute("UPDATE sales_activity SET customer_name = 'Drive Technology Development Studio Limited.' WHERE customer_id = %s", (dthk_id,))
if cur.rowcount > 0:
    print(f"  sales_activity.customer_name: {cur.rowcount}건 업데이트")

# DT 삭제
cur.execute("DELETE FROM business_partner WHERE id = %s", (dt_id,))
print(f"\nDT(id={dt_id}) 삭제: {cur.rowcount}건")

conn.commit()

# 검증
cur.execute("""SELECT count(*) FROM sales_document WHERE customer_id = %s""", (dthk_id,))
print(f"\nDTHK 문서: {cur.fetchone()[0]}건")
cur.execute("SELECT partner_code, partner_name FROM business_partner WHERE partner_code IN ('DT','DTHK')")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]}")

conn.close()
print("\n완료!")
