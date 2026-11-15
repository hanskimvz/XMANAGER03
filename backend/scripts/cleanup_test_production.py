r"""테스트용 생산관리 데이터 일괄 삭제 (생산요청 + 작업지시서)

생산요청 번호 체계를 26-NNN으로 전환하면서 기존 테스트 데이터를 정리합니다.

삭제 대상:
  - production_request (+ production_request_item: ondelete CASCADE)
  - work_order (+ work_order_item / work_order_item_issue / work_order_product / work_order_task: CASCADE)

삭제 순서 (FK 충돌 방지):
  1. work_order.production_request_id NULL 처리 (WO ↔ PR 교차참조 해제)
  2. production_request_item.work_order_id NULL 처리
  3. DELETE production_request  (production_request_item CASCADE)
  4. DELETE work_order          (하위 전부 CASCADE)

전체를 단일 트랜잭션으로 실행 — 실패 시 자동 롤백.

⚠️ 되돌릴 수 없음. 실행 전 반드시 DB 백업.

실행:
  cd backend
  set APP_ENV=production            # 또는 development (.env.* 의 DATABASE_URL 사용)
  python scripts\cleanup_test_production.py
  python scripts\cleanup_test_production.py --yes   # 확인 프롬프트 생략
"""

import io
import os
import sys

# backend/ 를 import path에 추가 (app.core.config 사용 위함)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 콘솔 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg2  # noqa: E402

from app.core.config import settings  # noqa: E402


def main() -> None:
    auto_yes = "--yes" in sys.argv

    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("SELECT count(*) FROM production_request")
        pr_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM work_order")
        wo_count = cur.fetchone()[0]

        print("=" * 50)
        print("테스트 생산관리 데이터 삭제")
        print("=" * 50)
        print(f"  DB                              : {settings.DATABASE_URL.rsplit('/', 1)[-1].split('?')[0]}")
        print(f"  생산요청 (production_request)   : {pr_count}건")
        print(f"  작업지시서 (work_order)         : {wo_count}건")
        print("  (하위 항목/이슈/태스크/제품은 CASCADE로 함께 삭제)")
        print()

        if pr_count == 0 and wo_count == 0:
            print("삭제할 데이터가 없습니다.")
            conn.rollback()
            return

        if not auto_yes:
            ans = input("정말 삭제하시겠습니까? 'DELETE' 입력 시 진행: ").strip()
            if ans != "DELETE":
                print("취소되었습니다.")
                conn.rollback()
                return

        # 1) 교차참조 해제
        cur.execute(
            "UPDATE work_order SET production_request_id = NULL "
            "WHERE production_request_id IS NOT NULL"
        )
        cur.execute(
            "UPDATE production_request_item SET work_order_id = NULL "
            "WHERE work_order_id IS NOT NULL"
        )

        # 2) production_request 삭제 (items cascade)
        cur.execute("DELETE FROM production_request")
        deleted_pr = cur.rowcount

        # 3) work_order 삭제 (하위 cascade)
        cur.execute("DELETE FROM work_order")
        deleted_wo = cur.rowcount

        conn.commit()

        # 결과 확인
        cur.execute("SELECT count(*) FROM production_request")
        remain_pr = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM work_order")
        remain_wo = cur.fetchone()[0]

        print()
        print(f"삭제 완료: 생산요청 {deleted_pr}건, 작업지시서 {deleted_wo}건")
        print(f"  남은 생산요청  : {remain_pr}건")
        print(f"  남은 작업지시서: {remain_wo}건")
        print()
        print("백엔드 재시작 후 새 생산요청부터 '26-099'로 부여됩니다.")

    except Exception as exc:
        conn.rollback()
        print()
        print(f"[실패 — 롤백됨] {type(exc).__name__}: {exc}")
        print("FK 충돌로 막혔다면, 위 메시지의 테이블명을 알려주세요. 스크립트를 조정하겠습니다.")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
