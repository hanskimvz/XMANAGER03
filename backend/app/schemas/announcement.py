"""회사 공지사항 스키마 (v0.50.0)."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ==================== 입력 ====================

class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=300, description="제목")
    body: str = Field(..., description="본문 HTML(TipTap)")
    is_pinned: bool = Field(False, description="상단 고정")
    target_departments: Optional[List[str]] = Field(
        None, description="대상 부서코드 목록. None/[]=전체 공개")


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    """부분 수정 — 보낸 필드만 갱신."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    body: Optional[str] = None
    is_pinned: Optional[bool] = None
    target_departments: Optional[List[str]] = None
    is_active: Optional[bool] = Field(None, description="복구/보관 토글")


# ==================== 출력 ====================

class AttachmentResponse(BaseModel):
    id: int
    original_name: str
    file_size: int
    content_type: Optional[str] = None
    download_url: str = Field(..., description="다운로드 URL")
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AnnouncementListItem(BaseModel):
    id: int
    title: str
    is_pinned: bool
    target_departments: Optional[List[str]] = None
    published_at: datetime
    is_active: bool
    created_by: int
    author_name: Optional[str] = None
    attachment_count: int = 0
    read_count: int = 0
    is_unread: bool = True  # 현재 사용자 기준
    model_config = ConfigDict(from_attributes=True)


class AnnouncementListResponse(BaseModel):
    items: List[AnnouncementListItem]
    total: int
    page: int
    size: int
    unread_total: int = 0  # 메뉴 배지용(현재 사용자 미열람 수)


class AnnouncementDetail(BaseModel):
    id: int
    title: str
    body: str
    is_pinned: bool
    target_departments: Optional[List[str]] = None
    published_at: datetime
    is_active: bool
    created_by: int
    author_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    attachments: List[AttachmentResponse] = []
    is_unread: bool = False  # 이번 열람으로 읽음 처리되기 직전 상태
    read_count: int = 0


# ==================== 읽음 영수(관리자) ====================

class ReadReceipt(BaseModel):
    user_id: int
    name: Optional[str] = None
    department: Optional[str] = None
    read_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UnreadUser(BaseModel):
    user_id: int
    name: Optional[str] = None
    department: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ReadReceiptList(BaseModel):
    announcement_id: int
    total_targeted: int  # 대상 인원 수
    read_count: int
    read: List[ReadReceipt]
    unread: List[UnreadUser]


class UnreadCountResponse(BaseModel):
    unread_total: int
