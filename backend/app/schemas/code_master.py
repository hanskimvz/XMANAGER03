"""
코드 마스터 스키마
API 요청/응답을 위한 Pydantic 스키마를 정의합니다.

v0.10.0: 품번 구조 변경 (부품코드 관리기준서 적용)
- 신규: ProductLine, PartGroup, DevelopmentType, PartType, DrawingType
- Legacy: MajorCategory, MiddleCategory, MinorCategory 유지 (하위 호환)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ============================================================
# 신규 코드 테이블 스키마 (v0.10.0)
# ============================================================

# ==================== 제품라인 (ProductLine) ====================

class ProductLineBase(BaseModel):
    """제품라인 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드 (3자리)")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class ProductLineCreate(ProductLineBase):
    """제품라인 생성 스키마"""
    pass


class ProductLineUpdate(BaseModel):
    """제품라인 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProductLineResponse(ProductLineBase):
    """제품라인 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 품목군 (PartGroup) ====================

class PartGroupBase(BaseModel):
    """품목군 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드 (2~3자리)")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class PartGroupCreate(PartGroupBase):
    """품목군 생성 스키마"""
    pass


class PartGroupUpdate(BaseModel):
    """품목군 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class PartGroupResponse(PartGroupBase):
    """품목군 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 개발구분 (DevelopmentType) ====================

class DevelopmentTypeBase(BaseModel):
    """개발구분 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드 (1자리)")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class DevelopmentTypeCreate(DevelopmentTypeBase):
    """개발구분 생성 스키마"""
    pass


class DevelopmentTypeUpdate(BaseModel):
    """개발구분 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class DevelopmentTypeResponse(DevelopmentTypeBase):
    """개발구분 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 부품유형 (PartType) ====================

class PartTypeBase(BaseModel):
    """부품유형 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드 (1자리)")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class PartTypeCreate(PartTypeBase):
    """부품유형 생성 스키마"""
    pass


class PartTypeUpdate(BaseModel):
    """부품유형 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class PartTypeResponse(PartTypeBase):
    """부품유형 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 도면여부 (DrawingType) ====================

class DrawingTypeBase(BaseModel):
    """도면여부 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드 (1자리)")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class DrawingTypeCreate(DrawingTypeBase):
    """도면여부 생성 스키마"""
    pass


class DrawingTypeUpdate(BaseModel):
    """도면여부 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class DrawingTypeResponse(DrawingTypeBase):
    """도면여부 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# Legacy 코드 테이블 스키마 (하위 호환)
# ============================================================

# ==================== 대분류 (MajorCategory) ====================

class MajorCategoryBase(BaseModel):
    """대분류 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class MajorCategoryCreate(MajorCategoryBase):
    """대분류 생성 스키마"""
    pass


class MajorCategoryUpdate(BaseModel):
    """대분류 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MajorCategoryResponse(MajorCategoryBase):
    """대분류 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2


# ==================== 재질 (Material) ====================

class MaterialBase(BaseModel):
    """재질 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class MaterialCreate(MaterialBase):
    """재질 생성 스키마"""
    pass


class MaterialUpdate(BaseModel):
    """재질 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MaterialResponse(MaterialBase):
    """재질 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 후처리 (Treatment) ====================

class TreatmentBase(BaseModel):
    """후처리 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class TreatmentCreate(TreatmentBase):
    """후처리 생성 스키마"""
    pass


class TreatmentUpdate(BaseModel):
    """후처리 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class TreatmentResponse(TreatmentBase):
    """후처리 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 레벨 (Level) v0.12.0 ====================

class LevelBase(BaseModel):
    """
    레벨 기본 스키마 (v0.12.0 확장)

    레벨별 관리 구분:
    - 단품 레벨 (부품관리 페이지): M(내작), O(외작), R(원자재) → is_assembly=False
    - 조립품 레벨 (BOM관리 페이지): C(조합), S(서브), P(패키지), K(키트), F(완제품) → is_assembly=True
    """
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    bom_level: Optional[int] = Field(None, description="BOM 레벨")
    default_unit: Optional[str] = Field(None, max_length=10, description="기본 단위")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")
    # v0.12.0 추가 필드
    is_assembly: bool = Field(default=False, description="조립품 여부 (True: BOM관리, False: 부품관리)")
    cost_calculation: str = Field(default="MANUAL", max_length=10, description="단가계산방식 (MANUAL: 직접입력, BOM: 하위합산)")


class LevelCreate(LevelBase):
    """레벨 생성 스키마"""
    pass


class LevelUpdate(BaseModel):
    """레벨 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    bom_level: Optional[int] = None
    default_unit: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    # v0.12.0 추가 필드
    is_assembly: Optional[bool] = None
    cost_calculation: Optional[str] = Field(None, max_length=10)


class LevelResponse(LevelBase):
    """레벨 응답 스키마 (v0.12.0)"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 중분류 (MiddleCategory) ====================

class MiddleCategoryBase(BaseModel):
    """중분류 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class MiddleCategoryCreate(MiddleCategoryBase):
    """중분류 생성 스키마"""
    pass


class MiddleCategoryUpdate(BaseModel):
    """중분류 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MiddleCategoryResponse(MiddleCategoryBase):
    """중분류 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 소분류 (MinorCategory) ====================

class MinorCategoryBase(BaseModel):
    """소분류 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class MinorCategoryCreate(MinorCategoryBase):
    """소분류 생성 스키마"""
    pass


class MinorCategoryUpdate(BaseModel):
    """소분류 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MinorCategoryResponse(MinorCategoryBase):
    """소분류 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 세분류 (SubCategory) ====================

class SubCategoryBase(BaseModel):
    """세분류 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class SubCategoryCreate(SubCategoryBase):
    """세분류 생성 스키마"""
    pass


class SubCategoryUpdate(BaseModel):
    """세분류 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class SubCategoryResponse(SubCategoryBase):
    """세분류 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 품목코드 (ItemCode) ====================

class ItemCodeBase(BaseModel):
    """품목코드 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class ItemCodeCreate(ItemCodeBase):
    """품목코드 생성 스키마"""
    pass


class ItemCodeUpdate(BaseModel):
    """품목코드 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ItemCodeResponse(ItemCodeBase):
    """품목코드 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 조달구분 (ProcurementType) ====================

class ProcurementTypeBase(BaseModel):
    """조달구분 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class ProcurementTypeCreate(ProcurementTypeBase):
    """조달구분 생성 스키마"""
    pass


class ProcurementTypeUpdate(BaseModel):
    """조달구분 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProcurementTypeResponse(ProcurementTypeBase):
    """조달구분 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 공급업체 구분 (SupplierType) ====================

class SupplierTypeBase(BaseModel):
    """공급업체 구분 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class SupplierTypeCreate(SupplierTypeBase):
    """공급업체 구분 생성 스키마"""
    pass


class SupplierTypeUpdate(BaseModel):
    """공급업체 구분 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class SupplierTypeResponse(SupplierTypeBase):
    """공급업체 구분 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 단위 (Unit) ====================

class UnitBase(BaseModel):
    """단위 기본 스키마"""
    code: str = Field(..., max_length=10, description="코드")
    name_ko: str = Field(..., max_length=50, description="한글명")
    name_en: Optional[str] = Field(None, max_length=50, description="영문명")
    description: Optional[str] = Field(None, description="설명")
    sort_order: int = Field(default=0, description="정렬순서")
    is_active: bool = Field(default=True, description="사용여부")


class UnitCreate(UnitBase):
    """단위 생성 스키마"""
    pass


class UnitUpdate(BaseModel):
    """단위 수정 스키마"""
    code: Optional[str] = Field(None, max_length=10)
    name_ko: Optional[str] = Field(None, max_length=50)
    name_en: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class UnitResponse(UnitBase):
    """단위 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
