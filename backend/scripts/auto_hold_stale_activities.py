"""180일 미활동 영업 건 자동 보류 배치.

Windows 작업 스케줄러에서 매일 04:00 실행(run-auto-hold.bat 경유).
- 마지막 히스토리 로그(없으면 생성일)가 180일 이전인 IN_PROGRESS/WAITING 건 → ON_HOLD 전환
- 각 건 타임라인에 AUTO_HOLD 로그 기록. 자동 복귀 없음(수동).

직접 실행:
    backend\.venv\Scripts\python.exe backend\scripts\auto_hold_stale_activities.py
"""
import os
import sys
from datetime import datetime

os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("PGCLIENTENCODING", "UTF8")
# backend/ 를 import path 에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.services.sales_activity_service import SalesActivityService  # noqa: E402


def main() -> int:
    stamp = datetime.now().isoformat(timespec="seconds")
    db = SessionLocal()
    try:
        result = SalesActivityService(db).auto_hold_stale(days=180)
        ids = [h["id"] for h in result["held"]]
        print(f"[{stamp}] 자동보류 {result['held_count']}건 (cutoff={result['cutoff']}) ids={ids}")
        return 0
    except Exception:
        import traceback
        print(f"[{stamp}] 자동보류 실패")
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
