"""인앱 알림 스키마 (v0.54.0)"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class NotificationItem(BaseModel):
    id: int
    type: str
    title: str
    message: Optional[str] = None
    link: Optional[str] = None
    related_type: Optional[str] = None
    related_id: Optional[int] = None
    actor_name: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationItem]
    total: int
    unread: int


class UnreadCountResponse(BaseModel):
    count: int
