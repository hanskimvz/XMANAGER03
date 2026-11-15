"""
JWT 인증 유틸리티
v0.28.0
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User

# 설정 (v0.41.0: 하드코딩 제거 → settings/.env 에서 로드)
# SECRET_KEY 는 반드시 환경변수(.env)로 주입한다. 미설정 시 settings 기본값 사용.
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 60       # 1시간
REFRESH_TOKEN_EXPIRE_DAYS = 7          # 7일

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer 토큰 추출
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """현재 로그인 사용자 반환. 토큰 없으면 None (비인증 허용)"""
    if not credentials:
        return None

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """인증 필수. 토큰 없거나 유효하지 않으면 401"""
    user = get_current_user(credentials, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: User = Depends(require_auth)) -> User:
    """관리자 권한 필수. USER면 403"""
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )
    return user


def require_permission(perm: str):
    """
    특정 RBAC 권한을 요구하는 의존성 팩토리 (v0.40.0).

    ⚠️ 정의만 제공 — 기존 350개 업무 라우터에는 부착하지 않는다(차단은 다음 단계).
    향후 차단 단계에서 `Depends(require_permission("part:edit"))` 형태로 사용한다.
    와일드카드(ADMIN / is_admin 역할)는 항상 통과.
    """

    def _checker(
        user: User = Depends(require_auth),
        db: Session = Depends(get_db),
    ) -> User:
        # 지연 임포트: 순환 참조 방지
        from app.services.rbac_service import has_permission

        if not has_permission(db, user, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 작업 권한이 없습니다",
            )
        return user

    return _checker
