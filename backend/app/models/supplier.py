"""
공급업체 테이블 모델
부품 공급업체 정보를 관리합니다.
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Supplier(Base):
    """
    공급업체 (Supplier)
    부품을 공급하는 업체 정보를 관리합니다.
    """
    __tablename__ = "supplier"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 기본 정보
    supplier_code = Column(String(50), unique=True, nullable=False, index=True, comment="공급업체 코드")
    supplier_name = Column(String(200), nullable=False, comment="공급업체명")
    supplier_name_en = Column(String(200), comment="영문 공급업체명")
    business_number = Column(String(20), comment="사업자등록번호")
    representative = Column(String(100), comment="대표자명")
    business_type = Column(String(100), comment="업태")
    business_item = Column(String(100), comment="종목")

    # 주소
    address = Column(String(500), comment="주소")

    # 연락처 정보
    tel = Column(String(50), comment="전화번호")
    fax = Column(String(50), comment="팩스번호")
    email = Column(String(200), comment="이메일")

    # 담당자 정보
    manager_name = Column(String(100), comment="담당자명")
    manager_tel = Column(String(50), comment="담당자 전화")
    manager_email = Column(String(200), comment="담당자 이메일")

    # 거래 조건
    payment_terms = Column(String(200), comment="결제 조건")
    delivery_terms = Column(String(200), comment="납품 조건")
    credit_rating = Column(String(10), comment="신용등급")

    # 비고
    remark = Column(Text, comment="비고")

    # 상태
    is_active = Column(Boolean, default=True, comment="활성 여부")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")
