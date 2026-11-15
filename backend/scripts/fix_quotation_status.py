import psycopg2, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = psycopg2.connect('postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8')
cur = conn.cursor()

cur.execute("""
    SELECT DISTINCT s.id FROM sales_document s
    JOIN sales_document_link l ON l.source_id = s.id
    JOIN sales_document t ON l.target_id = t.id AND t.document_type = 'PI'
    WHERE s.document_type = 'QUOTATION'
""")
linked = set(r[0] for r in cur.fetchall())
print(f"PI 연결된 견적서: {len(linked)}건")

if linked:
    cur.execute("UPDATE sales_document SET status = 'SENT' WHERE document_type = 'QUOTATION' AND id NOT IN %s",
        (tuple(linked),))
else:
    cur.execute("UPDATE sales_document SET status = 'SENT' WHERE document_type = 'QUOTATION'")
print(f"SENT 변경: {cur.rowcount}건")

conn.commit()

cur.execute("SELECT status, count(*) FROM sales_document WHERE document_type='QUOTATION' GROUP BY status")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}건")

conn.close()
