"""
연차 관리 API (v0.45.0)

A 예외 라우터: 자체 인증.
- 본인 조회: require_auth
- 관리(경영지원팀): leave_manager 가드 — RBAC_MODE 존중(disabled=로그인만 / observe·enforce=leave:manage).
  (시스템 전체가 disabled 면 무게이팅이므로 연차도 동일하게 동작 = 메뉴/API 일관성)

설계: 전자결재_연차관리_개발계획.md §5~§7
"""
import re
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_auth, require_admin, security, get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.leave_ledger import (
    LeaveLedger, ENTRY_ADJUST, ENTRY_ALLOWANCE_PAID, ENTRY_USAGE, SOURCE_MANUAL,
)
from app.schemas.leave import (
    LeaveYearSummary, LeaveLedgerEntry, LeaveOverviewRow, LeaveDetail,
    AdjustRequest, AllowanceRequest, SettlementResponse, EmploymentUpdate,
    ManualUsageRequest, CompanyWideLeaveRequest, SafetyOfficerUpdate,
)
from app.models.leave_ledger import ENTRY_GRANT, SOURCE_AUTO
from app.services import leave_accrual_service as acc

router = APIRouter(prefix="/leave", tags=["연차관리"])


def _cur_year() -> int:
    return datetime.now().year


def leave_manager(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """연차 관리 접근 가드. leave 는 **민감 모듈(항상 enforce)** 이라 RBAC_MODE 와 무관하게
    항상 leave:manage 권한을 요구한다(경영지원팀/ADMIN 와일드카드). v0.47.0 모듈 정책 사용.
    """
    user = get_current_user(credentials, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다",
                            headers={"WWW-Authenticate": "Bearer"})
    from app.services.rbac_service import effective_mode, has_permission
    if effective_mode(db, "leave") == "disabled":
        return user  # (이론상 발생 안 함 — leave 는 SENSITIVE)
    if not has_permission(db, user, "leave:manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="연차 관리 권한이 없습니다(경영지원팀/관리자)")
    return user


def _leave_app_entries(db: Session, user: User, cy: int) -> list:
    """경조/기타 휴가의 승인된 신청 내역을 '표시 전용' 원장 항목으로 반환.

    연차 잔여(GRANT/USAGE 누적)에는 영향을 주지 않는다(amount=0, source_type=LEAVE_APP).
    id는 음수(-approval_doc_id)로 실제 원장 id와 충돌 방지 + 삭제 불가 표식.
    """
    from datetime import date as _date
    from app.models.approval import ApprovalDocument, ApprovalForm
    leave_form = db.query(ApprovalForm).filter(ApprovalForm.code == "LEAVE").first()
    if not leave_form:
        return []
    # 취소(휴가취소 결재 승인)된 원 휴가 결재 id 집합 — 표시에서 빗금 처리
    cancelled_ids = set()
    lc_form = db.query(ApprovalForm).filter(ApprovalForm.code == "LEAVE_CANCEL").first()
    if lc_form:
        for c in db.query(ApprovalDocument).filter(
            ApprovalDocument.form_id == lc_form.id,
            ApprovalDocument.status == "APPROVED",
            ApprovalDocument.is_deleted.is_(False),
        ).all():
            rel = list(c.related_document_ids or [])
            if not rel and c.related_document_id is not None:
                rel = [c.related_document_id]
            cancelled_ids.update(rel)
    docs = (
        db.query(ApprovalDocument)
        .filter(
            ApprovalDocument.form_id == leave_form.id,
            ApprovalDocument.drafter_id == user.id,
            ApprovalDocument.status == "APPROVED",
            ApprovalDocument.is_deleted.is_(False),
        )
        .all()
    )
    out = []
    for d in docs:
        fd = d.form_data or {}
        lt = (fd.get("leave_type") or "").strip()
        if not ("경조" in lt or "기타" in lt):  # 경조/기타 휴가만
            continue
        sd, ed, days = fd.get("start_date"), fd.get("end_date"), fd.get("days")
        try:
            ev = _date.fromisoformat(sd) if sd else None
        except (TypeError, ValueError):
            ev = None
        period = sd if (not ed or ed == sd) else f"{sd} ~ {ed}"
        reason = (fd.get("reason") or "").strip()   # 사유(예: 조모상)
        is_cancelled = d.id in cancelled_ids
        note = reason or f"{lt} 신청"
        if is_cancelled:
            note = f"{note} · 취소됨"
        out.append(LeaveLedgerEntry(
            id=-d.id,
            fiscal_year=(ev.year if ev else cy),
            entry_type=lt,
            amount=0.0,
            event_date=ev,
            source_type="LEAVE_APP",
            memo=note,
            voided=is_cancelled,
            kind_label=f"{lt}휴가",       # 경조휴가 / 기타휴가
            date_display=(str(period) if period else ""),
            memo_label=note,              # 비고: 사유(조모상 등)
            admin_only=False,
        ))
    return out


_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:\s*~\s*(\d{4}-\d{2}-\d{2}))?")


def _dates_from(memo: Optional[str], event_date) -> str:
    """메모/이벤트일에서 날짜·기간 문자열 추출. 예: '2026-01-05~2026-01-07' 또는 '2026-01-05'."""
    if memo:
        m = _DATE_RE.search(memo)
        if m:
            s, e = m.group(1), m.group(2)
            return f"{s} ~ {e}" if e and e != s else s
    return event_date.isoformat() if event_date else ""


def _ledger_display(e) -> tuple:
    """원장 행 → (휴가구분, 날짜/기간, 비고).
    - 휴가부여(GRANT): 구분 공란, 비고 '휴가부여'
    - 개인 결재 사용(USAGE·결재연동): 구분 종일휴가/오전반차/오후반차, 비고 공란
    - 관리자 조정/수동기입(ADJUST·수동 USAGE): 비고 '관리자 조정 · 사유'
    - 연차수당(ALLOWANCE_PAID): 비고 '연차수당'
    - 경조/기타(LEAVE_APP)는 _leave_app_entries 에서 별도 설정."""
    et = e.entry_type
    st = e.source_type
    memo = e.memo or ""
    amt = e.amount or 0
    kind = ""
    note = ""
    if et == ENTRY_GRANT:
        note = "휴가부여"
    elif et == ENTRY_ALLOWANCE_PAID:
        note = "연차수당"
    elif et == ENTRY_ADJUST:
        reason = memo.strip()
        note = f"관리자 조정 · {reason}" if reason else "관리자 조정"
    elif et == ENTRY_USAGE:
        # 구분(휴가유형)은 공통으로 판정
        if "오전" in memo and "반차" in memo:
            kind = "오전반차"
        elif "오후" in memo and "반차" in memo:
            kind = "오후반차"
        elif "반차" in memo or abs(amt) == 0.5:
            kind = "반차"
        else:
            kind = "종일휴가"
        # 관리자 임의 기입(소급/전사)은 비고 '관리자 조정', 개인 결재는 비고 공란
        if st == SOURCE_MANUAL:
            note = "관리자 조정"
    else:
        kind = et
    return kind, _dates_from(memo, e.event_date), note


def _detail(db: Session, user: User) -> LeaveDetail:
    cy = _cur_year()
    upto = cy if user.resign_date is None else max(cy, user.resign_date.year)
    acc.refresh(db, user, upto)
    start = user.hire_date.year if user.hire_date else cy
    end = upto
    years = [LeaveYearSummary(**acc.year_summary(db, user.id, fy)) for fy in range(start, end + 1)]
    ledger = []
    for e in (
        db.query(LeaveLedger)
        .filter(LeaveLedger.user_id == user.id)
        .order_by(LeaveLedger.fiscal_year, LeaveLedger.id)
        .all()
    ):
        entry = LeaveLedgerEntry.model_validate(e)
        entry.kind_label, entry.date_display, entry.memo_label = _ledger_display(e)
        ledger.append(entry)
    # 경조/기타 휴가 신청 내역도 원장에 함께 표시(잔여 계산에는 미반영)
    ledger.extend(_leave_app_entries(db, user, cy))
    return LeaveDetail(
        user_id=user.id, name=user.name, hire_date=user.hire_date, resign_date=user.resign_date,
        current_year=cy, current_remaining=round(acc.balance(db, user.id, cy), 1),
        years=years, ledger=ledger,
    )


# ---------- 본인 ----------
@router.get("/me", response_model=LeaveDetail)
def my_leave(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    # 본인 화면도 거래원장과 동일하게 전체 표시(삭제만 불가)
    return _detail(db, user)


# ---------- 관리(경영지원팀) ----------
@router.get("/overview", response_model=List[LeaveOverviewRow], dependencies=[Depends(leave_manager)])
def overview(db: Session = Depends(get_db)):
    """전 재직자 연차 현황(올해 잔여). 입사일 있으면 자동 발생/동기화 후 집계."""
    cy = _cur_year()
    rows: List[LeaveOverviewRow] = []
    # 재직자(is_active) + 퇴사자(resign_date 있음)를 모두 반환 → 프론트에서 재직/퇴사 탭으로 분류
    users = (
        db.query(User)
        .filter((User.is_active == True) | (User.resign_date.isnot(None)))  # noqa: E712
        .order_by(User.id)
        .all()
    )
    for u in users:
        if u.hire_date is not None:
            acc.refresh(db, u, cy if u.resign_date is None else max(cy, u.resign_date.year))
        rows.append(LeaveOverviewRow(
            user_id=u.id, username=u.username, name=u.name, department=u.department, position=u.position,
            hire_date=u.hire_date, resign_date=u.resign_date, current_year=cy,
            current_remaining=round(acc.balance(db, u.id, cy), 1) if u.hire_date else 0.0,
            has_hire_date=u.hire_date is not None,
            is_safety_officer=bool(getattr(u, "is_safety_officer", False)),
        ))
    return rows


@router.post("/company-wide", dependencies=[Depends(leave_manager)])
def company_wide_leave(req: CompanyWideLeaveRequest, admin: User = Depends(require_auth), db: Session = Depends(get_db)):
    """회사 전체 휴가 시행 — 전 재직자에게 USAGE(−days)를 일괄 기입(일부 제외 가능).
    제외 목록(exclude_user_ids)에 든 사용자는 건너뜀. SOURCE_MANUAL 이라 개별 원장에서 삭제/조정 가능."""
    excl = set(req.exclude_user_ids or [])
    # 멱등: 같은 날짜+메모의 전사부여가 이미 있는 사용자는 건너뜀(더블클릭/재시도 중복차감 방지)
    already = {
        uid for (uid,) in db.query(LeaveLedger.user_id).filter(
            LeaveLedger.entry_type == ENTRY_USAGE,
            LeaveLedger.source_type == SOURCE_MANUAL,
            LeaveLedger.event_date == req.event_date,
            LeaveLedger.memo == req.memo,
        ).all()
    }
    users = db.query(User).filter(User.is_active == True).order_by(User.id).all()  # noqa: E712
    applied = 0
    skipped = 0
    for u in users:
        # 제외 목록 / 이미 부여됨 / 미입사(입사일 없음·시행일 이후 입사) / 퇴사(시행일 이전 퇴사) 는 건너뜀
        if (u.id in excl or u.id in already
                or u.hire_date is None or u.hire_date > req.event_date
                or (u.resign_date is not None and u.resign_date < req.event_date)):
            skipped += 1
            continue
        db.add(LeaveLedger(
            user_id=u.id, fiscal_year=req.event_date.year, entry_type=ENTRY_USAGE,
            amount=-abs(float(req.days)), event_date=req.event_date, source_type=SOURCE_MANUAL,
            memo=req.memo, created_by=admin.id,
        ))
        applied += 1
    db.commit()
    return {"applied": applied, "excluded": len(excl), "skipped": skipped,
            "event_date": req.event_date.isoformat(), "days": abs(float(req.days))}


@router.get("/{user_id}", response_model=LeaveDetail, dependencies=[Depends(leave_manager)])
def get_user_leave(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    return _detail(db, u)


@router.put("/{user_id}/employment", response_model=LeaveDetail, dependencies=[Depends(leave_manager)])
def set_employment(user_id: int, req: EmploymentUpdate, db: Session = Depends(get_db)):
    """연차 관리 화면에서 입사일/퇴사일 직접 지정(경영지원팀). 변경 시 자동발생 원장 재생성."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    changed = (u.hire_date != req.hire_date) or (u.resign_date != req.resign_date)
    u.hire_date = req.hire_date
    u.resign_date = req.resign_date
    if changed:
        # 입사일 변경 시 기존 자동발생(GRANT/AUTO)은 무효 → 삭제 후 재생성(수동 조정/수당/사용은 보존)
        db.query(LeaveLedger).filter(
            LeaveLedger.user_id == user_id,
            LeaveLedger.entry_type == ENTRY_GRANT,
            LeaveLedger.source_type == SOURCE_AUTO,
        ).delete()
    db.commit()
    return _detail(db, u)


@router.put("/{user_id}/safety-officer", response_model=LeaveDetail, dependencies=[Depends(leave_manager)])
def set_safety_officer(user_id: int, req: SafetyOfficerUpdate, db: Session = Depends(get_db)):
    """산업기능요원 지정/해제. True면 연차 자동발생을 '입사일 기준(근로기준법)'으로 산정.
    변경 시 자동발생을 현재 기준으로 강제 재계산(회계연도 ↔ 입사일)."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    u.is_safety_officer = bool(req.is_safety_officer)
    db.commit()
    if u.hire_date is not None:
        upto = _cur_year() if u.resign_date is None else max(_cur_year(), u.resign_date.year)
        acc.ensure_grants(db, u, upto, force=True)  # 기준 전환 → 강제 재계산
        acc.sync_usage(db, u)
    return _detail(db, u)


@router.post("/{user_id}/adjust", response_model=LeaveDetail, dependencies=[Depends(leave_manager)])
def adjust(user_id: int, req: AdjustRequest, admin: User = Depends(require_auth), db: Session = Depends(get_db)):
    """수동 조정/오버라이드(도입 초기 opening 포함). ADJUST 원장 추가."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    db.add(LeaveLedger(
        user_id=user_id, fiscal_year=req.fiscal_year, entry_type=ENTRY_ADJUST,
        amount=float(req.amount), event_date=date.today(), source_type=SOURCE_MANUAL,
        memo=req.memo, created_by=admin.id,
    ))
    db.commit()
    return _detail(db, u)


@router.post("/{user_id}/usage", response_model=LeaveDetail, dependencies=[Depends(leave_manager)])
def add_usage(user_id: int, req: ManualUsageRequest, admin: User = Depends(require_auth), db: Session = Depends(get_db)):
    """과거에 누락된 휴가 사용을 실제 날짜와 함께 소급 기입(백필).
    USAGE(−) + event_date + SOURCE_MANUAL → 잔여/엑셀/정산의 '사용'에 자동 반영.
    (결재연동 USAGE 와 달리 source=MANUAL 이라 동기화에 삭제되지 않고, 원장에서 직접 삭제 가능)"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    db.add(LeaveLedger(
        user_id=user_id, fiscal_year=req.event_date.year, entry_type=ENTRY_USAGE,
        amount=-abs(float(req.days)), event_date=req.event_date, source_type=SOURCE_MANUAL,
        memo=req.memo or f"{req.event_date.isoformat()} 휴가(소급 기입)", created_by=admin.id,
    ))
    db.commit()
    return _detail(db, u)


@router.post("/{user_id}/allowance", response_model=LeaveDetail, dependencies=[Depends(leave_manager)])
def pay_allowance(user_id: int, req: AllowanceRequest, admin: User = Depends(require_auth), db: Session = Depends(get_db)):
    """연말 연차수당 지급 입력. ALLOWANCE_PAID(−) → 다음 해 이월에서 자동 차감."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    db.add(LeaveLedger(
        user_id=user_id, fiscal_year=req.fiscal_year, entry_type=ENTRY_ALLOWANCE_PAID,
        amount=-abs(float(req.days)),
        event_date=date(req.fiscal_year, 12, 31),  # 해당 회계연도 말일로 자동 지정
        source_type=SOURCE_MANUAL,
        memo=req.memo or f"{req.fiscal_year}년 연차수당 지급", created_by=admin.id,
    ))
    db.commit()
    return _detail(db, u)


@router.delete("/ledger/{entry_id}", status_code=204, dependencies=[Depends(leave_manager)])
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    """수동 원장(조정/수당) 삭제. 자동발생·결재사용은 동기화로 관리되므로 수동만 허용."""
    e = db.query(LeaveLedger).filter(LeaveLedger.id == entry_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="원장을 찾을 수 없습니다")
    if e.source_type != SOURCE_MANUAL:
        raise HTTPException(status_code=400, detail="자동/결재 연동 원장은 삭제할 수 없습니다")
    db.delete(e)
    db.commit()


@router.get("/{user_id}/settlement", response_model=SettlementResponse, dependencies=[Depends(require_admin)])
def settlement(user_id: int, asof: Optional[date] = None, db: Session = Depends(get_db)):
    """퇴사 정산(법정). asof 미지정 시 퇴사일/올해말."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    if u.hire_date is None:
        raise HTTPException(status_code=400, detail="입사일이 없어 정산할 수 없습니다")
    return SettlementResponse(**acc.settlement(db, u, asof))


@router.get("/{user_id}/settlement.xlsx", dependencies=[Depends(require_admin)])
def settlement_xlsx(user_id: int, asof: Optional[date] = None, db: Session = Depends(get_db)):
    """퇴사 정산 엑셀 다운로드(입사/퇴사·연도별 사용내역·발생내역·잔여, 금액 제외)."""
    from datetime import date as _date
    from fastapi.responses import StreamingResponse
    from app.services import leave_excel_service
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    if u.hire_date is None:
        raise HTTPException(status_code=400, detail="입사일이 없어 정산할 수 없습니다")
    st = acc.settlement(db, u, asof)
    usage = acc.usage_detail(db, u)
    allowance = acc.allowance_detail(db, u)
    adjust = acc.adjust_detail(db, u)
    bd = acc.legal_breakdown(u.hire_date, _date.fromisoformat(st["asof"]))
    out = leave_excel_service.build_settlement_xlsx(u, st, usage, bd, allowance, adjust)
    fname = f"leave_settlement_{u.username}_{st['asof']}.xlsx"
    return StreamingResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.post("/ensure-all", dependencies=[Depends(leave_manager)])
def ensure_all(db: Session = Depends(get_db)):
    """전 직원 연차 일괄 생성/동기화 — 자동발생을 **현재 공식으로 재계산**(force).
    (수동 조정/수당/사용 원장은 보존)."""
    cy = _cur_year()
    users = db.query(User).filter(User.hire_date.isnot(None)).all()
    g = 0
    for u in users:
        g += acc.ensure_grants(db, u, cy if u.resign_date is None else max(cy, u.resign_date.year), force=True)
        acc.sync_usage(db, u)
    return {"users": len(users), "grants_recomputed": g}
