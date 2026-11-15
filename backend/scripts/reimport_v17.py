"""
v17 엑셀에서 Q/PI/CI 데이터 재입력
- IT(Inteldat) → AR(ARDyx) 자동 이관
- FC → FOCA 코드 매핑
- 17번 열 출고상태 → remarks에 저장
"""
import psycopg2, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from openpyxl import load_workbook
from decimal import Decimal
from datetime import date, datetime

EXCEL_PATH = 'c:/X-MANAGER_R0.1/docs/Q_PI_CI_데이터추출_검증및수정_v17_출고상태_20260422.xlsx'
DB_URL = 'postgresql://xmanager:xbeamtech@localhost:5432/xmanager?client_encoding=utf8'

# 코드 변환 매핑 (엑셀 → DB)
CODE_MAP = {
    'FC': 'FOCA',
    'IT': 'AR',  # Inteldat → ARDyx
}

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# ===== 1. 기존 데이터 삭제 =====
print('=== 1. 기존 데이터 삭제 ===')
cur.execute('DELETE FROM sales_document_link')
print(f'  연결: {cur.rowcount}건')
cur.execute('UPDATE production_request_item SET pi_document_id = NULL, pi_item_id = NULL WHERE pi_item_id IS NOT NULL')
print(f'  생산요청 참조 해제: {cur.rowcount}건')
cur.execute('DELETE FROM sales_document_item')
print(f'  품목: {cur.rowcount}건')
cur.execute('DELETE FROM sales_document')
print(f'  문서: {cur.rowcount}건')
conn.commit()

# ===== 2. 준비 =====
wb = load_workbook(EXCEL_PATH, data_only=True)
ws_doc = wb['문서']
ws_item = wb['품목']

cur.execute('SELECT partner_code, id FROM business_partner')
partner_map = {r[0]: r[1] for r in cur.fetchall()}

def parse_date(val):
    if isinstance(val, date): return val
    if isinstance(val, datetime): return val.date()
    if val:
        try: return date.fromisoformat(str(val).strip()[:10])
        except: pass
    return date.today()

def safe_decimal(val):
    if val is None: return Decimal('0')
    try: return Decimal(str(val).strip())
    except: return Decimal('0')

def safe_str(val, max_len=None):
    if val is None: return None
    s = str(val).strip()
    if not s or s == '-': return None
    if max_len: s = s[:max_len]
    return s

# ===== 3. 문서 등록 =====
print('\n=== 2. 문서 등록 ===')
doc_id_map = {}
type_count = {'QUOTATION': 0, 'PI': 0, 'CI': 0}
it_to_ar_count = 0

for r in range(2, ws_doc.max_row + 1):
    dt = safe_str(ws_doc.cell(row=r, column=1).value)
    dn = safe_str(ws_doc.cell(row=r, column=2).value)
    if not dt or not dn:
        continue

    dt = dt.upper()
    doc_date = parse_date(ws_doc.cell(row=r, column=3).value)
    cust_code = safe_str(ws_doc.cell(row=r, column=4).value)

    # 코드 변환
    original_code = cust_code
    if cust_code in CODE_MAP:
        cust_code = CODE_MAP[cust_code]
        if original_code == 'IT':
            it_to_ar_count += 1

    customer_id = partner_map.get(cust_code)
    currency = safe_str(ws_doc.cell(row=r, column=6).value) or 'USD'
    total_amount = safe_decimal(ws_doc.cell(row=r, column=7).value)
    po_number = safe_str(ws_doc.cell(row=r, column=10).value)
    payment_terms = safe_str(ws_doc.cell(row=r, column=11).value)
    delivery_terms = safe_str(ws_doc.cell(row=r, column=12).value)
    prepared_by = safe_str(ws_doc.cell(row=r, column=13).value)
    remarks = safe_str(ws_doc.cell(row=r, column=16).value)
    shipping_status = safe_str(ws_doc.cell(row=r, column=17).value)

    # 출고상태를 비고에 추가 저장
    if shipping_status:
        if remarks:
            remarks = f"{remarks} [출고:{shipping_status}]"
        else:
            remarks = f"[출고:{shipping_status}]"

    status = 'CONFIRMED'
    payment_status = 'PAID' if dt == 'PI' else None

    cur.execute("""
        INSERT INTO sales_document (
            document_type, document_number, document_date, customer_id,
            currency, total_amount, status, payment_status,
            customer_po_number, payment_terms, delivery_terms,
            prepared_by, remarks, version, is_latest, version_group
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,true,%s)
        RETURNING id
    """, (dt, dn, doc_date, customer_id, currency, total_amount,
          status, payment_status, po_number, payment_terms, delivery_terms,
          prepared_by, remarks, dn))

    doc_id = cur.fetchone()[0]
    doc_id_map[dn] = doc_id
    type_count[dt] = type_count.get(dt, 0) + 1

conn.commit()
print(f'  등록: {len(doc_id_map)}건')
for t, c in type_count.items():
    print(f'    {t}: {c}건')
print(f'  IT→AR 이관: {it_to_ar_count}건')

# ===== 4. 품목 등록 =====
print('\n=== 3. 품목 등록 ===')
item_count = 0
for r in range(2, ws_item.max_row + 1):
    ref = safe_str(ws_item.cell(row=r, column=1).value)
    if not ref:
        continue
    doc_id = doc_id_map.get(ref)
    if not doc_id:
        continue

    line_no = ws_item.cell(row=r, column=2).value or 1
    product_code = safe_str(ws_item.cell(row=r, column=3).value) or ''
    description = safe_str(ws_item.cell(row=r, column=4).value)
    quantity = safe_decimal(ws_item.cell(row=r, column=5).value) or Decimal('1')
    uom = safe_str(ws_item.cell(row=r, column=6).value) or 'EA'
    unit_price = safe_decimal(ws_item.cell(row=r, column=7).value)
    amount = safe_decimal(ws_item.cell(row=r, column=8).value)
    if amount == 0 and unit_price > 0:
        amount = quantity * unit_price
    item_currency = safe_str(ws_item.cell(row=r, column=9).value) or 'USD'
    line_remarks = safe_str(ws_item.cell(row=r, column=10).value)

    cur.execute("""
        INSERT INTO sales_document_item (
            document_id, line_no, product_code, description,
            quantity, uom, unit_price, amount, currency, line_remarks
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (doc_id, line_no, product_code, description,
          quantity, uom, unit_price, amount, item_currency, line_remarks))
    item_count += 1

conn.commit()
print(f'  등록: {item_count}건')

# ===== 5. 연결 관계 =====
print('\n=== 4. 연결 관계 ===')
doc_type_map = {}
for r in range(2, ws_doc.max_row + 1):
    dn = safe_str(ws_doc.cell(row=r, column=2).value)
    dt = safe_str(ws_doc.cell(row=r, column=1).value)
    if dn and dt:
        doc_type_map[dn] = dt.upper()

type_order = {'QUOTATION': 0, 'PI': 1, 'CI': 2}
link_count = 0
seen_links = set()

for r in range(2, ws_doc.max_row + 1):
    dn = safe_str(ws_doc.cell(row=r, column=2).value)
    sd = safe_str(ws_doc.cell(row=r, column=14).value)
    if not dn or not sd:
        continue

    my_type = doc_type_map.get(dn, '')
    my_order = type_order.get(my_type, -1)

    sources = [s.strip() for s in sd.split(',') if s.strip()]
    for src in sources:
        src_type = doc_type_map.get(src, '')
        src_order = type_order.get(src_type, -1)

        if src_order < my_order:
            source_dn, target_dn = src, dn
        elif src_order > my_order:
            source_dn, target_dn = dn, src
        else:
            continue

        link_key = (source_dn, target_dn)
        if link_key in seen_links:
            continue
        seen_links.add(link_key)

        source_id = doc_id_map.get(source_dn)
        target_id = doc_id_map.get(target_dn)
        if source_id and target_id:
            cur.execute('INSERT INTO sales_document_link (source_id, target_id) VALUES (%s, %s)',
                        (source_id, target_id))
            link_count += 1

# source_document_id 하위호환
for r in range(2, ws_doc.max_row + 1):
    dn = safe_str(ws_doc.cell(row=r, column=2).value)
    sd = safe_str(ws_doc.cell(row=r, column=14).value)
    if not dn or not sd:
        continue
    my_type = doc_type_map.get(dn, '')
    my_order = type_order.get(my_type, -1)
    sources = [s.strip() for s in sd.split(',') if s.strip()]
    for src in sources:
        src_type = doc_type_map.get(src, '')
        src_order = type_order.get(src_type, -1)
        if src_order < my_order:
            src_id = doc_id_map.get(src)
            doc_id = doc_id_map.get(dn)
            if src_id and doc_id:
                cur.execute('UPDATE sales_document SET source_document_id = %s WHERE id = %s AND source_document_id IS NULL',
                    (src_id, doc_id))
            break

conn.commit()
print(f'  등록: {link_count}건')

# ===== 6. 시퀀스 리셋 =====
cur.execute("SELECT setval('sales_document_id_seq', (SELECT COALESCE(MAX(id),0) FROM sales_document))")
cur.execute("SELECT setval('sales_document_item_id_seq', (SELECT COALESCE(MAX(id),0) FROM sales_document_item))")
cur.execute("SELECT setval('sales_document_link_id_seq', (SELECT COALESCE(MAX(id),0) FROM sales_document_link))")
conn.commit()

# ===== 7. 최종 확인 =====
print('\n=== 최종 결과 ===')
cur.execute('SELECT document_type, count(*) FROM sales_document GROUP BY document_type ORDER BY document_type')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}건')
cur.execute('SELECT count(*) FROM sales_document_item')
print(f'  품목: {cur.fetchone()[0]}건')
cur.execute('SELECT count(*) FROM sales_document_link')
print(f'  연결: {cur.fetchone()[0]}건')

# ARDyx 문서 확인
cur.execute("""SELECT count(*) FROM sales_document sd
JOIN business_partner bp ON sd.customer_id = bp.id WHERE bp.partner_code = 'AR'""")
print(f'  ARDyx(AR) 문서: {cur.fetchone()[0]}건')

conn.close()
print('\n완료!')
