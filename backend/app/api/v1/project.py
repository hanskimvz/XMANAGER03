"""
공용 프로젝트 마스터 API 라우터 (v0.38.0)

전자결재 전용이던 프로젝트를 전사 공용 도메인으로 분리. 다른 모듈/피커가 재사용한다.
- GET  /projects       (require_auth)  활성 목록 (피커 공용)
- POST /projects       (require_auth)  즉석 추가 (일반 사용자 허용)
- GET  /projects/all   (require_admin) 비활성 포함 전체
- PUT  /projects/{id}  (require_admin) 수정
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin, require_auth
from app.models.user import User
from app.api.v1.deps import get_db, handle_service_exception
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["프로젝트"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    """ProjectService 의존성 (v0.38.0)."""
    return ProjectService(db)


@router.get("", response_model=list[ProjectResponse])
@router.get("/", response_model=list[ProjectResponse], include_in_schema=False)
def list_projects(
    actor: User = Depends(require_auth),
    service: ProjectService = Depends(get_project_service),
):
    """활성 프로젝트 목록 (모듈/피커 공용)."""
    try:
        return [ProjectResponse.model_validate(p) for p in service.list_active()]
    except Exception as e:
        handle_service_exception(e)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_project(
    data: ProjectCreate,
    actor: User = Depends(require_auth),
    service: ProjectService = Depends(get_project_service),
):
    """프로젝트 즉석 추가 (일반 사용자 허용). code 미지정 시 자동 생성."""
    try:
        return ProjectResponse.model_validate(service.create(data))
    except Exception as e:
        handle_service_exception(e)


@router.get("/all", response_model=list[ProjectResponse])
def list_projects_all(
    admin: User = Depends(require_admin),
    service: ProjectService = Depends(get_project_service),
):
    """[관리자] 비활성 포함 전체 프로젝트 목록."""
    try:
        return [ProjectResponse.model_validate(p) for p in service.list_all()]
    except Exception as e:
        handle_service_exception(e)


@router.put("/{id}", response_model=ProjectResponse)
def update_project(
    id: int,
    data: ProjectUpdate,
    admin: User = Depends(require_admin),
    service: ProjectService = Depends(get_project_service),
):
    """[관리자] 프로젝트 수정(name/is_active/sort_order)."""
    try:
        return ProjectResponse.model_validate(service.update(id, data))
    except Exception as e:
        handle_service_exception(e)
