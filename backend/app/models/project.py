"""
프로젝트 마스터 모델 (v0.38.0)

전자결재 전용이던 프로젝트 마스터(구 approval_projects)를 전사 공용 도메인으로
일반화한다. 다른 모듈이 이 Project 모델과 /api/v1/projects API 를 그대로 재사용한다.
(테이블은 approval_projects → projects 로 rename — 데이터/시드 보존)
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Project(Base):
    """프로젝트 마스터 (v0.38.0 공용화) — 결재 등 여러 모듈에서 선택. 관리자/일반사용자 편집·추가."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(30), unique=True, nullable=False, index=True, comment="프로젝트 코드")
    name = Column(String(100), nullable=False, comment="프로젝트 이름")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true", comment="활성 여부")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0", comment="정렬 순서")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

    def __repr__(self):
        return f"<Project(code={self.code}, name={self.name})>"
