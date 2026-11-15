"""
회사 공지사항 (v0.50.0)

- announcements: 공지 1건(제목/본문 HTML/핀/대상부서/소프트삭제).
- announcement_attachments: 첨부파일(다중). files.py 저장 패턴과 동일한 상대경로 보관.
- announcement_reads: 읽음 영수(사용자×공지 1행, UNIQUE). 열람 시 자동 기록.

대상부서(target_departments)는 users.department 와 동일한 부서 **코드 문자열** 배열(JSONB).
NULL/빈배열 = 전체 공개. 본인 부서가 포함되면 열람 가능(관리자는 전체 열람).
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Announcement(Base):
    """공지 1건."""
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, comment="제목")
    body = Column(Text, nullable=False, comment="본문 HTML(TipTap 산출물, 서버 sanitize 후 저장)")
    is_pinned = Column(Boolean, nullable=False, default=False, server_default="false",
                       index=True, comment="상단 고정")
    target_departments = Column(JSONB(none_as_null=True), nullable=True,
                                comment="대상 부서코드 목록(JSONB). NULL/빈배열=전체 공개")
    published_at = Column(DateTime(timezone=True), server_default=func.now(),
                          index=True, comment="발행일시(목록 정렬 기준)")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true",
                       index=True, comment="활성(소프트 삭제 플래그)")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="작성자")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    attachments = relationship(
        "AnnouncementAttachment", back_populates="announcement",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    reads = relationship(
        "AnnouncementRead", back_populates="announcement",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_announcements_active_pinned_pub", "is_active", "is_pinned", "published_at"),
        Index("ix_announcements_target_gin", "target_departments", postgresql_using="gin"),
    )


class AnnouncementAttachment(Base):
    """공지 첨부파일 1건. files.py 저장 규약(상대경로/UUID 파일명)과 동일."""
    __tablename__ = "announcement_attachments"

    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(
        Integer, ForeignKey("announcements.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    original_name = Column(String(300), nullable=False, comment="원본 파일명")
    file_path = Column(String(500), nullable=False,
                       comment="저장 상대경로 announcements/{id}/attachments/{uuid}_{name}")
    file_size = Column(Integer, nullable=False, default=0, server_default="0", comment="바이트")
    content_type = Column(String(150), nullable=True, comment="MIME 타입")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="업로더")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    announcement = relationship("Announcement", back_populates="attachments")


class AnnouncementRead(Base):
    """읽음 영수: (공지, 사용자) 1행. 중복 열람해도 1행 유지."""
    __tablename__ = "announcement_reads"

    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(
        Integer, ForeignKey("announcements.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    read_at = Column(DateTime(timezone=True), server_default=func.now())

    announcement = relationship("Announcement", back_populates="reads")

    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_read_user"),
    )
