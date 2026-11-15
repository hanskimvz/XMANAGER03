"""
인앱 알림 모델 (v0.54.0)

수신자별 1행 = 1알림. 브로드캐스트(공지)와 달리 대상이 명확해 읽음상태를 행 자체에 둔다.
전자결재 상신/승인/반려/참조에서 발생하며, 추후 다른 도메인(생산요청 등)으로 확장 가능하도록
type + related_type/related_id + link 를 일반화해 둔다.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Notification(Base):
    """인앱 알림 (수신자 1인 기준 1행).

    type 예시:
    - APPROVAL_REQUEST   : 내 결재 차례 (상신/다음 단계)
    - APPROVAL_APPROVED  : 내가 기안한 문서 최종 승인
    - APPROVAL_REJECTED  : 내가 기안한 문서 반려
    - APPROVAL_REFERENCE : 참조자로 지정됨
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True, comment="수신자 user id")
    type = Column(String(40), nullable=False, index=True, comment="알림 유형")
    title = Column(String(200), nullable=False, comment="제목")
    message = Column(String(500), nullable=True, comment="본문 요약")
    link = Column(String(300), nullable=True, comment="클릭 시 이동할 프론트 경로 (예: /approvals/123)")
    related_type = Column(String(40), nullable=True, comment="연관 리소스 유형 (approval_document 등)")
    related_id = Column(Integer, nullable=True, comment="연관 리소스 id")
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                      nullable=True, comment="알림을 발생시킨 사용자")
    is_read = Column(Boolean, nullable=False, default=False, server_default="false",
                     index=True, comment="읽음 여부")
    read_at = Column(DateTime(timezone=True), nullable=True, comment="읽은 시각")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="생성일시")

    recipient = relationship("User", foreign_keys=[recipient_id])
    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self):
        return f"<Notification(to={self.recipient_id}, type={self.type}, read={self.is_read})>"
