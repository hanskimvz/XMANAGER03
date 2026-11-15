"""
BOM 스키마
BOM 관련 Pydantic 모델을 정의합니다.

v0.23.0: BOM 엑셀 업로드 스키마 추가
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# 부품 간략 정보 (BOM 내에서 사용)
class PartBrief(BaseModel):
    id: int
    part_number: str
    part_number_display: Optional[str] = None
    part_name: str
    description: Optional[str] = None
    specification: Optional[str] = None
    unit_name: Optional[str] = None
    is_classified: bool = True  # 미분류(False)면 품번 대신 공백 표시

    class Config:
        from_attributes = True


# BOM 생성 스키마
class BOMCreate(BaseModel):
    parent_part_id: int = Field(..., description="상위 부품 ID")
    child_part_id: int = Field(..., description="하위 부품 ID")
    quantity: float = Field(1.0, gt=0, description="소요량")
    unit_id: Optional[int] = Field(None, description="단위 ID")
    bom_level: int = Field(1, ge=1, description="BOM 레벨")
    sort_order: int = Field(0, ge=0, description="정렬순서")
    effective_date: Optional[datetime] = Field(None, description="적용 시작일")
    expiry_date: Optional[datetime] = Field(None, description="적용 종료일")
    remark: Optional[str] = Field(None, description="비고")
    is_active: bool = Field(True, description="사용여부")


# BOM 수정 스키마
class BOMUpdate(BaseModel):
    quantity: Optional[float] = Field(None, gt=0, description="소요량")
    unit_id: Optional[int] = Field(None, description="단위 ID")
    sort_order: Optional[int] = Field(None, ge=0, description="정렬순서")
    effective_date: Optional[datetime] = Field(None, description="적용 시작일")
    expiry_date: Optional[datetime] = Field(None, description="적용 종료일")
    remark: Optional[str] = Field(None, description="비고")
    is_active: Optional[bool] = Field(None, description="사용여부")


# BOM 응답 스키마
class BOMResponse(BaseModel):
    id: int
    parent_part_id: int
    child_part_id: int
    quantity: float
    unit_id: Optional[int] = None
    bom_level: int
    sort_order: int
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    remark: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# BOM 상세 응답 (부품 정보 포함)
class BOMDetailResponse(BOMResponse):
    parent_part: Optional[PartBrief] = None
    child_part: Optional[PartBrief] = None
    unit_name: Optional[str] = None

    class Config:
        from_attributes = True


# BOM 트리 노드 (재귀 구조)
class BOMTreeNode(BaseModel):
    id: int
    part_id: int
    part_number: str
    part_number_display: Optional[str] = None
    part_name: str
    specification: Optional[str] = None
    quantity: float
    unit_name: Optional[str] = None
    bom_level: int
    level_code: Optional[str] = None  # 부품 레벨코드(색상 구분용)
    is_classified: bool = True      # 미분류(False)면 품번 대신 공백 표시
    attachment_count: int = 0       # 첨부(도면/스펙) 수
    children: List["BOMTreeNode"] = []

    class Config:
        from_attributes = True


# BOM 목록 아이템 (Flat 구조)
class BOMListItem(BaseModel):
    id: int
    parent_part_id: int
    parent_part_number: str
    parent_part_name: str
    child_part_id: int
    child_part_number: str
    child_part_name: str
    child_specification: Optional[str] = None
    quantity: float
    unit_name: Optional[str] = None
    bom_level: int
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


# BOM 일괄 추가 스키마
class BOMBulkCreate(BaseModel):
    parent_part_id: int = Field(..., description="상위 부품 ID")
    items: List["BOMItemCreate"] = Field(..., description="하위 부품 목록")


class BOMItemCreate(BaseModel):
    child_part_id: int = Field(..., description="하위 부품 ID")
    quantity: float = Field(1.0, gt=0, description="소요량")
    unit_id: Optional[int] = Field(None, description="단위 ID")
    sort_order: int = Field(0, ge=0, description="정렬순서")
    remark: Optional[str] = Field(None, description="비고")


# BOM 검색 파라미터
class BOMSearchParams(BaseModel):
    parent_part_id: Optional[int] = Field(None, description="상위 부품 ID")
    child_part_id: Optional[int] = Field(None, description="하위 부품 ID")
    is_active: Optional[bool] = Field(None, description="사용여부")
    skip: int = Field(0, ge=0, description="건너뛸 개수")
    limit: int = Field(100, ge=1, le=1000, description="조회 개수")


# 페이지네이션 응답
class BOMPaginatedResponse(BaseModel):
    items: List[BOMListItem]
    total: int
    skip: int
    limit: int
    has_more: bool


# ==================== BOM 엑셀 업로드 스키마 (v0.23.0 → v2) ====================

class BOMExcelValidationItem(BaseModel):
    """엑셀 행별 검증 결과"""
    row_number: int = Field(..., description="엑셀 행 번호")
    level: int = Field(..., ge=1, description="BOM 레벨")
    part_number_display: str = Field(..., description="품번 (엑셀 원본)")
    part_name: Optional[str] = None
    specification: Optional[str] = None
    quantity: float = Field(1.0)
    unit_name: Optional[str] = None
    remark: Optional[str] = None
    # 조회 결과
    part_id: Optional[int] = None
    resolved_part_name: Optional[str] = None
    resolved_parent_part_id: Optional[int] = None
    is_new_part: bool = Field(False, description="미등록 품번 (자동 생성 대상)")
    has_existing_bom: bool = Field(False, description="기존 BOM 존재 (덮어쓰기 대상)")
    # 검증 상태
    status: str = Field("valid", description="valid / warning / error")
    messages: List[str] = Field(default_factory=list)


class BOMUploadValidateResponse(BaseModel):
    """엑셀 업로드 검증 결과"""
    is_valid: bool = Field(..., description="업로드 가능 여부 (error 없으면 true)")
    total_rows: int = 0
    valid_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    new_part_count: int = Field(0, description="미등록 품번 수")
    overwrite_count: int = Field(0, description="기존 BOM 덮어쓰기 수")
    items: List[BOMExcelValidationItem] = Field(default_factory=list)
    # 다중 L1 지원: 감지된 상위 부품 목록
    parent_parts: List[dict] = Field(default_factory=list, description="감지된 상위 부품 [{part_id, part_number, part_name}]")


class BOMUploadResult(BaseModel):
    """엑셀 업로드 실행 결과"""
    success: bool = True
    message: str = ""
    total: int = 0
    created_count: int = 0
    skipped_count: int = 0
    overwrite_count: int = Field(0, description="덮어쓴 BOM 수")
    new_part_count: int = Field(0, description="신규 생성된 품번 수")
    error_count: int = 0
    errors: List[dict] = Field(default_factory=list)
    parent_part_ids: List[int] = Field(default_factory=list, description="처리된 상위 부품 ID 목록")
