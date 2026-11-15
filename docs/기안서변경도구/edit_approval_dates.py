"""
전자결재 날짜 직접 수정 도구 (독립 실행 CLI)

⚠️ 이 도구는 approval_corrections(정정 이력)를 남기지 않고 날짜를 직접 변경한다.
   감사 추적이 사라지므로 출시 전 초기/이관 데이터 정리 용도로만 사용할 것.
   변경은 되돌릴 수 없다 — 실행 전 반드시 DB 백업.

대상 컬럼:
  approval_documents.drafted_at    (상신 시각)
  approval_documents.completed_at  (최종 승인/반려 시각)
  approval_documents.created_at     (생성 시각)
  approval_lines.acted_at          (각 결재자 처리 시각 = 도장 날짜)
  approval_actions.acted_at         (감사 이력 행위 시각)

입력 시간대: 기본 Asia/Seoul(KST). 내부적으로 UTC 로 변환해 저장한다.
기본은 미리보기(dry-run). 실제 반영은 --commit 플래그.

사용 예:
  # 1) 현재 날짜 확인 (문서번호 또는 id)
  python -m scripts.edit_approval_dates --doc AP-2026-0001
  python -m scripts.edit_approval_dates --id 42

  # 2) 미리보기 (아직 저장 안 함)
  python -m scripts.edit_approval_dates --doc AP-2026-0001 \
      --drafted "2026-03-15 09:30" --completed "2026-03-18 17:00" \
      --line 1="2026-03-15 10:00" --line 2="2026-03-18 16:30"

  # 3) 실제 반영
  python -m scripts.edit_approval_dates --doc AP-2026-0001 \
      --drafted "2026-03-15 09:30" --line 1="2026-03-15 10:00" --commit

  # 운영 DB 대상이면 APP_ENV 지정
  set APP_ENV=production && python -m scripts.edit_approval_dates --doc AP-2026-0001 ...
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:  # pragma: no cover
    ZoneInfo = None

# 같은 폴더(번들)를 import 경로에 추가 — 앱 패키지 비의존(다른 폴더에서도 동작)
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from approval_db import (  # noqa: E402
    ApprovalAction,
    ApprovalDocument,
    ApprovalLine,
    get_session,
)

DEFAULT_TZ = "Asia/Seoul"
# 허용 입력 포맷
_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")

# Windows 등 IANA tz DB(tzdata) 미설치 환경용 고정 오프셋 폴백.
# (KST/JST 등은 서머타임이 없어 고정 오프셋이 항상 정확)
_FIXED_OFFSETS = {"Asia/Seoul": 9, "Asia/Tokyo": 9, "UTC": 0, "Etc/UTC": 0}


def resolve_tz(tz_name: str):
    """tz 이름 → tzinfo. zoneinfo/tzdata 가 없으면 고정 오프셋으로 폴백(KST=UTC+9)."""
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return timezone(timedelta(hours=_FIXED_OFFSETS.get(tz_name, 0)))


def parse_local_to_utc(raw: str, tz_name: str) -> datetime:
    """'YYYY-MM-DD[ HH:MM[:SS]]' 지역시간 문자열 → tz-aware UTC datetime."""
    raw = raw.strip()
    dt = None
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        raise ValueError(
            f"날짜 형식을 해석할 수 없습니다: '{raw}' "
            f"(허용: YYYY-MM-DD / YYYY-MM-DD HH:MM / YYYY-MM-DD HH:MM:SS)"
        )
    local = dt.replace(tzinfo=resolve_tz(tz_name))
    return local.astimezone(timezone.utc)


def fmt(dt, tz_name: str) -> str:
    """저장된 UTC datetime 을 지역시간으로 보기 좋게 출력."""
    if dt is None:
        return "(없음)"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(resolve_tz(tz_name))
    return local.strftime("%Y-%m-%d %H:%M:%S %Z")


def parse_step_arg(values, label: str):
    """--line/--action 의 'KEY=날짜' 목록을 {int: raw} 로 파싱."""
    out = {}
    for item in values or []:
        if "=" not in item:
            raise ValueError(f"--{label} 형식 오류: '{item}' (예: --{label} 1=\"2026-03-15 10:00\")")
        key, _, raw = item.partition("=")
        try:
            out[int(key.strip())] = raw
        except ValueError:
            raise ValueError(f"--{label} 키는 정수여야 합니다: '{key}'")
    return out


def load_document(db, args):
    q = db.query(ApprovalDocument)
    if args.id is not None:
        doc = q.filter(ApprovalDocument.id == args.id).first()
    else:
        doc = q.filter(ApprovalDocument.doc_number == args.doc).first()
    return doc


def show(doc: ApprovalDocument, tz_name: str):
    print(f"\n=== 문서 #{doc.id}  {doc.doc_number}  [{doc.status}] ===")
    print(f"  제목       : {doc.title}")
    print(f"  created_at : {fmt(doc.created_at, tz_name)}")
    print(f"  drafted_at : {fmt(doc.drafted_at, tz_name)}   (상신)")
    print(f"  completed_at: {fmt(doc.completed_at, tz_name)}   (완료)")
    print("  결재선(lines):")
    for ln in sorted(doc.lines, key=lambda x: x.step_order):
        print(f"    step {ln.step_order} (line.id={ln.id}, {ln.status}) "
              f"approver_id={ln.approver_id}  acted_at={fmt(ln.acted_at, tz_name)}")
    print("  감사이력(actions):")
    for ac in sorted(doc.actions, key=lambda x: (x.acted_at or datetime.min.replace(tzinfo=timezone.utc))):
        print(f"    action.id={ac.id}  {ac.action:8s}  actor_id={ac.actor_id}  "
              f"acted_at={fmt(ac.acted_at, tz_name)}")
    print()


def main():
    p = argparse.ArgumentParser(description="전자결재 날짜 직접 수정 (정정 이력 없음)")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--doc", help="문서번호 (예: AP-2026-0001)")
    target.add_argument("--id", type=int, help="문서 내부 id")

    p.add_argument("--drafted", help="documents.drafted_at 새 값 (지역시간)")
    p.add_argument("--completed", help="documents.completed_at 새 값")
    p.add_argument("--created", help="documents.created_at 새 값")
    p.add_argument("--line", action="append", metavar="STEP=날짜",
                   help="결재선 acted_at: step_order 기준. 반복 가능 (예: --line 1=\"2026-03-15 10:00\")")
    p.add_argument("--action", action="append", metavar="ACTIONID=날짜",
                   help="감사이력 acted_at: action.id 기준. 반복 가능")
    p.add_argument("--tz", default=DEFAULT_TZ, help=f"입력 시간대 (기본 {DEFAULT_TZ})")
    p.add_argument("--commit", action="store_true", help="실제 DB 반영 (없으면 미리보기만)")
    args = p.parse_args()

    line_map = parse_step_arg(args.line, "line")
    action_map = parse_step_arg(args.action, "action")

    db = get_session()
    try:
        doc = load_document(db, args)
        if not doc:
            print(f"[오류] 문서를 찾을 수 없습니다: {args.doc or args.id}", file=sys.stderr)
            sys.exit(1)

        print("\n[변경 전]")
        show(doc, args.tz)

        changes = []  # (설명, 적용함수)

        if args.drafted is not None:
            new = parse_local_to_utc(args.drafted, args.tz)
            changes.append((f"documents.drafted_at → {fmt(new, args.tz)}",
                            lambda v=new: setattr(doc, "drafted_at", v)))
        if args.completed is not None:
            new = parse_local_to_utc(args.completed, args.tz)
            changes.append((f"documents.completed_at → {fmt(new, args.tz)}",
                            lambda v=new: setattr(doc, "completed_at", v)))
        if args.created is not None:
            new = parse_local_to_utc(args.created, args.tz)
            changes.append((f"documents.created_at → {fmt(new, args.tz)}",
                            lambda v=new: setattr(doc, "created_at", v)))

        lines_by_step = {ln.step_order: ln for ln in doc.lines}
        for step, raw in line_map.items():
            ln = lines_by_step.get(step)
            if not ln:
                print(f"[오류] step_order={step} 결재선이 없습니다.", file=sys.stderr)
                sys.exit(1)
            new = parse_local_to_utc(raw, args.tz)
            changes.append((f"lines[step {step}].acted_at → {fmt(new, args.tz)}",
                            lambda l=ln, v=new: setattr(l, "acted_at", v)))

        actions_by_id = {ac.id: ac for ac in doc.actions}
        for aid, raw in action_map.items():
            ac = actions_by_id.get(aid)
            if not ac:
                print(f"[오류] action.id={aid} 가 이 문서에 없습니다.", file=sys.stderr)
                sys.exit(1)
            new = parse_local_to_utc(raw, args.tz)
            changes.append((f"actions[id {aid}].acted_at → {fmt(new, args.tz)}",
                            lambda a=ac, v=new: setattr(a, "acted_at", v)))

        if not changes:
            print("(변경 항목 없음 — 조회만 수행)")
            return

        print("[적용할 변경]")
        for desc, _ in changes:
            print(f"  - {desc}")
        print()

        for _, apply in changes:
            apply()

        if args.commit:
            db.commit()
            db.refresh(doc)
            print("✅ 커밋 완료. [변경 후]")
            show(doc, args.tz)
        else:
            db.rollback()
            print("ℹ️  미리보기(dry-run)입니다. 실제 반영하려면 --commit 을 붙이세요.")
    except Exception as e:
        db.rollback()
        print(f"[실패] {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
