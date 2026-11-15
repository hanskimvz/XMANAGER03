"""
연차 발생/이월/정산 엔진 (v0.45.0)

정책: 전자결재_연차관리_개발계획.md §2/§6 (회계연도 기준).
- 부여(회계연도): 첫해=입사일 일괄(12−입사월), 다음해=비례+월차 일괄, 3년차+=연초 15.
- 비례 반올림 = 반차(0.5일) 단위 올림(D-1).
- 잔여 = 원장 누적합(이월은 별도 행 없이 미사용분이 자연 이어짐). 수당지급(ALLOWANCE_PAID, −)이 이월을 차감.
- 사용(USAGE)은 승인된 휴가 결재에서 멱등 동기화.
- 퇴사 정산 = 정식 노동부 규정(입사일 기준 + 근속가산)으로 법정 발생 산출.

⚠️ 법정 정산(legal_entitlement)은 근로기준법 해석이 들어가므로 **노무/HR 검토 권장**.
   관리 화면에서 회계연도 부여합계·법정 둘 다 보여주고 관리자가 최종 확정(오버라이드)한다.
"""

import math
from datetime import date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.leave_ledger import (
    LeaveLedger,
    ENTRY_GRANT, ENTRY_USAGE, ENTRY_ALLOWANCE_PAID, ENTRY_ADJUST,
    SOURCE_AUTO, SOURCE_APPROVAL, SOURCE_MANUAL,
)
import re as _re

_USAGE_DATE_RE = _re.compile(r"(\d{4}-\d{2}-\d{2})(?:\s*~\s*(\d{4}-\d{2}-\d{2}))?")


def _usage_kind_and_date(e) -> tuple:
    """USAGE 원장 → (휴가구분, 날짜/기간). 엑셀·정산용. '관리자기입' 등 비고 문구는 넣지 않음."""
    memo = e.memo or ""
    amt = e.amount or 0
    if "병가" in memo:
        label = "병가"
    elif "오전" in memo and "반차" in memo:
        label = "오전반차"
    elif "오후" in memo and "반차" in memo:
        label = "오후반차"
    elif "반차" in memo or abs(amt) == 0.5:
        label = "반차"
    else:
        label = "종일휴가"
    m = _USAGE_DATE_RE.search(memo)
    if m:
        s, en = m.group(1), m.group(2)
        date_s = f"{s} ~ {en}" if en and en != s else s
    else:
        date_s = e.event_date.isoformat() if e.event_date else ""
    return label, date_s
from app.models.approval import ApprovalDocument, ApprovalForm
from app.models.user import User

ANNUAL_BASE = 15          # 만 1년 이상 기본 연차
MAX_LEGAL = 25            # 근속가산 포함 법정 한도
# 연차로 차감하는 휴가 유형.
# 사내 지침상 유급휴가는 연차뿐이므로 병가도 연차에서 차감한다.
# 경조/기타는 차감 대상이 아니다(무급 가능성이 있어 별도 판단 필요).
DEDUCTIBLE_TYPES = ("연차", "반차", "병가")


def is_deductible_leave(lt) -> bool:
    """연차 차감 대상: '연차'·'반차'(오전/오후 반차 포함)·'병가'. 경조/기타는 제외."""
    return isinstance(lt, str) and (lt in ("연차", "병가") or "반차" in lt)
LEAVE_FORM_CODE = "LEAVE"


# ==================== 공통 ====================

def ceil_half(x: float) -> float:
    """반차(0.5일) 단위 올림. 예: 12.3→12.5, 12.5→12.5, 12.6→13.0."""
    return math.ceil(round(x * 2, 6)) / 2.0


def _to_date(v) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v.strip():
        try:
            from datetime import datetime
            return datetime.strptime(v.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


# ==================== 부여 공식 (§2) ====================

def compute_grant(hire_date: date, fy: int) -> float:
    """회계연도 fy 에 부여할 연차 일수(운영 부여, 15 고정 정책)."""
    if hire_date is None:
        return 0.0
    HY, HM = hire_date.year, hire_date.month
    if fy < HY:
        return 0.0
    if fy == HY:
        # 첫해: 입사 다음달~12월 매월 1개 발생분을 입사일에 일괄
        return float(max(0, 12 - HM))
    if fy == HY + 1:
        # 다음해 연초 일괄 = (회계연도 개산법 비례) + (입사 1년 이내 월차)
        # 비례분: 전년(입사년) 재직일수 기준 — 15 × (재직일수/365), 반차 올림, 상한 15.
        days_worked = (date(HY, 12, 31) - hire_date).days + 1  # 입사일~12/31 (입사일 포함)
        proportional = min(ANNUAL_BASE, ceil_half(ANNUAL_BASE * days_worked / 365.0))
        monthly = max(0, HM - 1)  # 입사 1년 이내 월차(개월 단위 1일씩)
        return float(proportional + monthly)
    # 3년차+ : 회계연도 15 + 근속가산.
    # 근로기준법: 계속근로 3년 이상이면 최초 1년 초과 매 2년마다 +1(상한 25=가산 10).
    # 회계연도 부여(1/1)는 '전년도 말까지 완성된 근속연수' 기준 → 완성근속 m = (fy-1) - HY = n - 1.
    # 가산 = (m - 1)//2 = (n - 2)//2.  예) 2019입사: 2021·22=15, 2023·24=16, 2025·26=17.
    n = fy - HY
    bonus = min(MAX_LEGAL - ANNUAL_BASE, max(0, (n - 2) // 2))
    return float(ANNUAL_BASE + bonus)


def grant_event_date(hire_date: date, fy: int) -> date:
    """부여 처리일: 첫해=입사일, 이후=해당 회계연도 1/1."""
    if fy == hire_date.year:
        return hire_date
    return date(fy, 1, 1)


# ==================== 자동 발생(멱등) ====================

def _anniversary_grant_rows(hire: date, cap: date) -> list:
    """입사일 기준(근로기준법) GRANT 스케줄. [(event_date, amount, memo)].
    - 1년 미만: 매월 개근 1일(입사+k개월, 최대 11)
    - 만 y년(입사기념일): 15 + 근속가산(3년 이상 2년마다 +1, 상한 25)
    cap(기준일)까지 **이미 도래한** 발생만 생성 — 미래 달/기념일은 선지급하지 않음."""
    if hire is None or cap is None:
        return []
    rows = []
    one_year = _add_years(hire, 1)
    for k in range(1, 12):                      # 1~11개월차 월차
        ev = _add_months(hire, k)
        if ev >= one_year or ev > cap:
            break
        rows.append((ev, 1.0, f"입사 {k}개월 개근(월차)"))
    y = 1
    while True:                                 # 만 y년 기념일 발생
        ev = _add_years(hire, y)
        if ev > cap:
            break
        ann = min(MAX_LEGAL, ANNUAL_BASE + (((y - 1) // 2) if y >= 3 else 0))
        rows.append((ev, float(ann), f"입사 {y}년차 발생"))
        y += 1
    return rows


def _ensure_anniversary_grants(db: Session, user: User, upto_year: int, force: bool) -> int:
    """산업기능요원 입사일 기준 GRANT 동기화(멱등). 시그니처 비교로 변경 시에만 재생성.
    기준일 = min(upto_year 말일, 오늘, 퇴사일) → 미래분 선지급 방지."""
    cap = min(date(upto_year, 12, 31), date.today())
    if user.resign_date is not None:
        cap = min(cap, user.resign_date)
    desired = _anniversary_grant_rows(user.hire_date, cap)
    existing = db.query(LeaveLedger).filter(
        LeaveLedger.user_id == user.id,
        LeaveLedger.entry_type == ENTRY_GRANT,
        LeaveLedger.source_type == SOURCE_AUTO,
    ).all()
    want_sig = sorted((ev.isoformat(), round(amt, 1)) for ev, amt, _m in desired)
    have_sig = sorted((e.event_date.isoformat() if e.event_date else "", round(e.amount, 1)) for e in existing)
    if not force and want_sig == have_sig:
        return 0
    for e in existing:
        db.delete(e)
    db.flush()
    for ev, amt, memo in desired:
        db.add(LeaveLedger(
            user_id=user.id, fiscal_year=ev.year, entry_type=ENTRY_GRANT, amount=float(amt),
            event_date=ev, source_type=SOURCE_AUTO, memo=f"자동 발생(입사일 기준) · {memo}",
        ))
    db.commit()
    return len(desired)


def ensure_grants(db: Session, user: User, upto_year: int, force: bool = False) -> int:
    """입사연도~upto_year 의 GRANT(자동) 원장 생성. 멱등.
    force=True 면 기존 자동발생을 삭제 후 현재 공식으로 재계산(공식 변경 반영). Returns 생성 수."""
    if user is None or user.hire_date is None:
        return 0
    HY = user.hire_date.year
    end = upto_year
    if user.resign_date is not None:
        end = min(end, user.resign_date.year)  # 퇴사연도까지만 부여

    # 산업기능요원: 회계연도가 아니라 '입사일 기준(근로기준법)'으로 발생
    if getattr(user, "is_safety_officer", False):
        return _ensure_anniversary_grants(db, user, end, force)

    if force:
        db.query(LeaveLedger).filter(
            LeaveLedger.user_id == user.id,
            LeaveLedger.entry_type == ENTRY_GRANT,
            LeaveLedger.source_type == SOURCE_AUTO,
        ).delete()
        db.commit()
        existing = set()
    else:
        existing = {
            fy for (fy,) in db.query(LeaveLedger.fiscal_year).filter(
                LeaveLedger.user_id == user.id,
                LeaveLedger.entry_type == ENTRY_GRANT,
                LeaveLedger.source_type == SOURCE_AUTO,
            ).all()
        }
    created = 0
    for fy in range(HY, end + 1):
        if fy in existing:
            continue
        amt = compute_grant(user.hire_date, fy)
        if amt <= 0:
            continue
        db.add(LeaveLedger(
            user_id=user.id, fiscal_year=fy, entry_type=ENTRY_GRANT, amount=float(amt),
            event_date=grant_event_date(user.hire_date, fy), source_type=SOURCE_AUTO,
            memo="자동 발생(회계연도)",
        ))
        created += 1
    if created:
        db.commit()
    return created


# ==================== 사용 동기화(결재 → 원장) ====================

def _approved_leave_docs(db: Session, user_id: int):
    form = db.query(ApprovalForm).filter(ApprovalForm.code == LEAVE_FORM_CODE).first()
    if form is None:
        return []
    return (
        db.query(ApprovalDocument)
        .filter(
            ApprovalDocument.form_id == form.id,
            ApprovalDocument.drafter_id == user_id,
            ApprovalDocument.status == "APPROVED",
            ApprovalDocument.is_deleted.is_(False),
        )
        .all()
    )


def _next_business_day(d: date) -> date:
    """다음 영업일(토/일 건너뜀)."""
    nd = d + timedelta(days=1)
    while nd.weekday() >= 5:
        nd += timedelta(days=1)
    return nd


def _leave_dates(data: dict) -> List[date]:
    """휴가 form_data → 실제 사용 날짜 리스트(정렬·중복제거).
    `dates`(신청자가 고른 날짜 배열) 우선. 없으면 start_date~end_date 의 주중(월~금)."""
    raw = data.get("dates")
    if isinstance(raw, list) and raw:
        # 서버측 방어: 주말은 제외(UI도 막지만 직접 호출/레거시 페이로드 대비)
        ds = sorted({d for d in (_to_date(x) for x in raw) if d is not None and d.weekday() < 5})
        return ds
    sd = _to_date(data.get("start_date"))
    ed = _to_date(data.get("end_date")) or sd
    if sd is None:
        return []
    if ed < sd:
        sd, ed = ed, sd
    out: List[date] = []
    cur = sd
    while cur <= ed:
        if cur.weekday() < 5:  # 주말 제외
            out.append(cur)
        cur += timedelta(days=1)
    return out


def _group_runs(dates: List[date]) -> List[Tuple[date, date, int]]:
    """정렬된 날짜 → 달력상 연속 구간 [(시작, 끝, 일수)].
    달력상 바로 다음날(d+1)일 때만 같은 구간 → **주말이 끼면 줄이 나뉨**(선택 날짜에 주말은 없음).
    회계연도(연도)가 바뀌면 구간을 분할 → 연말~연초에 걸친 휴가가 시작연도에 몰려 집계되지 않게 함."""
    runs: List[Tuple[date, date, int]] = []
    for d in dates:
        if runs and d == runs[-1][1] + timedelta(days=1) and d.year == runs[-1][1].year:
            s, _e, n = runs[-1]
            runs[-1] = (s, d, n + 1)
        else:
            runs.append((d, d, 1))
    return runs


def sync_usage(db: Session, user: User) -> int:
    """승인된 휴가(연차/반차) 결재 ↔ USAGE 원장 멱등 동기화.
    한 결재의 사용 날짜를 **연속 구간별 1행**으로 기록(중간이 끊기면 다음 행)."""
    if user is None:
        return 0
    # 동시 호출(예: /me 와 /overview 전 직원 루프) 간 read-modify-write 경쟁으로
    # 같은 USAGE 행이 중복 삽입되는 것을 막기 위해 사용자 행을 잠가 직렬화한다.
    db.query(User.id).filter(User.id == user.id).with_for_update().first()
    docs = _approved_leave_docs(db, user.id)
    # 결재별 원하는 USAGE 행들: doc_id -> [(fy, start, amount, memo)]
    desired = {}
    for doc in docs:
        data = doc.form_data or {}
        lt = data.get("leave_type")
        if not is_deductible_leave(lt):
            continue
        dates = _leave_dates(data)
        if not dates:
            continue
        per_day = 0.5 if (isinstance(lt, str) and "반차" in lt) else 1.0
        entries = []
        for (rs, re, n) in _group_runs(dates):
            amt = round(n * per_day, 1)
            memo = f"{lt} {rs.isoformat()}" if rs == re else f"{lt} {rs.isoformat()}~{re.isoformat()}"
            entries.append((rs.year, rs, amt, memo))
        desired[doc.id] = entries

    existing_by_doc = {}
    voided_doc_ids = set()
    for e in db.query(LeaveLedger).filter(
        LeaveLedger.user_id == user.id,
        LeaveLedger.entry_type == ENTRY_USAGE,
        LeaveLedger.source_type == SOURCE_APPROVAL,
    ).all():
        if e.source_doc_id is not None:
            existing_by_doc.setdefault(e.source_doc_id, []).append(e)
            if e.voided:
                voided_doc_ids.add(e.source_doc_id)

    changed = 0
    for did in set(desired) | set(existing_by_doc):
        # 취소로 무효화된 휴가는 원장을 손대지 않고 그대로 보존(빗금 유지)
        if did in voided_doc_ids:
            continue
        want = desired.get(did, [])
        have = existing_by_doc.get(did, [])
        want_sig = sorted((fy, sd.isoformat(), amt) for (fy, sd, amt, _m) in want)
        have_sig = sorted((e.fiscal_year, e.event_date.isoformat() if e.event_date else "", round(abs(e.amount), 1)) for e in have)
        if want_sig == have_sig:
            continue
        for e in have:
            db.delete(e)
        for (fy, sd, amt, memo) in want:
            db.add(LeaveLedger(
                user_id=user.id, fiscal_year=fy, entry_type=ENTRY_USAGE, amount=-abs(amt),
                event_date=sd, source_type=SOURCE_APPROVAL, source_doc_id=did, memo=memo,
            ))
        changed += 1
    if changed:
        db.commit()
    return changed


def void_usage_for_doc(db: Session, source_doc_id: int) -> int:
    """휴가 취소: 해당 휴가 결재(source_doc_id)의 USAGE 원장 행을 무효화(voided=True).
    삭제하지 않고 남겨(빗금 표시) 잔여 합산에서만 제외 → 일수 복구. 반환=무효화된 행 수."""
    rows = db.query(LeaveLedger).filter(
        LeaveLedger.entry_type == ENTRY_USAGE,
        LeaveLedger.source_doc_id == source_doc_id,
        LeaveLedger.voided.is_(False),
    ).all()
    for e in rows:
        e.voided = True
        e.memo = (e.memo or "") + " · 취소됨"
    if rows:
        db.commit()
    return len(rows)


def unvoid_usage_for_doc(db: Session, source_doc_id: int) -> int:
    """휴가취소 철회(취소 문서 삭제): void_usage_for_doc 의 역연산.
    해당 휴가 결재의 무효화된 USAGE 행을 다시 유효화(voided=False)해 일수를 재차감.
    반환=복구된 행 수. (commit 하지 않음 — 호출측에서 sync 후 일괄 commit)"""
    rows = db.query(LeaveLedger).filter(
        LeaveLedger.entry_type == ENTRY_USAGE,
        LeaveLedger.source_doc_id == source_doc_id,
        LeaveLedger.voided.is_(True),
    ).all()
    for e in rows:
        e.voided = False
        if e.memo and e.memo.endswith(" · 취소됨"):
            e.memo = e.memo[: -len(" · 취소됨")]
    return len(rows)


# ==================== 잔여/요약 ====================

def refresh(db: Session, user: User, upto_year: int) -> None:
    """발생+사용 동기화(표시/계산 전에 1회)."""
    ensure_grants(db, user, upto_year)
    sync_usage(db, user)


def _sum(db: Session, user_id: int, *, fy=None, fy_lte=None, entry_type=None) -> float:
    # 무효화(취소)된 행은 잔여/집계에서 제외 — 감사용으로 원장에는 남고 빗금으로 표시됨
    q = db.query(LeaveLedger).filter(
        LeaveLedger.user_id == user_id,
        LeaveLedger.voided.is_(False),
    )
    if fy is not None:
        q = q.filter(LeaveLedger.fiscal_year == fy)
    if fy_lte is not None:
        q = q.filter(LeaveLedger.fiscal_year <= fy_lte)
    if entry_type is not None:
        q = q.filter(LeaveLedger.entry_type == entry_type)
    return float(sum(e.amount for e in q.all()))


def balance(db: Session, user_id: int, asof_fy: int) -> float:
    """asof_fy 말 기준 누적 잔여(= 이월 포함)."""
    return _sum(db, user_id, fy_lte=asof_fy)


def year_summary(db: Session, user_id: int, fy: int) -> dict:
    """연도별 표 1행: 이월/부여/사용/수당/조정/잔여."""
    carried_in = _sum(db, user_id, fy_lte=fy - 1)
    granted = _sum(db, user_id, fy=fy, entry_type=ENTRY_GRANT)
    used = -_sum(db, user_id, fy=fy, entry_type=ENTRY_USAGE)            # 양수로
    paid = -_sum(db, user_id, fy=fy, entry_type=ENTRY_ALLOWANCE_PAID)  # 양수로
    adjust = _sum(db, user_id, fy=fy, entry_type=ENTRY_ADJUST)
    remaining = carried_in + granted + adjust - used - paid
    return {
        "fiscal_year": fy,
        "carried_in": round(carried_in, 1),
        "granted": round(granted, 1),
        "used": round(used, 1),
        "allowance_paid": round(paid, 1),
        "adjust": round(adjust, 1),
        "remaining": round(remaining, 1),
    }


# ==================== 퇴사 정산(법정) ====================

def _add_years(d: date, n: int) -> date:
    """d 에 n 년 더하기. 2/29 입사자는 비윤년 2/28 로 보정(ValueError 방지)."""
    try:
        return date(d.year + n, d.month, d.day)
    except ValueError:
        return date(d.year + n, d.month, 28)


def _full_years(hire: date, asof: date) -> int:
    """만 근속연수."""
    y = asof.year - hire.year
    if (asof.month, asof.day) < (hire.month, hire.day):
        y -= 1
    return max(0, y)


def _full_months(hire: date, asof: date) -> int:
    m = (asof.year - hire.year) * 12 + (asof.month - hire.month)
    if asof.day < hire.day:
        m -= 1
    return max(0, m)


def legal_entitlement(hire: date, asof: date) -> float:
    """정식 노동부(근로기준법) 기준 입사일~asof 누적 발생 연차.
    - 1년 미만: 매월 개근 1일(최대 11)
    - 만 N년: 각 1년 만료마다 15일 + 근속가산(3년 이상, 2년마다 +1, 한도 25)
    ⚠️ 노무 검토 권장.
    """
    if hire is None or asof is None or asof < hire:
        return 0.0
    total = 0.0
    # 1년 미만 월차(최대 11) — 입사 후 만 1년 도달 전까지
    one_year = _add_years(hire, 1)
    months = _full_months(hire, min(asof, one_year))
    total += float(min(11, max(0, months)))
    # 만 N년 경과: 각 연도 만료 시 연차 발생
    years = _full_years(hire, asof)
    for y in range(1, years + 1):
        ann = ANNUAL_BASE + (((y - 1) // 2) if y >= 3 else 0)
        total += float(min(MAX_LEGAL, ann))
    return total


def settlement(db: Session, user: User, asof: Optional[date] = None) -> dict:
    """퇴사 정산 요약(미정산 연차일수 산출). asof 미지정 시 퇴사일, 없으면 오늘(현재까지 누적)."""
    asof = asof or user.resign_date or date.today()
    refresh(db, user, asof.year)
    fiscal_granted = _sum(db, user.id, entry_type=ENTRY_GRANT)
    used = -_sum(db, user.id, entry_type=ENTRY_USAGE)
    paid = -_sum(db, user.id, entry_type=ENTRY_ALLOWANCE_PAID)
    adjust = _sum(db, user.id, entry_type=ENTRY_ADJUST)
    legal = legal_entitlement(user.hire_date, asof) if user.hire_date else 0.0
    # 법정 기준 미정산 = 법정 발생 + 수동조정 − 사용 − 기지급수당
    # (수동조정: 도입 초기값/관리자 가감 — 정산·엑셀에 반드시 반영. v0.45.1 버그수정)
    unsettled = round(legal + adjust - used - paid, 1)
    return {
        "asof": asof.isoformat(),
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
        "legal_entitlement": round(legal, 1),
        "fiscal_granted": round(fiscal_granted + adjust, 1),
        "adjust": round(adjust, 1),       # 수동조정 합계(+추가/−차감) — 정산에 반영됨
        "used": round(used, 1),
        "allowance_paid": round(paid, 1),
        "unsettled_days": unsettled,      # 퇴직금에 연차수당으로 정산할 일수(법정+조정 기준)
        "note": "법정 계산은 노무 검토 권장 — 관리자 최종 확정",
    }


def _add_months(d: date, n: int) -> date:
    """d 에 n 개월 더하기(말일 보정)."""
    import calendar
    m = d.month - 1 + n
    y = d.year + m // 12
    mm = m % 12 + 1
    return date(y, mm, min(d.day, calendar.monthrange(y, mm)[1]))


def legal_breakdown(hire: date, asof: date) -> List[dict]:
    """입사일 기준 법정 발생 내역(엑셀용). [{desc, days}] (합계 = legal_entitlement)."""
    if hire is None or asof is None or asof < hire:
        return []
    rows: List[dict] = []
    one_year = _add_years(hire, 1)
    months = min(11, max(0, _full_months(hire, min(asof, one_year))))
    if months > 0:
        first = _add_months(hire, 1)        # 첫 월차 발생 ≈ 입사+1개월
        last = _add_months(hire, months)
        rows.append({"desc": f"{first.isoformat()} ~ {last.isoformat()} (매월 1일씩)", "days": float(months)})
    for y in range(1, _full_years(hire, asof) + 1):
        ann = float(min(MAX_LEGAL, ANNUAL_BASE + (((y - 1) // 2) if y >= 3 else 0)))
        anniv = _add_years(hire, y)
        rows.append({"desc": f"입사 {y}년째 {anniv.isoformat()}", "days": ann})
    return rows


def usage_detail(db: Session, user: User) -> dict:
    """연도별 사용 내역 {fy: [{label(구분), date(날짜/기간), days}]} (엑셀용)."""
    out: dict = {}
    rows = db.query(LeaveLedger).filter(
        LeaveLedger.user_id == user.id,
        LeaveLedger.entry_type == ENTRY_USAGE,
        LeaveLedger.voided.is_(False),  # 취소된 사용은 제외
    ).order_by(LeaveLedger.fiscal_year, LeaveLedger.event_date).all()
    for e in rows:
        label, date_s = _usage_kind_and_date(e)
        out.setdefault(e.fiscal_year, []).append(
            {"label": label, "date": date_s, "days": round(abs(e.amount), 1)}
        )
    return out


def allowance_detail(db: Session, user: User) -> dict:
    """연도별 연차수당 지급 내역 {fy: [{label, days}]} (엑셀용, 일수 — 금액 아님)."""
    out: dict = {}
    rows = db.query(LeaveLedger).filter(
        LeaveLedger.user_id == user.id,
        LeaveLedger.entry_type == ENTRY_ALLOWANCE_PAID,
    ).order_by(LeaveLedger.fiscal_year, LeaveLedger.event_date).all()
    for e in rows:
        label = e.memo or (f"{e.fiscal_year}년 연차수당 지급")
        out.setdefault(e.fiscal_year, []).append({"label": label, "days": round(abs(e.amount), 1)})
    return out


def adjust_detail(db: Session, user: User) -> dict:
    """연도별 수동 조정 내역 {fy: [{label, days(±부호유지)}]} (엑셀용).
    +추가/−차감 부호를 그대로 보존해 정산 근거를 명확히 표시."""
    out: dict = {}
    rows = db.query(LeaveLedger).filter(
        LeaveLedger.user_id == user.id,
        LeaveLedger.entry_type == ENTRY_ADJUST,
    ).order_by(LeaveLedger.fiscal_year, LeaveLedger.event_date).all()
    for e in rows:
        label = e.memo or "수동 조정"
        out.setdefault(e.fiscal_year, []).append({"label": label, "days": round(e.amount, 1)})
    return out
