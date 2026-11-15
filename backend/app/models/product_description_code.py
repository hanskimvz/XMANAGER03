"""
제품 설명 코드 (Product Description Code) 모델
오더코드 세그먼트별 영문 Description 매핑을 관리합니다.

v0.24.0: 초기 구현

예시:
  오더코드: HXB13-PSD-B-O4-S1-D55
  세그먼트별 매핑:
    PSD  → "-Plug with Dust Cap"
    B    → "-Aluminium alloy, Black hard anodizing"
    O4   → "-4 CH"
    S1   → ", 9 μm core Singlemode fiber"
    D55  → "-for out diameter 5.5mm Outdoor cable"

  → 자동 조합 Description:
    "-Plug with Dust Cap\n-Aluminium alloy, Black hard anodizing\n-4 CH, 9 μm core Singlemode fiber\n-for out diameter 5.5mm Outdoor cable"
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class ProductDescriptionCode(Base):
    """
    제품 설명 코드 매핑
    오더코드의 각 세그먼트를 영문 Description으로 변환하기 위한 매핑 테이블
    """
    __tablename__ = "product_description_code"

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 세그먼트 유형
    # PRODUCT: 제품군 (HXB15, HXB13, HXB11, HXB15AS 등)
    # TYPE: 커넥터 타입 (PSD, RJS, RJL, RQS, RQL 등)
    # MATERIAL: 재질 (B, S)
    # CHANNEL: 채널 수 (O2, O4, O6, O8, OA, OC, OE, OG)
    # FIBER: 광섬유 타입 (S1, M1, M2, M3, M4)
    # CABLE: 케이블 사양 (S09, S20, D55, D65)
    # CONNECTOR: 커넥터 조합 (SA 등)
    segment_type = Column(String(20), nullable=False, index=True, comment="세그먼트 유형")

    # 코드 (오더코드에서 사용되는 값)
    code = Column(String(20), nullable=False, index=True, comment="코드")

    # 영문 설명 (Description에 사용)
    description_en = Column(Text, nullable=False, comment="영문 설명")

    # v0.26.0: 한글 설명 (국내 고객용)
    description_ko = Column(Text, comment="한글 설명")

    # 정렬 순서 (같은 segment_type 내에서의 순서)
    sort_order = Column(Integer, default=0, comment="정렬순서")

    # 활성 여부
    is_active = Column(Boolean, default=True, comment="활성 여부")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정일시")

    def __repr__(self):
        return f"<ProductDescriptionCode(segment_type={self.segment_type}, code={self.code})>"
