"""
거래처 담당자 스키마 (v0.31.0)
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


CONTACT_ROLES = {
    "PURCHASING": "구매 담당",
    "TECHNICAL": "기술 담당",
    "SALES": "영업 담당",
    "GENERAL": "일반",
}


class ContactCreate(BaseModel):
    name: str = Field(..., max_length=100, description="담당자명")
    position: Optional[str] = Field(None, max_length=50, description="직책")
    role: Optional[str] = Field(None, max_length=20, description="역할")
    email: Optional[str] = Field(None, max_length=200)
    tel_office: Optional[str] = Field(None, max_length=50, description="사무실 전화")
    tel_mobile: Optional[str] = Field(None, max_length=50, description="휴대폰")
    is_primary: bool = Field(False, description="기본 담당자 여부")
    sort_order: int = Field(0)
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=50)
    role: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    tel_office: Optional[str] = Field(None, max_length=50)
    tel_mobile: Optional[str] = Field(None, max_length=50)
    is_primary: Optional[bool] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class ContactResponse(BaseModel):
    id: int
    partner_id: int
    name: str
    position: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    tel_office: Optional[str] = None
    tel_mobile: Optional[str] = None
    is_primary: bool = False
    sort_order: int = 0
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
