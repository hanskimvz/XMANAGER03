"""
공용 프로젝트 마스터 서비스 (v0.38.0)

전자결재 전용이던 프로젝트 마스터를 전사 공용 도메인으로 분리.
- list_active / list_all: 피커·관리 목록 (읽기 전용)
- create: 일반 사용자 즉석 추가 허용. code 미지정 시 자동 생성.
- update: 관리자용 name/is_active/sort_order 수정.

트랜잭션 경계: 쓰기 메서드는 단일 commit, 예외 시 rollback 후 도메인 예외 재발생.
"""

import re
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleException, NotFoundException
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """공용 프로젝트 마스터 서비스 (자체 트랜잭션 경계)."""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 읽기 ====================

    def list_active(self) -> List[Project]:
        """활성 프로젝트 목록(정렬 순서). 읽기 전용."""
        return (
            self.db.query(Project)
            .filter(Project.is_active == True)
            .order_by(Project.sort_order, Project.id)
            .all()
        )

    def list_all(self) -> List[Project]:
        """비활성 포함 전체 프로젝트 목록. 읽기 전용."""
        return (
            self.db.query(Project)
            .order_by(Project.sort_order, Project.id)
            .all()
        )

    # ==================== 내부 유틸 ====================

    @staticmethod
    def _slugify(name: str) -> str:
        """name 기반 코드 후보 슬러그(영숫자 대문자, 최대 24자). 비면 'PRJ'."""
        slug = re.sub(r"[^A-Za-z0-9]+", "_", (name or "").strip()).strip("_").upper()
        slug = slug[:24]
        return slug or "PRJ"

    def _auto_code(self, name: str) -> str:
        """code 미지정 시 자동 생성.

        1순위: name 슬러그. 충돌 시 슬러그+숫자(2,3,...).
        슬러그가 의미 없으면(PRJ) 'PRJ'+(max id+1) 형태로 폴백.
        """
        base = self._slugify(name)
        if base == "PRJ":
            max_id = self.db.query(Project.id).order_by(Project.id.desc()).first()
            seq = (max_id[0] + 1) if max_id else 1
            base = f"PRJ{seq}"
        candidate = base
        n = 1
        while self.db.query(Project.id).filter(Project.code == candidate).first():
            n += 1
            candidate = f"{base}{n}"
        return candidate

    # ==================== 쓰기 ====================

    def create(self, data: ProjectCreate) -> Project:
        """프로젝트 생성 — 일반 사용자 즉석 추가 허용.

        code 미지정/공백이면 자동 생성. code 중복이면 BusinessRuleException. 단일 commit.
        """
        try:
            code = (data.code or "").strip()
            name = (data.name or "").strip()
            if not code:
                # 이름 앞에 '[코드]' 또는 '(코드)'가 붙어 있으면 그걸 코드로 쓰고 이름에서 제거
                # (그룹웨어 습관 '[E240003] 글로벌방위~' / '[연구소] 기자재' → code + 순수 이름)
                m = re.match(r"^[\[(]\s*([^\[\]()]{1,24}?)\s*[\])]\s*(.+)$", name)
                if m:
                    raw = m.group(1).strip()
                    code = raw.upper() if raw.isascii() else raw  # 영문 코드는 대문자화, 한글은 그대로
                    name = m.group(2).strip()
                else:
                    code = self._auto_code(name)
            proj = Project(
                code=code,
                name=name,
                sort_order=data.sort_order if data.sort_order is not None else 0,
            )
            self.db.add(proj)
            self.db.commit()
            self.db.refresh(proj)
            return proj
        except IntegrityError:
            self.db.rollback()
            raise BusinessRuleException(
                f"이미 존재하는 프로젝트 코드입니다: {data.code}",
                rule="PROJECT_CODE_DUPLICATE",
            )
        except Exception:
            self.db.rollback()
            raise

    def update(self, project_id: int, data: ProjectUpdate) -> Project:
        """[관리자] 프로젝트 수정(name/is_active/sort_order). 단일 commit."""
        try:
            proj = (
                self.db.query(Project)
                .filter(Project.id == project_id)
                .first()
            )
            if not proj:
                raise NotFoundException("프로젝트", project_id)
            if data.name is not None:
                proj.name = data.name
            if data.is_active is not None:
                proj.is_active = data.is_active
            if data.sort_order is not None:
                proj.sort_order = data.sort_order
            self.db.commit()
            self.db.refresh(proj)
            return proj
        except Exception:
            self.db.rollback()
            raise
