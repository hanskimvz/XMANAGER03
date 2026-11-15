r"""product_description_code 테이블 현황 조회.

Excel 매핑 표(Q-TEMPLATE.xlsx 키워드_디스크립션)와 비교하기 전 현황 파악용.
읽기 전용 — DB 변경 없음.

실행:
  cd backend
  set APP_ENV=production
  python scripts\inspect_description_codes.py
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg2  # noqa: E402

from app.core.config import settings  # noqa: E402


def main() -> None:
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("SELECT count(*) FROM product_description_code")
        total = cur.fetchone()[0]
        print("=" * 60)
        print(f"product_description_code 테이블 — 총 {total}건")
        print("=" * 60)

        # segment_type별 분포
        cur.execute("""
            SELECT segment_type, count(*)
            FROM product_description_code
            GROUP BY segment_type
            ORDER BY segment_type
        """)
        print("\n[segment_type별 건수]")
        for st, cnt in cur.fetchall():
            print(f"  {st:20s} : {cnt}")

        # 전체 코드 목록
        cur.execute("""
            SELECT segment_type, code, description_en, description_ko, is_active
            FROM product_description_code
            ORDER BY segment_type, sort_order, code
        """)
        rows = cur.fetchall()
        print(f"\n[전체 등록 코드 ({len(rows)}건)]")
        prev_type = None
        for st, code, desc_en, desc_ko, active in rows:
            if st != prev_type:
                print(f"\n--- {st} ---")
                prev_type = st
            flag = "" if active else " [비활성]"
            desc_show = (desc_en or "")[:60]
            ko_show = f" / {(desc_ko or '')[:30]}" if desc_ko else ""
            print(f"  {code:10s} | {desc_show}{ko_show}{flag}")

        # Excel 표의 핵심 코드 매핑 확인 (HXB / AS / SA-SC-LC-ST / PRD/RRD)
        print("\n" + "=" * 60)
        print("[핵심 코드 등록 여부 점검 — Excel 표 기준]")
        print("=" * 60)
        candidates = [
            "HXB11", "HXB13", "HXB15", "HXB17",
            "HXB11AS", "HXB13AS", "HXB15AS", "HXB17AS",
            "SA", "SC", "LC", "ST",
            "PRD", "RRD",
            "PSD", "RJS", "RJN", "RJL", "RQS", "RQN", "RQL",
            "B", "S",
            "O2", "O4", "O6", "O8", "OA", "OC", "OE", "OG",
            "02", "04", "06", "08", "0A", "0C", "0E", "0G",
            "S1", "M1", "M2", "M3", "M4", "S09", "S20",
            "D45", "D55", "D65", "D75",
        ]
        cur.execute(
            "SELECT upper(code) FROM product_description_code WHERE is_active = TRUE"
        )
        registered = {r[0] for r in cur.fetchall()}
        missing = []
        for c in candidates:
            mark = "OK " if c.upper() in registered else "❌ "
            if c.upper() not in registered:
                missing.append(c)
            print(f"  [{mark}] {c}")
        print(f"\n누락: {len(missing)}건 — {missing}")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
