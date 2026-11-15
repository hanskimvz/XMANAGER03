"""
보관위치(Warehouse Location) 모델
창고 및 보관 위치 정보를 관리합니다.

v0.5.0: 재고관리 기능 추가
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric
from sqlalchemy.sql import func
from app.core.database import Base


class WarehouseLocation(Base):
    """
    보관위치 (Warehouse Location)
    창고 내 보관 위치 정보를 관리합니다.

    위치코드 예시: A-01-01 (창고A, 1열, 1단)
    """
    __tablename__ = "warehouse_location"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 위치 정보
    code = Column(String(50), unique=True, nullable=False, index=True, comment="위치코드")
    name = Column(String(100), nullable=False, comment="위치명")
    warehouse_name = Column(String(100), comment="창고명")
    zone = Column(String(50), comment="구역")
    description = Column(Text, comment="설명")

    # 용량 정보
    capacity = Column(Numeric(15, 2), comment="용량")

    # 정렬 및 상태
    sort_order = Column(Integer, default=0, comment="정렬순서")
    is_active = Column(Boolean, default=True, comment="사용여부")

    # 감사
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")
