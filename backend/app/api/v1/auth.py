"""
인증 + 사용자 관리 API
v0.28.0
"""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ratelimit import login_limiter, client_key
from app.core.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    require_auth, require_admin,
)
from app.models.user import User
from app.schemas.user import (
    LoginRequest, TokenResponse, RefreshRequest,
    UserCreate, UserUpdate, UserResponse, PasswordChange, PasswordReset,
)
from app.services.rbac_service import get_user_permissions
from app.core.config import settings

router = APIRouter(tags=["인증"])


def _user_response_with_perms(db: Session, user: User) -> UserResponse:
    """UserResponse + RBAC 권한 채움 (v0.40.0). 와일드카드면 ['*']."""
    resp = UserResponse.model_validate(user)
    resp.permissions = sorted(get_user_permissions(db, user))
    resp.rbac_enforced = (settings.RBAC_MODE or "disabled").lower() == "enforce"  # v0.41.0
    return resp


# ==================== 인증 ====================

@router.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # 무차별 대입 방어: IP+ID 기준 5회 실패 시 15분 잠금
    key = client_key(request, data.username)
    locked = login_limiter.locked_for(key)
    if locked:
        raise HTTPException(status_code=429, detail=f"로그인 시도가 많아 잠시 차단되었습니다. {locked}초 후 다시 시도하세요.")

    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        login_limiter.record_fail(key)
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="비활성화된 계정입니다")

    login_limiter.record_success(key)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        user=_user_response_with_perms(db, user),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

    user = db.query(User).filter(User.id == int(payload["sub"]), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        user=_user_response_with_perms(db, user),
    )


@router.get("/auth/me", response_model=UserResponse)
def get_me(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    return _user_response_with_perms(db, user)


@router.post("/auth/change-password")
def change_password(data: PasswordChange, user: User = Depends(require_auth), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "비밀번호가 변경되었습니다"}


# ==================== 사용자 관리 (ADMIN) ====================

@router.get("/users", response_model=List[UserResponse])
def get_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at).all()


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        name=data.name,
        name_en=data.name_en,
        email=data.email,
        role=data.role,
        department=data.department,
        position=data.position,
        approver_id=data.approver_id,
        approver2_id=data.approver2_id,
        leave_approver_ids=data.leave_approver_ids,
        leave_reference_ids=data.leave_reference_ids,
        hire_date=data.hire_date,
        resign_date=data.resign_date,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, data: PasswordReset, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": f"{user.name}의 비밀번호가 초기화되었습니다"}


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="자기 자신은 삭제할 수 없습니다")
    user.is_active = False
    db.commit()
