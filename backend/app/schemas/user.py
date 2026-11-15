"""
사용자 스키마
v0.28.0
"""

from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, field_validator


def validate_password_strength(pw: str) -> str:
    """비밀번호 정책: 최소 8자 + 영문/숫자 혼합. (생성/변경/초기화 공통)"""
    if pw is None or len(pw) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다")
    has_alpha = any(c.isalpha() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    if not (has_alpha and has_digit):
        raise ValueError("비밀번호는 영문과 숫자를 모두 포함해야 합니다")
    return pw


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="로그인 ID")
    password: str = Field(..., min_length=8, description="비밀번호(8자 이상, 영문+숫자)")

    @field_validator("password")
    @classmethod
    def _v_pw(cls, v):
        return validate_password_strength(v)
    name: str = Field(..., min_length=1, max_length=100, description="표시 이름 (한글)")
    name_en: Optional[str] = Field(None, max_length=100, description="영문 이름")
    email: Optional[str] = Field(None, max_length=200)
    role: str = Field("USER", description="역할 (ADMIN/USER)")
    department: Optional[str] = Field(None, max_length=50, description="부서")
    position: Optional[str] = Field(None, max_length=50, description="직급")
    approver_id: Optional[int] = Field(None, description="기본 결재자 ID (1차)")
    approver2_id: Optional[int] = Field(None, description="기본 결재자 ID (2차)")
    leave_approver_ids: Optional[List[int]] = Field(None, description="휴가 결재선 결재자 ID 배열(순서)")
    leave_reference_ids: Optional[List[int]] = Field(None, description="휴가 참조자 ID 배열")
    hire_date: Optional[date] = Field(None, description="입사일(연차 발생 기준)")
    resign_date: Optional[date] = Field(None, description="퇴사일(연차 정산 기준)")


class UserUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    approver_id: Optional[int] = None
    approver2_id: Optional[int] = None
    leave_approver_ids: Optional[List[int]] = None
    leave_reference_ids: Optional[List[int]] = None
    hire_date: Optional[date] = None
    resign_date: Optional[date] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def _v_pw(cls, v):
        return validate_password_strength(v)


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def _v_pw(cls, v):
        return validate_password_strength(v)


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    name_en: Optional[str] = None
    email: Optional[str] = None
    role: str
    department: Optional[str] = None
    position: Optional[str] = None
    approver_id: Optional[int] = None
    approver2_id: Optional[int] = None
    leave_approver_ids: Optional[List[int]] = None
    leave_reference_ids: Optional[List[int]] = None
    hire_date: Optional[date] = None
    resign_date: Optional[date] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    permissions: List[str] = []  # RBAC 유효 권한 (v0.40.0). 와일드카드면 ["*"].
    rbac_enforced: bool = False  # v0.41.0: 서버가 enforce 모드인지(프론트 메뉴 게이팅 판단용)

    model_config = ConfigDict(from_attributes=True)


# TokenResponse에서 UserResponse 참조 해결
TokenResponse.model_rebuild()
