"""
공급업체 관리 Pydantic 스키마
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SupplierBase(BaseModel):
    """공급업체 기본 스키마"""

    supplier_code: str = Field(..., min_length=1, max_length=50, description="공급업체 코드")
    supplier_name: str = Field(..., min_length=1, max_length=200, description="공급업체명")
    supplier_name_en: Optional[str] = Field(None, max_length=200, description="영문 공급업체명")
    business_number: Optional[str] = Field(None, max_length=20, description="사업자등록번호")
    representative: Optional[str] = Field(None, max_length=100, description="대표자명")
    business_type: Optional[str] = Field(None, max_length=100, description="업태")
    business_item: Optional[str] = Field(None, max_length=100, description="종목")
    address: Optional[str] = Field(None, max_length=500, description="주소")
    tel: Optional[str] = Field(None, max_length=50, description="전화번호")
    fax: Optional[str] = Field(None, max_length=50, description="팩스번호")
    email: Optional[str] = Field(None, max_length=200, description="이메일")
    manager_name: Optional[str] = Field(None, max_length=100, description="담당자명")
    manager_tel: Optional[str] = Field(None, max_length=50, description="담당자 전화")
    manager_email: Optional[str] = Field(None, max_length=200, description="담당자 이메일")
    payment_terms: Optional[str] = Field(None, max_length=200, description="결제 조건")
    delivery_terms: Optional[str] = Field(None, max_length=200, description="납품 조건")
    credit_rating: Optional[str] = Field(None, max_length=10, description="신용등급")
    is_active: bool = Field(True, description="활성 여부")
    remark: Optional[str] = Field(None, description="비고")


class SupplierCreate(SupplierBase):
    """공급업체 생성 스키마"""

    pass


class SupplierUpdate(BaseModel):
    """공급업체 수정 스키마 (모든 필드 선택적)"""

    supplier_code: Optional[str] = Field(None, min_length=1, max_length=50)
    supplier_name: Optional[str] = Field(None, min_length=1, max_length=200)
    supplier_name_en: Optional[str] = Field(None, max_length=200)
    business_number: Optional[str] = Field(None, max_length=20)
    representative: Optional[str] = Field(None, max_length=100)
    business_type: Optional[str] = Field(None, max_length=100)
    business_item: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    tel: Optional[str] = Field(None, max_length=50)
    fax: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=200)
    manager_name: Optional[str] = Field(None, max_length=100)
    manager_tel: Optional[str] = Field(None, max_length=50)
    manager_email: Optional[str] = Field(None, max_length=200)
    payment_terms: Optional[str] = Field(None, max_length=200)
    delivery_terms: Optional[str] = Field(None, max_length=200)
    credit_rating: Optional[str] = Field(None, max_length=10)
    is_active: Optional[bool] = None
    remark: Optional[str] = None


class SupplierResponse(SupplierBase):
    """공급업체 응답 스키마"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierListItem(BaseModel):
    """공급업체 목록 아이템 (간소화된 정보)"""

    id: int
    supplier_code: str
    supplier_name: str
    supplier_name_en: Optional[str] = None
    tel: Optional[str] = None
    manager_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierSearchParams(BaseModel):
    """공급업체 검색 파라미터"""

    keyword: Optional[str] = Field(None, description="검색 키워드 (코드, 업체명)")
    is_active: Optional[bool] = Field(None, description="활성 여부 필터")
    skip: int = Field(0, ge=0, description="건너뛸 레코드 수")
    limit: int = Field(100, ge=1, le=1000, description="최대 레코드 수")
