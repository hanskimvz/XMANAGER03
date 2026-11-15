r"""Q-TEMPLATE.xlsx 의 '키워드_디스크립션' 시트를 product_description_code 테이블로 동기화.

코드별로 segment_type을 자동 분류 후 upsert:
  - PSD/RJ*/RQ*/PRD/RRD          → TYPE
  - B / S                         → MATERIAL
  - O2~OG / 02~0G                 → CHANNEL
  - S1 / M1~M4 / S09 / S20        → FIBER
  - D##                           → CABLE
  - HXB## / HXB##AS               → PRODUCT
  - SA / SC / LC / ST             → CONNECTOR
  - 그 외                         → MISC (수동 분류 필요시 알림)

신규 코드는 INSERT, 기존 코드는 description_en 업데이트 (description_ko/사용자 수정 보존).
드라이런(--dry-run)으로 변경 미리보기 가능.

실행:
  cd backend
  set APP_ENV=production
  python scripts\sync_description_codes_from_excel.py --dry-run   # 미리보기
  python scripts\sync_description_codes_from_excel.py             # 실제 적용
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from openpyxl import load_workbook  # noqa: E402
import psycopg2  # noqa: E402

from app.core.config import settings  # noqa: E402


EXCEL_PATH = r"c:\X-MANAGER_R0.1\docs\samples\sales-export\Q-TEMPLATE.xlsx"
SHEET_NAME = "키워드_디스크립션"


def classify(code: str) -> str:
    """코드 → segment_type 매핑."""
    c = code.upper().strip()
    if re.match(r"^HXB\d+(AS)?$", c):
        return "PRODUCT"
    if c in ("PSD", "RJS", "RJN", "RJL", "RQS", "RQN", "RQL", "PRD", "RRD"):
        return "TYPE"
    if c in ("B", "S"):
        return "MATERIAL"
    if re.match(r"^[O0][2-9A-G]$", c):
        return "CHANNEL"
    if c in ("S1", "M1", "M2", "M3", "M4", "S09", "S20"):
        return "FIBER"
    if re.match(r"^D\d{2,3}$", c):
        return "CABLE"
    if c in ("SA", "SC", "LC", "ST"):
        return "CONNECTOR"
    return "MISC"


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    # Excel 로드
    wb = load_workbook(EXCEL_PATH, data_only=False)
    if SHEET_NAME not in wb.sheetnames:
        print(f"[실패] '{SHEET_NAME}' 시트를 찾을 수 없습니다.")
        sys.exit(1)
    ws = wb[SHEET_NAME]

    # 표 데이터 수집
    excel_rows = []
    for r in range(1, ws.max_row + 1):
        code = ws.cell(row=r, column=1).value
        desc = ws.cell(row=r, column=2).value
        if not code:
            continue
        code_str = str(code).strip()
        # Excel 셀의 선·후행 공백은 시각 들여쓰기일 뿐 의미 없음 — strip
        desc_str = str(desc).strip() if desc else ""
        if not code_str:
            continue
        excel_rows.append((code_str, desc_str))

    print("=" * 60)
    print(f"Excel '{SHEET_NAME}' — {len(excel_rows)}건")
    print(f"DRY RUN: {dry_run}")
    print(f"DB     : {settings.DATABASE_URL.rsplit('/', 1)[-1].split('?')[0]}")
    print("=" * 60)

    # DB 연결
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    try:
        # 기존 코드 맵 (대문자 키)
        cur.execute("SELECT id, code, description_en FROM product_description_code")
        existing = {row[1].upper(): (row[0], row[2]) for row in cur.fetchall()}

        to_insert = []
        to_update = []  # (id, code, old_desc, new_desc, segment_type)
        unchanged = []
        misc = []  # MISC 분류 — 사용자 검토 필요

        for code, desc in excel_rows:
            stype = classify(code)
            if stype == "MISC":
                misc.append(code)
            key = code.upper()
            if key in existing:
                old_id, old_desc = existing[key]
                old_norm = (old_desc or "").strip()
                if old_norm != desc:
                    to_update.append((old_id, code, old_desc or "", desc, stype))
                else:
                    unchanged.append(code)
            else:
                to_insert.append((code, desc, stype))

        # 리포트
        print(f"\n[INSERT 예정 — {len(to_insert)}건]")
        for code, desc, stype in to_insert:
            print(f"  + {stype:10s} {code:10s} | {desc[:60]}")

        print(f"\n[UPDATE 예정 — {len(to_update)}건]")
        for _id, code, old, new, stype in to_update:
            print(f"  ~ {stype:10s} {code:10s}")
            print(f"     old: {old[:80]!r}")
            print(f"     new: {new[:80]!r}")

        print(f"\n[UNCHANGED — {len(unchanged)}건]")
        if unchanged:
            print(f"  {', '.join(unchanged)}")

        if misc:
            print(f"\n[⚠ MISC 분류 — 자동 분류 실패 — {len(misc)}건]")
            print(f"  {misc} → segment_type='MISC'로 등록됨. 추후 정확한 분류로 UPDATE 필요")

        if dry_run:
            print("\n[DRY RUN] 실제 변경 안 함. --dry-run 빼고 다시 실행하면 적용.")
            return

        if not to_insert and not to_update:
            print("\n변경할 내용이 없습니다.")
            return

        # 실제 적용
        # INSERT
        for code, desc, stype in to_insert:
            cur.execute(
                """INSERT INTO product_description_code
                   (segment_type, code, description_en, description_ko, sort_order, is_active, created_at)
                   VALUES (%s, %s, %s, NULL, 0, TRUE, now())""",
                (stype, code, desc),
            )
        # UPDATE
        for _id, code, old, new, stype in to_update:
            cur.execute(
                """UPDATE product_description_code
                   SET description_en = %s, updated_at = now()
                   WHERE id = %s""",
                (new, _id),
            )

        conn.commit()
        print(f"\n적용 완료: INSERT {len(to_insert)}건 / UPDATE {len(to_update)}건")
        print("백엔드 재시작 또는 캐시 갱신 후 효과 반영됩니다.")

    except Exception as exc:
        conn.rollback()
        print(f"\n[실패 — 롤백됨] {type(exc).__name__}: {exc}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
