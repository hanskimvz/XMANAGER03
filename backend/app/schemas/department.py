"""부서(조직) 마스터 스키마 (v0.43.0, 조직도 필드 v1.04.0)"""

from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

OrgType = Literal["EXECUTIVE", "DIVISION", "DEPARTMENT", "TEAM"]


class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=30, description="부서 코드(영문 권장)")
    name: str = Field(..., min_length=1, max_length=50, description="부서 이름(한글)")
    sort_order: int = Field(0, description="정렬 순서")
    name_en: Optional[str] = Field(None, max_length=100, description="영문명")
    org_type: OrgType = Field("TEAM", description="조직 유형")
    parent_id: Optional[int] = Field(None, description="상위 조직 id(없으면 최상위)")
    manager_user_id: Optional[int] = Field(None, description="책임자 사용자 id")
    description: Optional[str] = Field(None, max_length=2000, description="설명")


class DepartmentUpdate(BaseModel):
    """부분 수정 — 보낸 필드만 갱신. 상위 조직/책임자/영문명/설명은 null 을 보내면 비운다."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    name_en: Optional[str] = Field(None, max_length=100)
    org_type: Optional[OrgType] = None
    parent_id: Optional[int] = None
    manager_user_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=2000)


class DepartmentResponse(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool
    sort_order: int
    created_at: Optional[datetime] = None
    name_en: Optional[str] = None
    org_type: str = "TEAM"
    parent_id: Optional[int] = None
    manager_user_id: Optional[int] = None
    manager_name: Optional[str] = None  # 책임자 이름(조회 시 채움)
    description: Optional[str] = None
    member_count: int = 0               # 소속 사용자 수(users.department == code)

    model_config = ConfigDict(from_attributes=True)
