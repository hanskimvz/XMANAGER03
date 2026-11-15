"""
앱 전역 설정 (key-value) 모델 (v0.49.0)

관리자가 화면에서 바꾸는 운영 설정을 저장하는 범용 테이블.
- 예) disbursement_approvers = [user_id, ...]  (지출결의서 기본 집행 담당 결재선)
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(60), primary_key=True, comment="설정 키")
    value = Column(JSONB, nullable=True, comment="설정 값(JSON)")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AppSetting(key={self.key})>"
