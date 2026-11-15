"""
부서(조직) 마스터 모델 (v0.43.0, 조직도 필드 v1.04.0)

users.department(코드 문자열)이 참조하는 부서 마스터. 관리자가 추가/수정/삭제.
- code: 안정 키(users.department 에 저장되는 값). 예: SALES
- name: 표시 이름(한글). 예: 영업팀
users.department 는 FK 아닌 문자열 코드라 부서 삭제가 사용자 행을 깨지 않음.

v1.04.0 — 경영관리 > 조직관리(조직도):
- parent_id: 상위 조직(자기참조). NULL 이면 최상위.
- org_type: 조직 유형(EXECUTIVE 경영진/DIVISION 본부/DEPARTMENT 부서/TEAM 팀).
- manager_user_id: 책임자. name_en: 영문명. description: 설명.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base

# 조직 유형 코드 -> 한글 라벨 (프런트 api/department.ts 의 ORG_TYPES 와 동일하게 유지)
ORG_TYPES = {
    "EXECUTIVE": "경영진",
    "DIVISION": "본부",
    "DEPARTMENT": "부서",
    "TEAM": "팀",
}


class Department(Base):
    """부서(조직) 마스터 — 사용자 관리 드롭다운, 조직도 등에서 사용."""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(30), unique=True, nullable=False, index=True, comment="부서 코드(users.department 저장값)")
    name = Column(String(50), nullable=False, comment="부서 이름(한글)")
    name_en = Column(String(100), nullable=True, comment="영문명")
    org_type = Column(String(20), nullable=False, default="TEAM", server_default="TEAM",
                      comment="조직 유형(EXECUTIVE 경영진/DIVISION 본부/DEPARTMENT 부서/TEAM 팀)")
    parent_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"),
                       nullable=True, index=True, comment="상위 조직(NULL=최상위)")
    manager_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True, comment="책임자")
    description = Column(Text, nullable=True, comment="설명")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true", comment="활성 여부")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0", comment="정렬 순서")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

    def __repr__(self):
        return f"<Department(code={self.code}, name={self.name})>"
