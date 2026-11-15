"""거래처 배송지 스키마 (v0.58.0)"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ShippingAddressCreate(BaseModel):
    label: Optional[str] = Field(None, max_length=100, description="배송지 이름표")
    name: Optional[str] = Field(None, max_length=200, description="수령처명")
    address: Optional[str] = Field(None, description="배송 주소")
    contact: Optional[str] = Field(None, max_length=100, description="수령 담당자")
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=200)
    is_default: bool = Field(False, description="기본 배송지 여부")
    sort_order: int = Field(0)


class ShippingAddressUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = None
    contact: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=200)
    is_default: Optional[bool] = None
    sort_order: Optional[int] = None


class ShippingAddressResponse(BaseModel):
    id: int
    partner_id: int
    label: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_default: bool = False
    sort_order: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
