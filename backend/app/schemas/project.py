"""
공용 프로젝트 마스터 Pydantic 스키마 (v0.38.0)

전자결재 전용이던 프로젝트 스키마를 전사 공용으로 분리. 응답은 from_attributes.
- 일반 사용자 즉석 추가: ProjectCreate.code 는 선택(미지정 시 서비스에서 자동 생성).
- 수정(관리자): ProjectUpdate.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProjectResponse(BaseModel):
    """프로젝트 응답"""
    id: int
    code: str
    name: str
    is_active: bool = True
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    """프로젝트 생성 — 일반 사용자 즉석 추가 허용. code 미지정 시 자동 생성."""
    code: Optional[str] = Field(None, max_length=30, description="프로젝트 코드(미지정 시 자동 생성)")
    name: str = Field(..., max_length=100, description="프로젝트 이름")
    sort_order: int = Field(0, description="정렬 순서")


class ProjectUpdate(BaseModel):
    """프로젝트 수정(관리자)"""
    name: Optional[str] = Field(None, max_length=100, description="프로젝트 이름")
    is_active: Optional[bool] = Field(None, description="활성 여부")
    sort_order: Optional[int] = Field(None, description="정렬 순서")
