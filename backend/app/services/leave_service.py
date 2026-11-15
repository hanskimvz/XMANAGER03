"""
휴가 연차 계산 서비스 (v0.34.0)

설계: LEAVE 양식 문서의 form_data['days'] 를 영업일 기준으로 계산하고,
연차 잔여(entitlement - used)를 산출한다.

공휴일 반영은 Phase 추후 — 현재는 주말(토/일)만 제외한다.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.approval import ApprovalDocument, ApprovalForm
from app.models.user import User

# 연차로 차감하는 휴가 유형. 판정은 leave_accrual_service 가 단일 기준.
# (사내 지침: 유급휴가는 연차뿐 → 병가도 차감. 경조/기타는 제외)
from app.services.leave_accrual_service import DEDUCTIBLE_TYPES, is_deductible_leave  # noqa: F401
DEFAULT_ENTITLEMENT = 15


def _to_date(value) -> Optional[date]:
    """'YYYY-MM-DD' 문자열 / date / datetime → date 변환. 실패 시 None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # 'YYYY-MM-DD' 또는 'YYYY-MM-DDTHH:MM' 등 앞 10자 사용
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def business_days(start_date, end_date) -> int:
    """주말(토/일) 제외, 양끝 포함 영업일 수. (공휴일은 Phase 추후)"""
    start = _to_date(start_date)
    end = _to_date(end_date)
    if start is None or end is None:
        return 0
    if end < start:
        start, end = end, start
    count = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # 0=월 ... 4=금
            count += 1
        cur += timedelta(days=1)
    return count


def _is_half_day(leave_type) -> bool:
    return isinstance(leave_type, str) and "반차" in leave_type


def compute_leave_days(leave_type: Optional[str], start_date, end_date) -> float:
    """휴가 일수 계산. 반차(오전/오후 포함)=0.5, 그 외=영업일 수."""
    if _is_half_day(leave_type):
        return 0.5
    return float(business_days(start_date, end_date))


def leave_balance(db: Session, user_id: int, year: int) -> dict:
    """연차 잔여 산출.

    v0.45.0: 입사일이 있으면 **연차 원장(회계연도 엔진)** 기반으로 산출(이월 포함).
    입사일이 없으면 레거시(annual_leave_days 고정 − 사용) 방식으로 폴백.
    """
    user = db.query(User).filter(User.id == user_id).first()

    # v0.45.0: 입사일 보유 시 원장 엔진 사용(발생+이월+사용 동기화)
    if user is not None and getattr(user, "hire_date", None) is not None:
        from app.services import leave_accrual_service as acc
        acc.refresh(db, user, year if user.resign_date is None else max(year, user.resign_date.year))
        s = acc.year_summary(db, user_id, year)
        entitlement = s["carried_in"] + s["granted"] + s["adjust"]
        return {
            "year": year,
            "entitlement": round(entitlement, 1),
            "used": s["used"],
            "remaining": s["remaining"],
        }

    entitlement = float(
        getattr(user, "annual_leave_days", None) or DEFAULT_ENTITLEMENT
    ) if user else float(DEFAULT_ENTITLEMENT)

    leave_form = db.query(ApprovalForm).filter(ApprovalForm.code == "LEAVE").first()
    used = 0.0
    if leave_form is not None:
        docs = (
            db.query(ApprovalDocument)
            .filter(
                ApprovalDocument.form_id == leave_form.id,
                ApprovalDocument.drafter_id == user_id,
                ApprovalDocument.status == "APPROVED",
            )
            .all()
        )
        for doc in docs:
            data = doc.form_data or {}
            leave_type = data.get("leave_type")
            if not is_deductible_leave(leave_type):
                continue
            # 연도 필터: start_date 기준
            sd = _to_date(data.get("start_date"))
            if sd is not None and sd.year != year:
                continue
            days = data.get("days")
            if days in (None, ""):
                days = compute_leave_days(
                    leave_type, data.get("start_date"), data.get("end_date")
                )
            try:
                used += float(days)
            except (TypeError, ValueError):
                continue

    return {
        "year": year,
        "entitlement": entitlement,
        "used": used,
        "remaining": entitlement - used,
    }
