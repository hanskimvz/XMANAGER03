"""결재 의견(댓글) 모델 (v0.65.0)

결재 문서를 열람할 수 있는 사람(기안자/결재자/참조자/관리자)이 자유롭게 남기는 논의용 댓글.
작성 시 문서 연관자(기안자+결재선+참조자+시행자)에게 인앱 알림이 간다.
삭제는 본인 또는 관리자만. (수정 없음)
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ApprovalComment(Base):
    __tablename__ = "approval_comment"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("approval_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="결재 문서 ID",
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="작성자")
    content = Column(Text, nullable=False, comment="댓글 내용")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="작성 일시")

    user = relationship("User", foreign_keys=[user_id])
