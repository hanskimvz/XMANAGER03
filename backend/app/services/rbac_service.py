"""
RBAC 서비스 (v0.40.0)

가산적(additive) 토대:
- 부팅 동기화(sync_permissions / ensure_default_role_grants)
- 권한 판정 유틸(get_user_permissions / has_permission)

기존 업무 엔드포인트에는 적용하지 않는다(차단은 다음 단계).
"""

from typing import Set

from sqlalchemy.orm import Session

from app.core.permissions import (
    ALL_PERMISSIONS,
    ALL_PERMISSION_CODES,
    DEFAULT_EMPLOYEE_PERMISSIONS,
    MODULE_LABELS,
    WILDCARD,
)
from app.core.config import settings
from app.models.rbac import Role, Permission, RolePermission, UserRole, RbacModulePolicy
from app.models.user import User


# ==================== 부팅 동기화 ====================

def sync_permissions(db: Session) -> int:
    """
    레지스트리(ALL_PERMISSIONS) 기준으로 permissions 테이블을 upsert 한다.
    - 없는 코드: insert
    - 이미 있는 코드: module/action/label 최신화(라벨 변경 반영)
    Returns: 새로 삽입된 권한 수.
    """
    existing = {p.code: p for p in db.query(Permission).all()}
    inserted = 0
    for spec in ALL_PERMISSIONS:
        perm = existing.get(spec["code"])
        if perm is None:
            db.add(
                Permission(
                    code=spec["code"],
                    module=spec["module"],
                    action=spec["action"],
                    label=spec["label"],
                )
            )
            inserted += 1
        else:
            perm.module = spec["module"]
            perm.action = spec["action"]
            perm.label = spec["label"]
    db.commit()
    return inserted


def ensure_default_role_grants(db: Session) -> int:
    """
    EMPLOYEE 역할에 기본 권한을 부여한다(없을 때만 추가, 기존 부여는 건드리지 않음).
    Returns: 새로 부여된 권한 수.
    """
    role = db.query(Role).filter(Role.code == "EMPLOYEE").first()
    if role is None:
        return 0

    # EMPLOYEE 가 이미 가진 권한 코드
    existing_codes = {
        rp.permission.code
        for rp in db.query(RolePermission)
        .filter(RolePermission.role_id == role.id)
        .all()
        if rp.permission is not None
    }

    # 코드 -> permission_id 매핑
    perm_by_code = {
        p.code: p.id
        for p in db.query(Permission)
        .filter(Permission.code.in_(DEFAULT_EMPLOYEE_PERMISSIONS))
        .all()
    }

    granted = 0
    for code in DEFAULT_EMPLOYEE_PERMISSIONS:
        if code in existing_codes:
            continue
        pid = perm_by_code.get(code)
        if pid is None:
            continue
        db.add(RolePermission(role_id=role.id, permission_id=pid))
        granted += 1
    db.commit()
    return granted


# ==================== 표준 역할 시드 (v0.41.0) ====================

def _crud(module: str) -> list:
    return [f"{module}:view", f"{module}:create", f"{module}:edit", f"{module}:delete"]


# 표준 역할 초안 (회사가 관리자 화면에서 자유롭게 수정). code -> (name, sort_order, [권한코드])
# is_system=False 로 생성 → 관리자가 권한/이름 수정·삭제 가능. 이미 존재하면 건드리지 않음(idempotent).

# FULL(전 서비스 사용) 역할용 권한: user/system/leave(전담 관리) 제외한 전 업무 권한.
# 현재 운영(영업팀)은 사실상 무제한 사용 중 → enforce 전환 시 capability 보존(무중단)용.
# leave(연차 관리)는 경영지원팀 전담이라 FULL 에서 제외(STAFF_MGMT 에만 부여).
# announcement 쓰기(create/edit/delete/manage)도 경영지원팀 전담 → FULL 에서 제외(view 만 별도 부여).
_ANNOUNCE_WRITE = {"announcement:create", "announcement:edit", "announcement:delete", "announcement:manage"}
# 특정인에게만 따로 주는 권한 — FULL 등 묶음 역할에 자동 포함하지 않음(전용 역할로만 부여)
_SPECIAL_GRANTS = {"sales:ci_delete"}
_FULL_PERMS = sorted(
    c for c in ALL_PERMISSION_CODES
    if not c.startswith(("user:", "system:", "leave:")) and c not in _ANNOUNCE_WRITE and c not in _SPECIAL_GRANTS
)

STANDARD_ROLES = {
    # === 단계적 도입(coarse) 2역할 — 전자결재 우선 도입용 ===
    # APPROVAL_ONLY: 전자결재만. 다른 모듈은 권한 0 → enforce에서 메뉴 숨김 + API 403.
    #   (전자결재 라우터는 A 예외라 module_guard 미적용 → 결재는 동작. 메뉴 노출 위해 approval:view 필요)
    "APPROVAL_ONLY": (
        "전자결재 전용", 1,
        ["dashboard:view", "approval:view", "approval:create", "approval:approve", "announcement:view"],
    ),
    # FULL: 전자결재 + 전 업무. 현재 영업팀 등 기존 사용자에 부여(capability 보존).
    "FULL": (
        "전체 사용(영업팀 등)", 2,
        _FULL_PERMS,
    ),
    "MANAGER": (
        "부서장", 5,
        [
            "dashboard:view", "code:view", "part:view", "bom:view", "partner:view",
            "inventory:view", "purchase:view", "workorder:view", "production:view", "production_simple:view",
            "price:view", "price:edit", "sales:view", "sales:export", "sales_activity:view",
            "approval:view", "approval:create", "approval:approve", "project:view", "project:manage",
            "user:view", "announcement:view",
            "part:create", "part:edit", "bom:create", "bom:edit",
            "partner:create", "partner:edit", "partner:delete",
            "inventory:create", "inventory:edit", "purchase:create", "purchase:edit", "purchase:delete",
            "workorder:create", "workorder:edit", "production:create", "production:edit",
            "sales:create", "sales:edit", "sales:delete",
            "sales_activity:create", "sales_activity:edit", "sales_activity:delete",
        ],
    ),
    "STAFF_SALES": (
        "영업팀", 11,
        [
            "dashboard:view", "approval:view", "approval:create",
            "code:view", "part:view", "bom:view", "inventory:view", "price:view", "purchase:view",
            *_crud("sales"), "sales:export",
            *_crud("sales_activity"), *_crud("partner"),
            "project:view", "project:manage", "announcement:view",
        ],
    ),
    "STAFF_PROD": (
        "생산팀", 12,
        [
            "dashboard:view", "approval:view", "approval:create",
            "partner:view", "price:view", "project:view",
            *_crud("code"),  # 생산팀 = BOM/코드 관리자 → 코드관리 메뉴/화면 노출(code:edit)
            *_crud("production"), *_crud("workorder"), *_crud("inventory"),
            *_crud("bom"), *_crud("part"),
            "production_simple:view",  # 간편처리 탭
            "announcement:view",
        ],
    ),
    "STAFF_MGMT": (
        "경영지원", 13,
        [
            "dashboard:view", "approval:view", "approval:create", "approval:approve",
            "part:view", "bom:view", "inventory:view", "sales:view", "user:view",
            *_crud("purchase"), "price:view", "price:edit", *_crud("partner"),
            "project:view", "project:manage",
            "leave:manage",  # v0.45.0 연차 관리 전담(view 액션 없음 — 전 화면 manage 게이팅)
            "announcement:view", "announcement:manage",  # v0.50.0 공지 작성/관리 전담(경영지원)
        ],
    ),
    # 추가 지정용 역할: 기존 역할은 그대로 두고 이 역할을 더 붙이면 CI 삭제만 가능해진다.
    # (CI 삭제 시 생산요청 품목의 CI 발행 수량은 자동 복원 — SalesDocumentService._release_production_ci_quantity)
    "CI_DELETE": (
        "CI 삭제", 20,
        ["sales:ci_delete"],
    ),
}


def ensure_standard_roles(db: Session) -> int:
    """
    표준 역할(부서장/영업/생산/경영지원)을 '없을 때만' 생성하고 권한을 부여한다.
    이미 존재하는 역할은 권한을 건드리지 않음(관리자 수정 존중). Returns: 새로 만든 역할 수.
    """
    perm_by_code = {p.code: p.id for p in db.query(Permission).all()}
    created = 0
    for code, (name, sort_order, perm_codes) in STANDARD_ROLES.items():
        if db.query(Role).filter(Role.code == code).first() is not None:
            continue
        role = Role(code=code, name=name, is_system=False, is_admin=False, sort_order=sort_order)
        db.add(role)
        db.flush()  # role.id 확보
        seen = set()
        for pc in perm_codes:
            pid = perm_by_code.get(pc)
            if pid is None or pid in seen:
                continue
            seen.add(pid)
            db.add(RolePermission(role_id=role.id, permission_id=pid))
        created += 1
    db.commit()
    return created


# ==================== 권한 판정 ====================

def _user_has_wildcard(db: Session, user: User) -> bool:
    """사용자가 와일드카드(전체 권한)인지 판정. is_admin 역할 보유 또는 user.role=='ADMIN'."""
    if getattr(user, "role", None) == "ADMIN":
        return True
    admin_role = (
        db.query(UserRole)
        .join(Role, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id, Role.is_admin == True)  # noqa: E712
        .first()
    )
    return admin_role is not None


def get_user_permissions(db: Session, user: User) -> Set[str]:
    """
    사용자의 유효 권한 집합을 반환한다.
    - 와일드카드(is_admin 역할 보유 또는 user.role=='ADMIN')이면 {"*"}.
    - 그 외에는 보유 역할들의 role_permissions 합집합.
    """
    if user is None:
        return set()

    if _user_has_wildcard(db, user):
        return {WILDCARD}

    codes = {
        rp.permission.code
        for rp in (
            db.query(RolePermission)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .filter(UserRole.user_id == user.id)
            .all()
        )
        if rp.permission is not None
    }
    return codes


def has_permission(db: Session, user: User, perm: str) -> bool:
    """
    사용자가 특정 권한을 가지는지 판정(와일드카드 고려).
    """
    if user is None:
        return False
    perms = get_user_permissions(db, user)
    if WILDCARD in perms:
        return True
    return perm in perms


# ==================== 모듈별 enforce 토글 (v0.47.0) ====================
# 전역 RBAC_MODE 와 별개로 '모듈 단위'로 권한 강제를 켜고 끈다(관리자 UI).
# 민감 모듈은 코드 상수로 항상 enforce(토글 불가) — 새 기능 도입 시 즉시 보호.
SENSITIVE_MODULES = {"leave"}  # 연차(인사). admin/user/system 은 라우터 자체 require_admin 로 별도 보호.
# 관리자가 켜고 끌 수 있는 업무 모듈(module_guard 부착 모듈)
TOGGLE_MODULES = [
    "dashboard", "code", "part", "bom", "partner", "inventory",
    "purchase", "workorder", "production", "price", "sales", "sales_activity",
]


def effective_mode(db: Session, module: str) -> str:
    """모듈의 실효 모드. 민감/토글ON 이면 'enforce', 아니면 전역 RBAC_MODE."""
    if module in SENSITIVE_MODULES:
        return "enforce"
    row = db.query(RbacModulePolicy).filter(RbacModulePolicy.module == module).first()
    if row is not None and row.enforced:
        return "enforce"
    return (settings.RBAC_MODE or "disabled").lower()


def set_module_policy(db: Session, module: str, enforced: bool) -> None:
    """모듈 enforce 토글 저장(민감 모듈은 변경 불가)."""
    if module in SENSITIVE_MODULES:
        return
    row = db.query(RbacModulePolicy).filter(RbacModulePolicy.module == module).first()
    if row is None:
        row = RbacModulePolicy(module=module)
        db.add(row)
    row.enforced = bool(enforced)
    db.commit()


def list_module_policy(db: Session) -> list:
    """모듈별 정책 목록(민감=locked on / 토글 모듈)."""
    enforced = {p.module for p in db.query(RbacModulePolicy).filter(RbacModulePolicy.enforced == True).all()}  # noqa: E712
    out = []
    for m in sorted(SENSITIVE_MODULES):
        out.append({"module": m, "label": MODULE_LABELS.get(m, m), "enforced": True, "locked": True})
    for m in TOGGLE_MODULES:
        out.append({"module": m, "label": MODULE_LABELS.get(m, m), "enforced": m in enforced, "locked": False})
    return out
