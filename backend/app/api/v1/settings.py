"""
앱 설정 API (v0.49.0) — A 예외 라우터(자체 인증)

- 지출결의서 기본 집행 담당(disbursement_approvers):
    GET  /settings/disbursement-approvers  (require_auth)  — 작성 화면 자동채움용(목록 공용)
    PUT  /settings/disbursement-approvers  (require_admin) — 관리자 지정/변경
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import require_auth, require_admin
from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["설정"])

_KEY_DISB = "disbursement_approvers"
_KEY_BANK = "company_bank_accounts"

# 설정 미지정 시 기본 시드(기존 하드코딩 USD 외화계좌) — 관리자가 화면에서 수정
_DEFAULT_BANK_ACCOUNTS = [
    {
        "currency": "USD",
        "bank_name": "KEB HANA BANK, HEAD OFFICE",
        "bank_address": "35, EULJI-RO, JUNG-GU, SEOUL, KOREA",
        "swift_code": "KOEXKRSE",
        "account_name": "XBEAMTECH CO., LTD.",
        "account_number": "332-910005-81138",
        "is_default": True,
    },
]


def _get_setting(db: Session, key: str):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row else None


def _set_setting(db: Session, key: str, value):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


class DisbApproverItem(BaseModel):
    id: int
    name: str
    username: str
    position: str | None = None
    department: str | None = None


class DisbApproversResponse(BaseModel):
    approvers: List[DisbApproverItem]


class DisbApproversUpdate(BaseModel):
    user_ids: List[int]


def _resolve_approvers(db: Session) -> List[DisbApproverItem]:
    ids = _get_setting(db, _KEY_DISB) or []
    if not isinstance(ids, list):
        ids = []
    out: List[DisbApproverItem] = []
    for uid in ids:  # 저장된 순서 유지
        u = db.query(User).filter(User.id == uid, User.is_active == True).first()  # noqa: E712
        if u:
            out.append(DisbApproverItem(id=u.id, name=u.name, username=u.username,
                                        position=u.position, department=u.department))
    return out


@router.get("/disbursement-approvers", response_model=DisbApproversResponse)
def get_disbursement_approvers(actor: User = Depends(require_auth), db: Session = Depends(get_db)):
    """지출결의서 기본 집행 담당(순서대로). 작성 시 결재선 자동채움에 사용."""
    return DisbApproversResponse(approvers=_resolve_approvers(db))


@router.put("/disbursement-approvers", response_model=DisbApproversResponse)
def set_disbursement_approvers(data: DisbApproversUpdate, admin: User = Depends(require_admin),
                               db: Session = Depends(get_db)):
    """[관리자] 집행 담당 지정/변경. user_ids 순서 = 지출결의서 결재선 순서."""
    # 유효한 활성 사용자만, 입력 순서 보존(중복 제거)
    seen = set()
    clean: List[int] = []
    for uid in data.user_ids:
        if uid in seen:
            continue
        if db.query(User).filter(User.id == uid, User.is_active == True).first():  # noqa: E712
            seen.add(uid)
            clean.append(uid)
    _set_setting(db, _KEY_DISB, clean)
    return DisbApproversResponse(approvers=_resolve_approvers(db))


# ==================== 회사 은행 계좌(통화별) ====================

class CompanyBankAccount(BaseModel):
    currency: str = Field(..., max_length=10, description="통화 코드(USD/EUR/KRW 등)")
    bank_name: Optional[str] = None
    bank_address: Optional[str] = None
    swift_code: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    is_default: bool = False


class CompanyBankAccountsResponse(BaseModel):
    accounts: List[CompanyBankAccount]


class CompanyBankAccountsUpdate(BaseModel):
    accounts: List[CompanyBankAccount]


def _resolve_bank_accounts(db: Session) -> List[dict]:
    val = _get_setting(db, _KEY_BANK)
    return val if isinstance(val, list) and val else list(_DEFAULT_BANK_ACCOUNTS)


@router.get("/company-bank-accounts", response_model=CompanyBankAccountsResponse)
def get_company_bank_accounts(actor: User = Depends(require_auth), db: Session = Depends(get_db)):
    """회사 은행 계좌(통화별). 문서 작성 시 통화에 맞는 계좌 자동채움에 사용."""
    return CompanyBankAccountsResponse(accounts=[CompanyBankAccount(**a) for a in _resolve_bank_accounts(db)])


@router.put("/company-bank-accounts", response_model=CompanyBankAccountsResponse)
def set_company_bank_accounts(data: CompanyBankAccountsUpdate, admin: User = Depends(require_admin),
                              db: Session = Depends(get_db)):
    """[관리자] 통화별 회사 계좌 저장. 통장이 바뀌면 여기서 수정하면 신규 문서에 반영됨."""
    clean: List[dict] = []
    default_idx = -1
    for a in data.accounts:
        d = a.model_dump()
        d["currency"] = (d.get("currency") or "").strip().upper()
        if not d["currency"]:
            continue
        if d.get("is_default") and default_idx < 0:
            default_idx = len(clean)
        else:
            d["is_default"] = False
        clean.append(d)
    # 기본계좌 지정이 없으면 첫 계좌를 기본으로
    if clean and default_idx < 0:
        clean[0]["is_default"] = True
    _set_setting(db, _KEY_BANK, clean)
    return CompanyBankAccountsResponse(accounts=[CompanyBankAccount(**a) for a in clean])
