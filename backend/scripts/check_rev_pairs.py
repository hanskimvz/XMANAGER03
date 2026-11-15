import psycopg2, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = psycopg2.connect('postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8')
cur = conn.cursor()

# REV 문서의 원본이 있는지 확인
cur.execute("""SELECT document_number, document_type, total_amount FROM sales_document
WHERE is_latest=true AND (document_number LIKE '%%.REV%%' OR document_number LIKE '%%.Rev%%')
ORDER BY document_number""")
revs = cur.fetchall()

print("=== REV 문서 vs 원본 매칭 ===")
for rev_num, dt, amt in revs:
    # 원본 번호 추정 (.REV, .Rev 제거)
    base = rev_num.replace('.REV', '').replace('.Rev', '').replace('.rev', '')
    cur.execute("SELECT document_number, total_amount FROM sales_document WHERE document_number = %s", (base,))
    orig = cur.fetchone()
    if orig:
        print(f"  원본: {orig[0]} (${float(orig[1]):,.0f}) -> REV: {rev_num} (${float(amt):,.0f}) [중복!]")
    else:
        print(f"  REV: {rev_num} (${float(amt):,.0f}) -> 원본 {base} 없음 [단독]")

conn.close()
