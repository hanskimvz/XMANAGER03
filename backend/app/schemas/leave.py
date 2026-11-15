"""연차 관리 스키마 (v0.45.0)."""
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict


class LeaveYearSummary(BaseModel):
    fiscal_year: int
    carried_in: float
    granted: float
    used: float
    allowance_paid: float
    adjust: float
    remaining: float


class LeaveLedgerEntry(BaseModel):
    id: int
    fiscal_year: int
    entry_type: str
    amount: float
    event_date: Optional[date] = None
    source_type: str
    source_doc_id: Optional[int] = None
    memo: Optional[str] = None
    voided: bool = False  # 취소로 무효화된 행(빗금 표시, 잔여 제외)
    created_at: Optional[datetime] = None
    # 표시용(서버 계산): 휴가구분 / 날짜·기간 / 비고
    kind_label: str = ""     # 휴가구분: 종일휴가/오전반차/오후반차/경조휴가 등(부여·조정은 공란)
    date_display: str = ""   # 사용기간(날짜 또는 기간)
    memo_label: str = ""     # 비고: 휴가부여 / 관리자 조정 · 사유 / 경조 사유(조모상) 등
    admin_only: bool = False  # (미사용) 하위호환 유지
    model_config = ConfigDict(from_attributes=True)


class LeaveOverviewRow(BaseModel):
    user_id: int
    username: str
    name: str
    department: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[date] = None
    resign_date: Optional[date] = None
    current_year: int
    current_remaining: float
    has_hire_date: bool
    is_safety_officer: bool = False  # 산업기능요원 → 입사일 기준 발생


class SafetyOfficerUpdate(BaseModel):
    is_safety_officer: bool = Field(..., description="산업기능요원 여부(True=입사일 기준 연차)")


class LeaveDetail(BaseModel):
    user_id: int
    name: str
    hire_date: Optional[date] = None
    resign_date: Optional[date] = None
    current_year: int
    current_remaining: float
    years: List[LeaveYearSummary]
    ledger: List[LeaveLedgerEntry]


class EmploymentUpdate(BaseModel):
    hire_date: Optional[date] = Field(None, description="입사일")
    resign_date: Optional[date] = Field(None, description="퇴사일(재직중=null)")


class AdjustRequest(BaseModel):
    fiscal_year: int
    amount: float = Field(..., description="+ 추가 / − 차감")
    memo: str = Field(..., min_length=1, description="조정 사유(필수)")


class ManualUsageRequest(BaseModel):
    """과거에 누락된 휴가 사용 기록을 날짜와 함께 기입(백필)."""
    event_date: date = Field(..., description="실제 휴가 사용일")
    days: float = Field(..., gt=0, description="사용 일수(0.5 단위 가능)")
    memo: Optional[str] = Field(None, description="비고(예: 누락분 소급 기입)")


class CompanyWideLeaveRequest(BaseModel):
    """회사 전체 휴가 시행(전 재직자 일괄 차감, 일부 제외 가능)."""
    event_date: date = Field(..., description="회사 전체 휴가일")
    days: float = Field(1.0, gt=0, description="차감 일수(기본 1일)")
    memo: str = Field(..., min_length=1, description="사유(예: 창립기념일 휴무)")
    exclude_user_ids: List[int] = Field(default_factory=list, description="제외할 사용자 id 목록")


class AllowanceRequest(BaseModel):
    fiscal_year: int
    days: float = Field(..., gt=0, description="연차수당 지급 일수")
    memo: Optional[str] = Field(None, description="비고")


class SettlementResponse(BaseModel):
    asof: str
    hire_date: Optional[str] = None
    legal_entitlement: float
    fiscal_granted: float
    adjust: float = 0.0
    used: float
    allowance_paid: float
    unsettled_days: float
    note: str
