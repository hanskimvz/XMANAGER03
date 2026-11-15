"""
부서(조직) 마스터 API 라우터 (v0.43.0, 조직도 필드 v1.04.0)

- GET    /departments       (require_auth)  활성 목록 (사용자 관리 드롭다운 등 공용)
- GET    /departments/all   (require_admin) 비활성 포함 전체 (조직관리 화면)
- POST   /departments       (require_admin) 추가
- PUT    /departments/{id}  (require_admin) 수정(코드 제외 전 필드)
- DELETE /departments/{id}  (require_admin) 삭제 (소속 사용자·하위 조직이 있으면 차단)

RBAC: 라우터 자체 require_auth/require_admin (module_guard 미부착 = A 예외).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import require_admin, require_auth
from app.core.database import get_db
from app.models.department import Department
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate

router = APIRouter(prefix="/departments", tags=["부서"])


def _responses(db: Session, rows: List[Department]) -> List[DepartmentResponse]:
    """응답 변환 — 책임자 이름과 소속 인원을 채운다."""
    counts = dict(
        db.query(User.department, func.count())
        .filter(User.department.isnot(None))
        .group_by(User.department).all()
    )
    manager_ids = {d.manager_user_id for d in rows if d.manager_user_id}
    names = {}
    if manager_ids:
        names = dict(db.query(User.id, User.name).filter(User.id.in_(manager_ids)).all())
    out = []
    for d in rows:
        item = DepartmentResponse.model_validate(d)
        item.manager_name = names.get(d.manager_user_id)
        item.member_count = int(counts.get(d.code, 0))
        out.append(item)
    return out


def _response(db: Session, dept: Department) -> DepartmentResponse:
    return _responses(db, [dept])[0]


def _clean(text: Optional[str]) -> Optional[str]:
    text = (text or "").strip()
    return text or None


def _check_parent(db: Session, parent_id: Optional[int], self_id: Optional[int] = None) -> None:
    """상위 조직 검증 — 존재해야 하고, 자기 자신·자기 하위 조직은 상위로 둘 수 없다(순환 방지)."""
    if parent_id is None:
        return
    if parent_id == self_id:
        raise HTTPException(status_code=400, detail="자기 자신을 상위 조직으로 지정할 수 없습니다")
    parents = dict(db.query(Department.id, Department.parent_id).all())
    if parent_id not in parents:
        raise HTTPException(status_code=400, detail="상위 조직을 찾을 수 없습니다")
    # 상위 조직에서 위로 거슬러 올라가다 자신을 만나면 순환
    cur, seen = parent_id, set()
    while cur is not None and cur not in seen:
        if cur == self_id:
            raise HTTPException(status_code=400, detail="하위 조직을 상위 조직으로 지정할 수 없습니다")
        seen.add(cur)
        cur = parents.get(cur)


def _check_manager(db: Session, user_id: Optional[int]) -> None:
    if user_id is None:
        return
    if db.query(User.id).filter(User.id == user_id).first() is None:
        raise HTTPException(status_code=400, detail="책임자를 찾을 수 없습니다")


@router.get("", response_model=list[DepartmentResponse])
@router.get("/", response_model=list[DepartmentResponse], include_in_schema=False)
def list_departments(actor: User = Depends(require_auth), db: Session = Depends(get_db)):
    """활성 부서 목록 (정렬순). 로그인 사용자 공용."""
    rows = (
        db.query(Department)
        .filter(Department.is_active == True)  # noqa: E712
        .order_by(Department.sort_order, Department.id)
        .all()
    )
    return _responses(db, rows)


@router.get("/all", response_model=list[DepartmentResponse])
def list_departments_all(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """[관리자] 비활성 포함 전체."""
    rows = db.query(Department).order_by(Department.sort_order, Department.id).all()
    return _responses(db, rows)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_department(data: DepartmentCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """[관리자] 부서 추가. 코드 중복 불가."""
    code = data.code.strip()
    name = data.name.strip()
    if not code or not name:
        raise HTTPException(status_code=400, detail="코드와 조직명을 입력하세요")
    if db.query(Department).filter(Department.code == code).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 부서 코드입니다")
    _check_parent(db, data.parent_id)
    _check_manager(db, data.manager_user_id)
    dept = Department(
        code=code, name=name, sort_order=data.sort_order,
        name_en=_clean(data.name_en), org_type=data.org_type,
        parent_id=data.parent_id, manager_user_id=data.manager_user_id,
        description=_clean(data.description),
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return _response(db, dept)


@router.put("/{id}", response_model=DepartmentResponse)
def update_department(id: int, data: DepartmentUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """[관리자] 부서 수정. 코드는 불변(사용자 참조 안정성)."""
    dept = db.query(Department).filter(Department.id == id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="부서를 찾을 수 없습니다")
    payload = data.model_dump(exclude_unset=True)

    # 비울 수 없는 필드 — null 은 무시
    if payload.get("name") is not None:
        name = payload["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail="조직명을 입력하세요")
        dept.name = name
    for key in ("is_active", "sort_order", "org_type"):
        if payload.get(key) is not None:
            setattr(dept, key, payload[key])

    # 비울 수 있는 필드 — 보냈으면 null 도 반영
    if "parent_id" in payload:
        _check_parent(db, payload["parent_id"], self_id=dept.id)
        dept.parent_id = payload["parent_id"]
    if "manager_user_id" in payload:
        _check_manager(db, payload["manager_user_id"])
        dept.manager_user_id = payload["manager_user_id"]
    if "name_en" in payload:
        dept.name_en = _clean(payload["name_en"])
    if "description" in payload:
        dept.description = _clean(payload["description"])

    db.commit()
    db.refresh(dept)
    return _response(db, dept)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """[관리자] 부서 삭제. 소속 사용자나 하위 조직이 있으면 차단."""
    dept = db.query(Department).filter(Department.id == id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="부서를 찾을 수 없습니다")
    in_use = db.query(User).filter(User.department == dept.code).count()
    if in_use > 0:
        raise HTTPException(
            status_code=400,
            detail=f"이 부서에 소속된 사용자가 {in_use}명 있어 삭제할 수 없습니다. 비활성화하거나 사용자 부서를 먼저 변경하세요.",
        )
    children = db.query(Department).filter(Department.parent_id == dept.id).count()
    if children > 0:
        raise HTTPException(
            status_code=400,
            detail=f"하위 조직이 {children}개 있어 삭제할 수 없습니다. 하위 조직을 먼저 옮기거나 삭제하세요.",
        )
    db.delete(dept)
    db.commit()
