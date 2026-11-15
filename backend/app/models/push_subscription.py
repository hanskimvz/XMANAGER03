"""
웹푸시 구독 (v0.59.0)
브라우저(PushManager)가 발급한 구독 정보를 사용자별로 저장. 알림 발생 시 이 구독으로
서버가 Web Push(pywebpush)를 발송 → 앱이 닫혀 있어도 OS 알림이 뜬다.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(String(500), nullable=False, unique=True, index=True, comment="푸시 서비스 endpoint")
    p256dh = Column(String(200), nullable=False, comment="구독 공개키")
    auth = Column(String(100), nullable=False, comment="구독 auth secret")
    user_agent = Column(String(300), nullable=True, comment="구독 기기 UA")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
