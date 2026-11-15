"""
코드 마스터 API 라우터
코드 마스터 CRUD API를 제공합니다.

Service Layer를 통해 비즈니스 로직을 처리합니다.

v0.10.0: 품번 구조 변경 (부품코드 관리기준서 적용)
- 신규: ProductLine, PartGroup, DevelopmentType, PartType, DrawingType
- Legacy: MajorCategory, MiddleCategory, MinorCategory 유지 (하위 호환)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from app.api.v1.deps import get_code_master_service, handle_service_exception
from app.services.code_master_service import CodeMasterService
from app.schemas.code_master import (
    # 신규 코드 테이블 (v0.10.0)
    ProductLineCreate, ProductLineUpdate, ProductLineResponse,
    PartGroupCreate, PartGroupUpdate, PartGroupResponse,
    DevelopmentTypeCreate, DevelopmentTypeUpdate, DevelopmentTypeResponse,
    PartTypeCreate, PartTypeUpdate, PartTypeResponse,
    DrawingTypeCreate, DrawingTypeUpdate, DrawingTypeResponse,
    # Legacy 코드 테이블
    MajorCategoryCreate, MajorCategoryUpdate, MajorCategoryResponse,
    MaterialCreate, MaterialUpdate, MaterialResponse,
    TreatmentCreate, TreatmentUpdate, TreatmentResponse,
    LevelCreate, LevelUpdate, LevelResponse,
    MiddleCategoryCreate, MiddleCategoryUpdate, MiddleCategoryResponse,
    MinorCategoryCreate, MinorCategoryUpdate, MinorCategoryResponse,
    SubCategoryCreate, SubCategoryUpdate, SubCategoryResponse,
    ItemCodeCreate, ItemCodeUpdate, ItemCodeResponse,
    ProcurementTypeCreate, ProcurementTypeUpdate, ProcurementTypeResponse,
    SupplierTypeCreate, SupplierTypeUpdate, SupplierTypeResponse,
    UnitCreate, UnitUpdate, UnitResponse,
)
from app.core.exceptions import AppException

router = APIRouter(prefix="/codes", tags=["코드 마스터"])


# ============================================================
# 신규 코드 테이블 API (v0.10.0)
# ============================================================

# ==================== 제품라인 (ProductLine) ====================

@router.get("/product-lines", response_model=List[ProductLineResponse])
def get_product_lines(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """제품라인 목록 조회"""
    return service.get_all("product-lines", is_active=is_active, skip=skip, limit=limit)


@router.get("/product-lines/{item_id}", response_model=ProductLineResponse)
def get_product_line(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """제품라인 단건 조회"""
    try:
        return service.get_or_raise("product-lines", item_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/product-lines", response_model=ProductLineResponse, status_code=status.HTTP_201_CREATED)
def create_product_line(
    item: ProductLineCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """제품라인 생성"""
    try:
        return service.create("product-lines", item.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/product-lines/{item_id}", response_model=ProductLineResponse)
def update_product_line(
    item_id: int,
    item: ProductLineUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """제품라인 수정"""
    try:
        return service.update("product-lines", item_id, item.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/product-lines/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_line(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """제품라인 삭제"""
    try:
        service.delete("product-lines", item_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 품목군 (PartGroup) ====================

@router.get("/part-groups", response_model=List[PartGroupResponse])
def get_part_groups(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목군 목록 조회"""
    return service.get_all("part-groups", is_active=is_active, skip=skip, limit=limit)


@router.get("/part-groups/{item_id}", response_model=PartGroupResponse)
def get_part_group(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목군 단건 조회"""
    try:
        return service.get_or_raise("part-groups", item_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/part-groups", response_model=PartGroupResponse, status_code=status.HTTP_201_CREATED)
def create_part_group(
    item: PartGroupCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목군 생성"""
    try:
        return service.create("part-groups", item.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/part-groups/{item_id}", response_model=PartGroupResponse)
def update_part_group(
    item_id: int,
    item: PartGroupUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목군 수정"""
    try:
        return service.update("part-groups", item_id, item.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/part-groups/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part_group(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목군 삭제"""
    try:
        service.delete("part-groups", item_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 개발구분 (DevelopmentType) ====================

@router.get("/development-types", response_model=List[DevelopmentTypeResponse])
def get_development_types(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """개발구분 목록 조회"""
    return service.get_all("development-types", is_active=is_active, skip=skip, limit=limit)


@router.get("/development-types/{item_id}", response_model=DevelopmentTypeResponse)
def get_development_type(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """개발구분 단건 조회"""
    try:
        return service.get_or_raise("development-types", item_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/development-types", response_model=DevelopmentTypeResponse, status_code=status.HTTP_201_CREATED)
def create_development_type(
    item: DevelopmentTypeCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """개발구분 생성"""
    try:
        return service.create("development-types", item.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/development-types/{item_id}", response_model=DevelopmentTypeResponse)
def update_development_type(
    item_id: int,
    item: DevelopmentTypeUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """개발구분 수정"""
    try:
        return service.update("development-types", item_id, item.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/development-types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_development_type(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """개발구분 삭제"""
    try:
        service.delete("development-types", item_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 부품유형 (PartType) ====================

@router.get("/part-types", response_model=List[PartTypeResponse])
def get_part_types(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """부품유형 목록 조회"""
    return service.get_all("part-types", is_active=is_active, skip=skip, limit=limit)


@router.get("/part-types/{item_id}", response_model=PartTypeResponse)
def get_part_type(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """부품유형 단건 조회"""
    try:
        return service.get_or_raise("part-types", item_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/part-types", response_model=PartTypeResponse, status_code=status.HTTP_201_CREATED)
def create_part_type(
    item: PartTypeCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """부품유형 생성"""
    try:
        return service.create("part-types", item.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/part-types/{item_id}", response_model=PartTypeResponse)
def update_part_type(
    item_id: int,
    item: PartTypeUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """부품유형 수정"""
    try:
        return service.update("part-types", item_id, item.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/part-types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part_type(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """부품유형 삭제"""
    try:
        service.delete("part-types", item_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 도면여부 (DrawingType) ====================

@router.get("/drawing-types", response_model=List[DrawingTypeResponse])
def get_drawing_types(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """도면여부 목록 조회"""
    return service.get_all("drawing-types", is_active=is_active, skip=skip, limit=limit)


@router.get("/drawing-types/{item_id}", response_model=DrawingTypeResponse)
def get_drawing_type(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """도면여부 단건 조회"""
    try:
        return service.get_or_raise("drawing-types", item_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/drawing-types", response_model=DrawingTypeResponse, status_code=status.HTTP_201_CREATED)
def create_drawing_type(
    item: DrawingTypeCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """도면여부 생성"""
    try:
        return service.create("drawing-types", item.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/drawing-types/{item_id}", response_model=DrawingTypeResponse)
def update_drawing_type(
    item_id: int,
    item: DrawingTypeUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """도면여부 수정"""
    try:
        return service.update("drawing-types", item_id, item.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/drawing-types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_drawing_type(
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """도면여부 삭제"""
    try:
        service.delete("drawing-types", item_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ============================================================
# Legacy 코드 테이블 API (하위 호환)
# ============================================================

# ==================== 대분류 (MajorCategory) ====================

@router.get("/major-categories", response_model=List[MajorCategoryResponse])
def get_major_categories(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """대분류 목록 조회"""
    return service.get_all("major-categories", is_active=is_active, skip=skip, limit=limit)


@router.get("/major-categories/{category_id}", response_model=MajorCategoryResponse)
def get_major_category(
    category_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """대분류 단건 조회"""
    try:
        return service.get_or_raise("major-categories", category_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/major-categories", response_model=MajorCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_major_category(
    category: MajorCategoryCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """대분류 생성"""
    try:
        return service.create("major-categories", category.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/major-categories/{category_id}", response_model=MajorCategoryResponse)
def update_major_category(
    category_id: int,
    category: MajorCategoryUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """대분류 수정"""
    try:
        return service.update("major-categories", category_id, category.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/major-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_major_category(
    category_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """대분류 삭제"""
    try:
        service.delete("major-categories", category_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 중분류 (MiddleCategory) ====================

@router.get("/middle-categories", response_model=List[MiddleCategoryResponse])
def get_middle_categories(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """중분류 목록 조회"""
    return service.get_all("middle-categories", is_active=is_active, skip=skip, limit=limit)


@router.get("/middle-categories/{category_id}", response_model=MiddleCategoryResponse)
def get_middle_category(
    category_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """중분류 단건 조회"""
    try:
        return service.get_or_raise("middle-categories", category_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/middle-categories", response_model=MiddleCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_middle_category(
    category: MiddleCategoryCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """중분류 생성"""
    try:
        return service.create("middle-categories", category.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/middle-categories/{category_id}", response_model=MiddleCategoryResponse)
def update_middle_category(
    category_id: int,
    category: MiddleCategoryUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """중분류 수정"""
    try:
        return service.update("middle-categories", category_id, category.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/middle-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_middle_category(
    category_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """중분류 삭제"""
    try:
        service.delete("middle-categories", category_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 소분류 (MinorCategory) ====================

@router.get("/minor-categories", response_model=List[MinorCategoryResponse])
def get_minor_categories(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """소분류 목록 조회"""
    return service.get_all("minor-categories", is_active=is_active, skip=skip, limit=limit)


@router.get("/minor-categories/{category_id}", response_model=MinorCategoryResponse)
def get_minor_category(
    category_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """소분류 단건 조회"""
    try:
        return service.get_or_raise("minor-categories", category_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/minor-categories", response_model=MinorCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_minor_category(
    category: MinorCategoryCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """소분류 생성"""
    try:
        return service.create("minor-categories", category.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/minor-categories/{category_id}", response_model=MinorCategoryResponse)
def update_minor_category(
    category_id: int,
    category: MinorCategoryUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """소분류 수정"""
    try:
        return service.update("minor-categories", category_id, category.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/minor-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_minor_category(
    category_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """소분류 삭제"""
    try:
        service.delete("minor-categories", category_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 세분류 (SubCategory) ====================

@router.get("/sub-categories", response_model=List[SubCategoryResponse])
def get_sub_categories(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """세분류 목록 조회"""
    return service.get_all("sub-categories", is_active=is_active, skip=skip, limit=limit)


@router.get("/sub-categories/{category_id}", response_model=SubCategoryResponse)
def get_sub_category(
    category_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """세분류 단건 조회"""
    try:
        return service.get_or_raise("sub-categories", category_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/sub-categories", response_model=SubCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_sub_category(
    category: SubCategoryCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """세분류 생성"""
    try:
        return service.create("sub-categories", category.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/sub-categories/{category_id}", response_model=SubCategoryResponse)
def update_sub_category(
    category_id: int,
    category: SubCategoryUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """세분류 수정"""
    try:
        return service.update("sub-categories", category_id, category.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/sub-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sub_category(
    category_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """세분류 삭제"""
    try:
        service.delete("sub-categories", category_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 품목코드 (ItemCode) ====================

@router.get("/item-codes", response_model=List[ItemCodeResponse])
def get_item_codes(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목코드 목록 조회"""
    return service.get_all("item-codes", is_active=is_active, skip=skip, limit=limit)


@router.get("/item-codes/{code_id}", response_model=ItemCodeResponse)
def get_item_code(
    code_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목코드 단건 조회"""
    try:
        return service.get_or_raise("item-codes", code_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/item-codes", response_model=ItemCodeResponse, status_code=status.HTTP_201_CREATED)
def create_item_code(
    code: ItemCodeCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목코드 생성"""
    try:
        return service.create("item-codes", code.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/item-codes/{code_id}", response_model=ItemCodeResponse)
def update_item_code(
    code_id: int,
    code: ItemCodeUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목코드 수정"""
    try:
        return service.update("item-codes", code_id, code.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/item-codes/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item_code(
    code_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """품목코드 삭제"""
    try:
        service.delete("item-codes", code_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 재질 (Material) ====================

@router.get("/materials", response_model=List[MaterialResponse])
def get_materials(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """재질 목록 조회"""
    return service.get_all("materials", is_active=is_active, skip=skip, limit=limit)


@router.get("/materials/{material_id}", response_model=MaterialResponse)
def get_material(
    material_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """재질 단건 조회"""
    try:
        return service.get_or_raise("materials", material_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
def create_material(
    material: MaterialCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """재질 생성"""
    try:
        return service.create("materials", material.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/materials/{material_id}", response_model=MaterialResponse)
def update_material(
    material_id: int,
    material: MaterialUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """재질 수정"""
    try:
        return service.update("materials", material_id, material.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """재질 삭제"""
    try:
        service.delete("materials", material_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 후처리 (Treatment) ====================

@router.get("/treatments", response_model=List[TreatmentResponse])
def get_treatments(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """후처리 목록 조회"""
    return service.get_all("treatments", is_active=is_active, skip=skip, limit=limit)


@router.get("/treatments/{treatment_id}", response_model=TreatmentResponse)
def get_treatment(
    treatment_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """후처리 단건 조회"""
    try:
        return service.get_or_raise("treatments", treatment_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/treatments", response_model=TreatmentResponse, status_code=status.HTTP_201_CREATED)
def create_treatment(
    treatment: TreatmentCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """후처리 생성"""
    try:
        return service.create("treatments", treatment.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/treatments/{treatment_id}", response_model=TreatmentResponse)
def update_treatment(
    treatment_id: int,
    treatment: TreatmentUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """후처리 수정"""
    try:
        return service.update("treatments", treatment_id, treatment.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/treatments/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_treatment(
    treatment_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """후처리 삭제"""
    try:
        service.delete("treatments", treatment_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 레벨 (Level) ====================

@router.get("/levels", response_model=List[LevelResponse])
def get_levels(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """레벨 목록 조회"""
    return service.get_all("levels", is_active=is_active, skip=skip, limit=limit)


@router.get("/levels/{level_id}", response_model=LevelResponse)
def get_level(
    level_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """레벨 단건 조회"""
    try:
        return service.get_or_raise("levels", level_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/levels", response_model=LevelResponse, status_code=status.HTTP_201_CREATED)
def create_level(
    level: LevelCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """레벨 생성"""
    try:
        return service.create("levels", level.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/levels/{level_id}", response_model=LevelResponse)
def update_level(
    level_id: int,
    level: LevelUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """레벨 수정"""
    try:
        return service.update("levels", level_id, level.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/levels/{level_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_level(
    level_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """레벨 삭제"""
    try:
        service.delete("levels", level_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 조달구분 (ProcurementType) ====================

@router.get("/procurement-types", response_model=List[ProcurementTypeResponse])
def get_procurement_types(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """조달구분 목록 조회"""
    return service.get_all("procurement-types", is_active=is_active, skip=skip, limit=limit)


@router.get("/procurement-types/{type_id}", response_model=ProcurementTypeResponse)
def get_procurement_type(
    type_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """조달구분 단건 조회"""
    try:
        return service.get_or_raise("procurement-types", type_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/procurement-types", response_model=ProcurementTypeResponse, status_code=status.HTTP_201_CREATED)
def create_procurement_type(
    procurement_type: ProcurementTypeCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """조달구분 생성"""
    try:
        return service.create("procurement-types", procurement_type.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/procurement-types/{type_id}", response_model=ProcurementTypeResponse)
def update_procurement_type(
    type_id: int,
    procurement_type: ProcurementTypeUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """조달구분 수정"""
    try:
        return service.update("procurement-types", type_id, procurement_type.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/procurement-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_procurement_type(
    type_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """조달구분 삭제"""
    try:
        service.delete("procurement-types", type_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 공급업체 구분 (SupplierType) ====================

@router.get("/supplier-types", response_model=List[SupplierTypeResponse])
def get_supplier_types(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """공급업체 구분 목록 조회"""
    return service.get_all("supplier-types", is_active=is_active, skip=skip, limit=limit)


@router.get("/supplier-types/{type_id}", response_model=SupplierTypeResponse)
def get_supplier_type(
    type_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """공급업체 구분 단건 조회"""
    try:
        return service.get_or_raise("supplier-types", type_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/supplier-types", response_model=SupplierTypeResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_type(
    supplier_type: SupplierTypeCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """공급업체 구분 생성"""
    try:
        return service.create("supplier-types", supplier_type.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/supplier-types/{type_id}", response_model=SupplierTypeResponse)
def update_supplier_type(
    type_id: int,
    supplier_type: SupplierTypeUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """공급업체 구분 수정"""
    try:
        return service.update("supplier-types", type_id, supplier_type.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/supplier-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier_type(
    type_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """공급업체 구분 삭제"""
    try:
        service.delete("supplier-types", type_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 단위 (Unit) ====================

@router.get("/units", response_model=List[UnitResponse])
def get_units(
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """단위 목록 조회"""
    return service.get_all("units", is_active=is_active, skip=skip, limit=limit)


@router.get("/units/{unit_id}", response_model=UnitResponse)
def get_unit(
    unit_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """단위 단건 조회"""
    try:
        return service.get_or_raise("units", unit_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit(
    unit: UnitCreate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """단위 생성"""
    try:
        return service.create("units", unit.model_dump())
    except AppException as e:
        handle_service_exception(e)


@router.put("/units/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: int,
    unit: UnitUpdate,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """단위 수정"""
    try:
        return service.update("units", unit_id, unit.model_dump(exclude_unset=True))
    except AppException as e:
        handle_service_exception(e)


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """단위 삭제"""
    try:
        service.delete("units", unit_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ============================================================
# 코드 변경 시 영향받는 부품 조회 및 일괄 업데이트 API
# ============================================================

@router.get("/{table_name}/{item_id}/affected-parts")
def get_affected_parts(
    table_name: str,
    item_id: int,
    service: CodeMasterService = Depends(get_code_master_service)
):
    """
    코드 변경 시 영향받는 부품 목록 조회

    품번에 해당 코드가 포함된 부품들을 반환합니다.
    - product-lines: 대분류 코드 (품번 앞 4자리)
    - part-groups: 품목군 코드 (품번 5~7자리)
    - materials: 재질 코드 (품번 끝에서 4~3자리)
    - treatments: 후처리 코드 (품번 끝 2자리)
    """
    try:
        result = service.get_affected_parts(table_name, item_id)
        return result
    except AppException as e:
        handle_service_exception(e)


@router.post("/{table_name}/{item_id}/batch-update-part-numbers")
def batch_update_part_numbers(
    table_name: str,
    item_id: int,
    new_code: str = Query(..., description="변경할 새 코드값"),
    service: CodeMasterService = Depends(get_code_master_service)
):
    """
    코드 변경에 따른 품번 일괄 업데이트

    해당 코드를 사용하는 모든 부품의 품번을 새 코드로 업데이트합니다.
    """
    try:
        result = service.batch_update_part_numbers(table_name, item_id, new_code)
        return result
    except AppException as e:
        handle_service_exception(e)
