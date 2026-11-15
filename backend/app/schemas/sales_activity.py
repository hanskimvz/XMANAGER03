"""
영업 대응 현황 스키마
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


# ==================== 상태 상수 ====================

ACTIVITY_STATUS = {
    "IN_PROGRESS": "진행중",
    "WAITING": "대기",
    "COMPLETED": "완료",
    "ON_HOLD": "보류",
    "DROPPED": "무산",
}

ACTIVITY_STATUS_STYLES = {
    "IN_PROGRESS": "bg-blue-100 text-blue-800",
    "WAITING": "bg-yellow-100 text-yellow-800",
    "COMPLETED": "bg-green-100 text-green-800",
    "ON_HOLD": "bg-gray-100 text-gray-800",
    "DROPPED": "bg-rose-100 text-rose-700",
}

INQUIRY_TYPES = {
    "TECHNICAL": "기술 문의",
    "QUOTATION": "견적 문의",
    "GENERAL": "일반 문의",
    "SAMPLE": "샘플 요청",
    "CLAIM": "클레임",
    "OTHER": "기타",
}


# ==================== 로그 스키마 ====================

class SalesActivityLogCreate(BaseModel):
    content: str = Field(..., min_length=1, description="로그 내용")
    log_type: str = Field("COMMENT", description="로그 유형 (COMMENT/NEXT_STEP/PENDING_REASON/STATUS/INQUIRY_TYPE/ASSIGNEE)")
    logged_by: Optional[str] = Field(None, description="작성자")


class SalesActivityLogUpdate(BaseModel):
    content: str = Field(..., min_length=1, description="수정할 로그 내용")
    edited_by: Optional[str] = Field(None, description="수정자")


class SalesActivityLogResponse(BaseModel):
    id: int
    activity_id: int
    log_type: str = "COMMENT"
    content: str
    logged_by: Optional[str] = None
    attachment_files: Optional[list] = None
    edited_by: Optional[str] = None
    edited_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== 활동 스키마 ====================

class SalesActivityCreate(BaseModel):
    customer_id: Optional[int] = Field(None, description="거래처 ID")
    customer_name: Optional[str] = Field(None, max_length=200, description="거래처명")
    country: Optional[str] = Field(None, max_length=100, description="나라")
    title: str = Field(..., max_length=300, description="프로젝트명")
    assigned_to: Optional[str] = Field(None, max_length=100, description="담당자")
    status: str = Field("IN_PROGRESS", description="상태")
    inquiry_type: str = Field("GENERAL", description="문의 유형")
    is_urgent: bool = Field(False, description="긴급(시급성)")
    is_important: bool = Field(False, description="중요(전략가치)")
    current_step: Optional[str] = Field(None, description="현재 진행 단계")
    next_step: Optional[str] = Field(None, description="다음 필요 단계")
    pending_reason: Optional[str] = Field(None, description="지연 사유")
    expected_amount: Optional[Decimal] = Field(None, description="예상 금액")
    expected_currency: str = Field("KRW", max_length=3, description="통화")


class SalesActivityUpdate(BaseModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    country: Optional[str] = None
    title: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    inquiry_type: Optional[str] = None
    is_urgent: Optional[bool] = None
    is_important: Optional[bool] = None
    current_step: Optional[str] = None
    next_step: Optional[str] = None
    pending_reason: Optional[str] = None
    expected_amount: Optional[Decimal] = None
    expected_currency: Optional[str] = None


class CustomerSimple(BaseModel):
    id: int
    partner_name: Optional[str] = None
    partner_name_en: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SalesActivityResponse(BaseModel):
    id: int
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    country: Optional[str] = None
    title: str
    assigned_to: Optional[str] = None
    status: str
    inquiry_type: Optional[str] = "GENERAL"
    is_urgent: bool = False
    is_important: bool = False
    current_step: Optional[str] = None
    next_step: Optional[str] = None
    pending_reason: Optional[str] = None
    expected_amount: Optional[Decimal] = None
    expected_currency: str = "KRW"
    nextcloud_folder: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    customer: Optional[CustomerSimple] = None
    logs: Optional[List[SalesActivityLogResponse]] = None
    log_count: Optional[int] = None
    last_log_date: Optional[datetime] = None
    # 진행 단계(리스트에서 주입) — 연결된 영업문서 기준 최신 단계
    stage_type: Optional[str] = None   # QUOTATION/PI/CI/PRODUCTION
    stage_label: Optional[str] = None  # 견적/PI/CI/생산요청
    stage_doc_id: Optional[int] = None # 클릭 시 이동할 문서 id (PRODUCTION은 생산요청 id)

    model_config = ConfigDict(from_attributes=True)


class SalesActivityListResponse(BaseModel):
    items: List[SalesActivityResponse]
    total: int
    skip: int
    limit: int
