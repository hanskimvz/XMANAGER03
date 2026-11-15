import psycopg2, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = psycopg2.connect('postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8')
cur = conn.cursor()

# is_latest 분포
cur.execute("""SELECT document_type, is_latest, count(*), coalesce(sum(total_amount),0)
FROM sales_document GROUP BY document_type, is_latest ORDER BY document_type, is_latest""")
print("=== is_latest 분포 ===")
for r in cur.fetchall():
    print(f"  {r[0]:12s} latest={r[1]} -> {r[2]}건, ${float(r[3]):,.0f}")

# 일괄 입력 데이터는 전부 is_latest=true, version=1
print()
cur.execute("""SELECT document_type, version, count(*) FROM sales_document
GROUP BY document_type, version ORDER BY document_type, version""")
print("=== 버전 분포 ===")
for r in cur.fetchall():
    print(f"  {r[0]:12s} v{r[1]} -> {r[2]}건")

# 문제: 같은 거래의 PI가 여러건(예: PI-HT260120, PI-HT260120-REV)인 경우
# 둘 다 is_latest=true이므로 매출에 중복 집계됨
print()
cur.execute("""SELECT document_number, total_amount FROM sales_document
WHERE document_type='PI' AND is_latest=true
AND (document_number LIKE '%%.REV%%' OR document_number LIKE '%%.Rev%%' OR document_number LIKE '%%rev%%')
ORDER BY document_number""")
revs = cur.fetchall()
print(f"=== REV 포함 PI (중복 가능성) ===")
for r in revs:
    print(f"  {r[0]}: ${float(r[1]):,.0f}")

conn.close()
