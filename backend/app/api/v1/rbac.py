"""
RBAC 관리 API (v0.40.0)

가산적(additive) 관리 화면용 — 모두 require_admin.
- 권한 레지스트리 조회
- 역할 CRUD + 역할 권한 교체
- 사용자 역할 배정(교체)

기존 업무 엔드포인트에는 권한 검사를 부착하지 않는다(차단은 다음 단계).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_admin
from app.core.permissions import MODULE_DEFS, MODULE_LABELS, ACTION_LABELS
from app.models.user import User
from app.models.rbac import Role, Permission, RolePermission, UserRole

admin_router = APIRouter(prefix="/admin", tags=["RBAC-관리자"])


# ==================== 스키마 ====================

class RoleCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    sort_order: Optional[int] = 0


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class RolePermissionsUpdate(BaseModel):
    permission_codes: List[str] = Field(default_factory=list)


class UserRolesUpdate(BaseModel):
    role_ids: List[int] = Field(default_factory=list)


# ==================== 직렬화 ====================

def _serialize_role(db: Session, role: Role) -> dict:
    codes = [
        rp.permission.code
        for rp in db.query(RolePermission)
        .filter(RolePermission.role_id == role.id)
        .all()
        if rp.permission is not None
    ]
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "is_admin": role.is_admin,
        "sort_order": role.sort_order,
        "permission_codes": sorted(codes),
    }


# ==================== 권한 레지스트리 ====================

@admin_router.get("/permissions")
def list_permissions(admin: User = Depends(require_admin)):
    """전체 권한을 모듈별로 그룹화하여 반환."""
    groups = []
    for module, label, actions in MODULE_DEFS:
        groups.append(
            {
                "module": module,
                "label": label,
                "actions": [
                    {
                        "code": f"{module}:{action}",
                        "action": action,
                        "label": f"{label} {ACTION_LABELS.get(action, action)}",
                    }
                    for action in actions
                ],
            }
        )
    return groups


# ==================== 역할 ====================

@admin_router.get("/roles")
def list_roles(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    roles = db.query(Role).order_by(Role.sort_order, Role.id).all()
    return [_serialize_role(db, r) for r in roles]


@admin_router.post("/roles", status_code=201)
def create_role(data: RoleCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(Role).filter(Role.code == data.code).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 역할 코드입니다")
    role = Role(
        code=data.code,
        name=data.name,
        description=data.description,
        sort_order=data.sort_order or 0,
        is_system=False,
        is_admin=False,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return _serialize_role(db, role)


@admin_router.put("/roles/{role_id}")
def update_role(role_id: int, data: RoleUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="역할을 찾을 수 없습니다")
    # is_system 역할도 이름/설명/정렬은 수정 가능, 코드는 어떤 역할이든 변경 금지(스키마에 code 없음).
    payload = data.model_dump(exclude_unset=True)
    for key in ("name", "description", "sort_order"):
        if key in payload and payload[key] is not None:
            setattr(role, key, payload[key])
    db.commit()
    db.refresh(role)
    return _serialize_role(db, role)


@admin_router.delete("/roles/{role_id}", status_code=204)
def delete_role(role_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="역할을 찾을 수 없습니다")
    if role.is_system:
        raise HTTPException(status_code=400, detail="시스템 기본 역할은 삭제할 수 없습니다")
    db.delete(role)  # role_permissions / user_roles 는 CASCADE
    db.commit()


@admin_router.put("/roles/{role_id}/permissions")
def replace_role_permissions(
    role_id: int,
    data: RolePermissionsUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """역할 권한 전체 교체. is_admin 역할은 와일드카드라 변경 불필요."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="역할을 찾을 수 없습니다")
    if role.is_admin:
        return {
            "message": "전체 권한(와일드카드) 역할은 권한 설정이 불필요합니다",
            "role_id": role.id,
            "is_admin": True,
        }

    # 코드 검증 + permission_id 조회
    perms = db.query(Permission).filter(Permission.code.in_(data.permission_codes)).all()
    found = {p.code: p.id for p in perms}
    unknown = [c for c in data.permission_codes if c not in found]
    if unknown:
        raise HTTPException(status_code=400, detail=f"알 수 없는 권한 코드: {', '.join(unknown)}")

    # 기존 전체 삭제 후 재삽입(중복 제거)
    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    for pid in {found[c] for c in data.permission_codes}:
        db.add(RolePermission(role_id=role.id, permission_id=pid))
    db.commit()
    db.refresh(role)
    return _serialize_role(db, role)


# ==================== 사용자 역할 배정 ====================

@admin_router.get("/users/{user_id}/roles")
def get_user_roles(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    role_ids = [ur.role_id for ur in db.query(UserRole).filter(UserRole.user_id == user_id).all()]
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []
    return {
        "user_id": user_id,
        "role_ids": role_ids,
        "roles": [_serialize_role(db, r) for r in roles],
    }


@admin_router.put("/users/{user_id}/roles")
def replace_user_roles(
    user_id: int,
    data: UserRolesUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """사용자 역할 전체 교체."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    valid_ids = {r.id for r in db.query(Role).filter(Role.id.in_(data.role_ids)).all()}
    unknown = [rid for rid in data.role_ids if rid not in valid_ids]
    if unknown:
        raise HTTPException(status_code=400, detail=f"알 수 없는 역할 ID: {unknown}")

    db.query(UserRole).filter(UserRole.user_id == user_id).delete()
    for rid in set(data.role_ids):
        db.add(UserRole(user_id=user_id, role_id=rid))
    db.commit()

    role_ids = [ur.role_id for ur in db.query(UserRole).filter(UserRole.user_id == user_id).all()]
    return {"user_id": user_id, "role_ids": role_ids}


# ==================== 모듈별 enforce 토글 (v0.47.0) ====================

@admin_router.get("/module-policy")
def get_module_policy(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """모듈별 권한 강제(enforce) 상태 + 전역 모드."""
    from app.services.rbac_service import list_module_policy
    from app.core.config import settings
    return {
        "global_mode": (settings.RBAC_MODE or "disabled").lower(),
        "modules": list_module_policy(db),
    }


@admin_router.put("/module-policy/{module}")
def set_module_policy(module: str, enforced: bool, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """모듈 enforce 토글(민감 모듈은 변경 불가). enforced=true/false 쿼리."""
    from app.services.rbac_service import set_module_policy as _set, SENSITIVE_MODULES, TOGGLE_MODULES, list_module_policy
    if module in SENSITIVE_MODULES:
        raise HTTPException(status_code=400, detail="민감 모듈은 항상 보호되어 변경할 수 없습니다")
    if module not in TOGGLE_MODULES:
        raise HTTPException(status_code=400, detail=f"토글 불가 모듈: {module}")
    _set(db, module, enforced)
    from app.core.config import settings
    return {"global_mode": (settings.RBAC_MODE or "disabled").lower(), "modules": list_module_policy(db)}
