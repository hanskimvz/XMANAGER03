"""
BOM (Bill of Materials) 모델
부품간의 구성 관계를 정의합니다.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BOM(Base):
    """
    BOM (Bill of Materials) 테이블
    상위 부품과 하위 부품의 구성 관계를 정의합니다.
    """
    __tablename__ = "bom"

    id = Column(Integer, primary_key=True, index=True)

    # 상위 부품 (조립품/반제품)
    parent_part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True)

    # 하위 부품 (구성품)
    child_part_id = Column(Integer, ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True)

    # 수량 정보
    quantity = Column(Float, nullable=False, default=1.0, comment="소요량")
    unit_id = Column(Integer, ForeignKey("unit.id"), nullable=True, comment="단위")

    # BOM 레벨 (1: 직접 하위, 2: 2단계 하위, ...)
    bom_level = Column(Integer, nullable=False, default=1, comment="BOM 레벨")

    # 정렬 순서
    sort_order = Column(Integer, nullable=False, default=0, comment="정렬순서")

    # 유효 기간
    effective_date = Column(DateTime, nullable=True, comment="적용 시작일")
    expiry_date = Column(DateTime, nullable=True, comment="적용 종료일")

    # 상태
    is_active = Column(Boolean, default=True, comment="사용여부")

    # 비고
    remark = Column(Text, nullable=True, comment="비고")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)

    # Relationships
    parent_part = relationship("Part", foreign_keys=[parent_part_id], back_populates="bom_children")
    child_part = relationship("Part", foreign_keys=[child_part_id], back_populates="bom_parents")
    unit = relationship("Unit", foreign_keys=[unit_id])

    # 복합 유니크 인덱스 (같은 상위-하위 조합 중복 방지)
    __table_args__ = (
        Index('ix_bom_parent_child', 'parent_part_id', 'child_part_id', unique=True),
    )

    def __repr__(self):
        return f"<BOM(id={self.id}, parent={self.parent_part_id}, child={self.child_part_id}, qty={self.quantity})>"


class BomChangeLog(Base):
    """BOM 변경 감사 로그 (v0.97.0) — 누가 언제 무엇을(추가/이동/수량/삭제/분류/병합) 바꿨나."""
    __tablename__ = "bom_change_log"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(20), nullable=False, comment="ADD/MOVE/QTY/DELETE/GROUP/CLASSIFY/MERGE")
    parent_part_id = Column(Integer, nullable=True, index=True, comment="상위 부품 id")
    child_part_id = Column(Integer, nullable=True, index=True, comment="하위 부품 id")
    detail = Column(JSON, nullable=True, comment="변경 상세(before/after 등)")
    actor_id = Column(Integer, nullable=True, comment="변경자 user id")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
