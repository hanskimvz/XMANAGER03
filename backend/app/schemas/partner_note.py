"""
거래처 메모 스키마
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


NOTE_TYPE_LABELS = {
    "GENERAL": "일반",
    "STRATEGY": "전략",
    "RISK": "주의",
    "MEETING": "미팅",
    "INTERNAL": "내부",
}


class PartnerNoteCreate(BaseModel):
    note_type: str = Field("GENERAL", description="메모 유형")
    content: str = Field(..., min_length=1, description="메모 내용")
    is_pinned: bool = Field(False, description="상단 고정")
    created_by: Optional[str] = Field(None, description="작성자")


class PartnerNoteUpdate(BaseModel):
    note_type: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None


class PartnerNoteResponse(BaseModel):
    id: int
    partner_id: int
    note_type: str
    content: str
    is_pinned: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
