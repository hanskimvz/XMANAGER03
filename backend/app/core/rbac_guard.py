"""
RBAC 강제 가드 (v0.41.0)

`module_guard(module)` : 라우터 레벨 의존성 팩토리(C 규칙 가드).
- `settings.RBAC_MODE` 에 따라 동작:
    disabled → 검사 안 함(기존 동작 그대로)
    observe  → 로그인 요구 + 권한 부족은 [RBAC-MISS] 로그만(차단 안 함)
    enforce  → 로그인 요구 + 권한 부족 시 403
- HTTP 메서드 + 경로 동사로 동작(action)을 추론해 `module:action` 권한을 검사.
- 와일드카드(ADMIN / is_admin 역할)는 항상 통과(has_permission 내부 처리).

approval / admin / rbac / auth 라우터는 자체 인증(A 예외)이라 이 가드를 붙이지 않는다.
계획: 전자결재_RBAC_하이브리드_개발계획.md (§2 동작 추론 규칙, §3 매핑표).
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.auth import security, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import MODULE_DEFS
from app.models.user import User

logger = logging.getLogger("rbac")

# 모듈 코드 -> 유효 동작 집합 (레지스트리 기준)
_MODULE_ACTIONS = {code: set(actions) for code, _label, actions in MODULE_DEFS}

# 경로 끝 동사 → 신규 생성(create) 으로 보는 토큰
_CREATE_NEW_VERBS = {
    "upload-excel", "upload", "import", "bulk", "import-sales-tracking",
    "create-work-order", "shipping-invoices",
}

# 경로 토큰 → 기존 레코드 상태 변경(edit) 으로 보는 토큰
_WRITE_VERBS = {
    "approve", "reject", "cancel", "confirm", "complete", "submit", "resubmit",
    "return", "withdraw", "hold", "release-hold", "release", "status", "change-status",
    "payment", "receive", "ship", "issue", "issue-with-lots", "issue-additional",
    "start", "start-production", "complete-production", "complete-inspection",
    "rollback", "restore", "activate", "deactivate", "acknowledge-modification",
    "reorder", "move", "refresh-cache", "refresh", "sync", "save", "save-all",
    "deposit", "deduct", "shipment-date", "order", "quick-complete", "correct",
}

# GET 경로가 '진짜 내보내기(리포트 생성)'인지 판단하는 힌트.
# pdf/preview/download 은 단순 읽기이므로 view 로 본다(export 권한 요구 X).
_EXPORT_ACTION_HINTS = {"export", "excel", "template"}


def _infer_action(module: str, method: str, path: str) -> str:
    """메서드 + 경로로 RBAC 동작(action)을 추론. 모듈에 없는 동작이면 가용 동작으로 폴백."""
    avail = _MODULE_ACTIONS.get(module, {"view", "create", "edit", "delete"})
    method = method.upper()
    tokens = {t for t in path.lower().replace("{", " ").replace("}", " ").split("/") if t}

    def read_fb() -> str:
        return "view" if "view" in avail else next(iter(avail), "view")

    def write_fb(cand: str) -> str:
        """쓰기 동작 폴백: 쓰기 계열만 후보. 가용한 쓰기가 없으면 cand 유지(=실재 안 함 → enforce 시 거부=fail-closed)."""
        if cand in avail:
            return cand
        for alt in ("edit", "manage", "create", "delete"):
            if alt in avail:
                return alt
        return cand  # 읽기로 다운그레이드하지 않음

    if method == "GET":
        if (tokens & _EXPORT_ACTION_HINTS) and "export" in avail:
            return "export"
        return read_fb()
    if method == "DELETE":
        return write_fb("delete")
    # POST / PUT / PATCH
    if module == "price":  # price 모듈은 create/delete 없음 → 모든 쓰기 edit
        return write_fb("edit")
    if tokens & _CREATE_NEW_VERBS:
        return write_fb("create")
    if tokens & _WRITE_VERBS:
        return write_fb("edit")
    if method == "POST":
        return write_fb("create")
    return write_fb("edit")  # PUT / PATCH


def login_guard():
    """로그인만 요구하는 모드 인식 가드(D-4: 공유 파일 다운로드 등). disabled 면 통과."""

    def _dep(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db),
    ) -> Optional[User]:
        mode = (settings.RBAC_MODE or "disabled").lower()
        if mode == "disabled":
            return None
        user = get_current_user(credentials, db)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인이 필요합니다",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    return _dep


def module_guard(module: str):
    """라우터 레벨 RBAC 가드 의존성 팩토리. main.py 에서 include_router(dependencies=[...]) 로 부착."""

    def _dep(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db),
    ) -> Optional[User]:
        # v0.47.0: 전역 RBAC_MODE 대신 '모듈별 실효 모드'(민감/토글ON 이면 enforce)
        from app.services.rbac_service import effective_mode, has_permission
        mode = effective_mode(db, module)
        if mode == "disabled":
            return None  # 검사 안 함

        # 로그인 게이트 (observe/enforce 공통 — D-2=A)
        user = get_current_user(credentials, db)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인이 필요합니다",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 권한 게이트 (와일드카드 통과는 has_permission 내부 처리)

        action = _infer_action(module, request.method, request.url.path)
        perm = f"{module}:{action}"
        if has_permission(db, user, perm):
            return user

        if mode == "observe":
            logger.warning(
                "[RBAC-MISS] user=%s(id=%s) perm=%s %s %s",
                getattr(user, "username", "?"), getattr(user, "id", "?"),
                perm, request.method, request.url.path,
            )
            return user  # 관찰 모드: 차단하지 않음
        # enforce
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 작업 권한이 없습니다",
        )

    return _dep
