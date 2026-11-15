"""
사용자 모델
v0.28.0: 인증/권한 시스템

역할: ADMIN (관리자) / USER (사원)
- ADMIN: 전체 기능 + 관리자 대시보드 + 사용자 관리
- USER: 일반 업무 기능 (대시보드 제외)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="로그인 ID")
    password_hash = Column(String(200), nullable=False, comment="bcrypt 해시")
    name = Column(String(100), nullable=False, comment="표시 이름 (한글)")
    name_en = Column(String(100), nullable=True, comment="영문 이름")
    email = Column(String(200), comment="이메일")
    role = Column(String(20), default="USER", nullable=False, comment="역할 (ADMIN/USER)")
    position = Column(String(50), nullable=True, comment="직급 (CTO/과장/사원 등)")
    department = Column(String(50), comment="부서 (SALES/PRODUCTION/MANAGEMENT)")
    is_active = Column(Boolean, default=True, comment="활성 여부")
    # --- 연차 관리 (v0.45.0) ---
    hire_date = Column(Date, nullable=True, comment="입사일 — 연차 발생 계산 기준(필수 입력 권장)")
    resign_date = Column(Date, nullable=True, comment="퇴사일 — 연차 정산 기준(재직중=NULL)")
    last_login_at = Column(DateTime(timezone=True), comment="최근 로그인")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # --- 전자결재 모듈 (v0.33.0) ---
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="디폴트 결재자(관리자 설정, 기안 시 1차로 자동 채움)")
    approver2_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="디폴트 결재자 2차(기안 시 2번째로 자동 채움, v0.42.0)")
    seal_text = Column(String(10), nullable=True, comment="도장에 새길 글자(미설정 시 name에서 추출)")
    seal_image_path = Column(String(300), nullable=True, comment="업로드한 도장/서명 이미지 경로(선택). NULL이면 자동 생성 SVG 사용")
    annual_leave_days = Column(Integer, nullable=True, default=15, server_default="15", comment="연 부여 연차 일수(v0.34.0)")
    is_safety_officer = Column(Boolean, nullable=False, default=False, server_default="false", comment="산업기능요원 — True면 연차를 입사일 기준(근로기준법)으로 자동발생 — v0.63.0")
    # --- 휴가 결재 전용 프리셋 (v0.51.0): 휴가(LEAVE) 기안 시 이 결재선/참조자로 자동 채움. 미설정 시 approver_id 폴백 ---
    leave_approver_ids = Column(JSONB, nullable=True, comment="휴가 결재선 결재자 user id 배열(순서)")
    leave_reference_ids = Column(JSONB, nullable=True, comment="휴가 참조자 user id 배열")

    # self-참조 관계 (디폴트 결재자 1차/2차)
    default_approver = relationship("User", remote_side=[id], foreign_keys=[approver_id])
    default_approver2 = relationship("User", remote_side=[id], foreign_keys=[approver2_id])
