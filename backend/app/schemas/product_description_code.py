"""
제품 설명 코드 Pydantic 스키마
오더코드 세그먼트별 Description 매핑 API용
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ProductDescriptionCodeBase(BaseModel):
    """제품 설명 코드 기본 스키마"""
    segment_type: str = Field(..., max_length=20, description="세그먼트 유형 (PRODUCT/TYPE/MATERIAL/CHANNEL/FIBER/CABLE/CONNECTOR)")
    code: str = Field(..., max_length=20, description="코드 (PSD, RJS, B, O4 등)")
    description_en: str = Field(..., description="영문 설명")
    sort_order: int = Field(0, description="정렬순서")
    is_active: bool = Field(True, description="활성 여부")


class ProductDescriptionCodeCreate(ProductDescriptionCodeBase):
    """제품 설명 코드 생성 스키마"""
    pass


class ProductDescriptionCodeUpdate(BaseModel):
    """제품 설명 코드 수정 스키마"""
    segment_type: Optional[str] = Field(None, max_length=20)
    code: Optional[str] = Field(None, max_length=20)
    description_en: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProductDescriptionCodeResponse(ProductDescriptionCodeBase):
    """제품 설명 코드 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductDescriptionCodeListResponse(BaseModel):
    """제품 설명 코드 목록 응답"""
    items: List[ProductDescriptionCodeResponse]
    total: int


class DescriptionComposeRequest(BaseModel):
    """오더코드 Description 자동 조합 요청"""
    order_code: str = Field(..., description="오더코드 (예: HXB13-PSD-B-O4-S1-D55)")
    language: str = Field("en", description="언어 (en: 영문, ko: 한글)")


class DescriptionComposeResponse(BaseModel):
    """오더코드 Description 자동 조합 응답"""
    order_code: str
    description: str = Field(..., description="조합된 Description")
    segments: List[dict] = Field(default_factory=list, description="매칭된 세그먼트 목록")
    unmatched: List[str] = Field(default_factory=list, description="매칭 실패한 세그먼트")
