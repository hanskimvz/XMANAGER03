"""
공정 템플릿 모델
v0.29.0: 제품 유형별 기본 공정 순서

작업지시서 생성 시 템플릿에 맞는 공정이 자동으로 추가됩니다.
생산팀 총괄이 필요에 따라 수정 가능.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class ProcessTemplate(Base):
    __tablename__ = "process_template"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(100), unique=True, nullable=False, comment="템플릿명 (커넥터 조립, 케이블 조립체 등)")
    description = Column(Text, comment="설명")

    # 공정 단계 [{task_name, assigned_team, sort_order}]
    steps = Column(JSON, default=list, comment="공정 단계 목록")

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
