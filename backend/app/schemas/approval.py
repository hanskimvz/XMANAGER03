"""
전자결재 Pydantic 스키마 (v0.33.0)

설계노트 3장 그대로. 응답은 ConfigDict(from_attributes=True).
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ==================== Enum ====================

class ApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"


class LineStatus(str, Enum):
    WAITING = "WAITING"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ActionType(str, Enum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    RESUBMIT = "RESUBMIT"


class BoxType(str, Enum):
    drafted = "drafted"      # 기안함 (내가 기안한 모든 상태)
    pending = "pending"      # 결재대기 (내 차례)
    done = "done"            # 완료함
    reference = "reference"  # 참조함
    execution = "execution"  # 시행함 (내가 시행자 — 시행전/시행후)
    draft = "draft"          # 하위호환 — drafted 처럼 동작


# ==================== 결재선 입력/응답 ====================

class ApprovalLineCreate(BaseModel):
    """결재선 입력"""
    step_order: int = Field(..., ge=1, description="결재 순서(1부터)")
    approver_id: int = Field(..., description="결재자 ID")


class ApprovalLineResponse(BaseModel):
    """결재선 응답"""
    id: int
    step_order: int
    approver_id: int
    approver_name: Optional[str] = None
    approver_position: Optional[str] = None
    status: str
    acted_at: Optional[datetime] = None
    comment: Optional[str] = None
    # 출력용 — 서비스/라우터에서 주입(자동 SVG 재생성)
    seal_svg: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 감사 이력 응답 ====================

class ApprovalActionResponse(BaseModel):
    """결재 행위 이력 응답 (ip_address 는 ADMIN 전용 응답에만 노출)"""
    id: int
    actor_id: int
    actor_name: Optional[str] = None
    action: str
    comment: Optional[str] = None
    acted_at: Optional[datetime] = None
    ip_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 결재 의견(댓글) ====================


class ApprovalCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class ApprovalCommentResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None
    can_delete: bool = False

    model_config = ConfigDict(from_attributes=True)


# ==================== 문서 Create / Update ====================

class ApprovalDocumentCreate(BaseModel):
    """임시저장(DRAFT) 생성"""
    title: str = Field(..., max_length=200, description="제목")
    content: Optional[str] = Field(None, description="본문 HTML")
    lines: List[ApprovalLineCreate] = Field(default_factory=list, description="결재선(빈 리스트 허용 — DRAFT 단계)")
    form_id: Optional[int] = Field(None, description="양식 ID (NULL=일반 자유기안)")
    form_data: Optional[dict] = Field(None, description="양식별 입력값(key→값)")
    reference_ids: Optional[List[int]] = Field(None, description="참조자(CC) 사용자 ID 목록")
    related_document_id: Optional[int] = Field(None, description="관련 문서 ID(단일, 하위호환)")
    related_document_ids: Optional[List[int]] = Field(None, description="관련 문서 ID 목록(다중 연결)")
    project_id: Optional[int] = Field(None, description="프로젝트 ID")
    purchase_category: Optional[str] = Field(None, description="구매 구분: 일반/과제/개발")
    executor_id: Optional[int] = Field(None, description="시행자(집행자) 사용자 ID")


class ApprovalDocumentUpdate(BaseModel):
    """DRAFT 수정 (lines 는 전체 교체)"""
    title: Optional[str] = Field(None, max_length=200, description="제목")
    content: Optional[str] = Field(None, description="본문 HTML")
    lines: Optional[List[ApprovalLineCreate]] = Field(None, description="결재선 전체 교체")
    form_id: Optional[int] = Field(None, description="양식 ID (NULL=일반 자유기안)")
    form_data: Optional[dict] = Field(None, description="양식별 입력값(key→값)")
    reference_ids: Optional[List[int]] = Field(None, description="참조자(CC) 사용자 ID 목록 전체 교체")
    related_document_id: Optional[int] = Field(None, description="관련 문서 ID(단일, 하위호환)")
    related_document_ids: Optional[List[int]] = Field(None, description="관련 문서 ID 목록(다중 연결, 전체 교체)")
    project_id: Optional[int] = Field(None, description="프로젝트 ID")
    purchase_category: Optional[str] = Field(None, description="구매 구분: 일반/과제/개발")
    executor_id: Optional[int] = Field(None, description="시행자(집행자) 사용자 ID")


class AdminFullEditRequest(ApprovalDocumentUpdate):
    """[관리자] 결재 문서 전체 정정 — 작성 폼 payload + 정정 사유(필수).
    상태/결재선(승인·도장)은 보존하고 문서 내용(제목/본문/form_data 등)만 교체."""
    reason: str = Field(..., min_length=1, description="정정 사유(필수)")


# ==================== 프로젝트 마스터 (v0.38.0 공용화) ====================
# 프로젝트는 app.schemas.project 로 분리됨. 하위호환을 위해 별칭으로 재노출.
from app.schemas.project import (  # noqa: E402
    ProjectResponse as ApprovalProjectResponse,
    ProjectCreate as ApprovalProjectCreate,
    ProjectUpdate as ApprovalProjectUpdate,
)


# ==================== 프리폼 양식 ====================

class ApprovalFormFieldSchema(BaseModel):
    """양식 입력 필드 정의(가이드용)."""
    key: str
    label: str
    type: str = Field("text", description="text|textarea|number|date|select")
    required: bool = False
    placeholder: Optional[str] = None
    help: Optional[str] = None
    options: Optional[List[str]] = None


class ApprovalFormResponse(BaseModel):
    """양식 응답"""
    id: int
    code: str
    name: str
    fields_schema: List[dict] = []
    default_line: Optional[list] = None
    is_active: bool = True
    sort_order: int = 0
    phase: str = "NONE"
    linked_form_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("fields_schema", "default_line", mode="before")
    @classmethod
    def _parse_json_text(cls, v):
        """JSONB가 문자열(이중 인코딩)로 저장된 경우 방어적으로 파싱."""
        if isinstance(v, str):
            import json as _json
            try:
                return _json.loads(v)
            except (ValueError, TypeError):
                return v
        return v


# ==================== 참조자 / 첨부 응답 ====================

class ApprovalReferenceResponse(BaseModel):
    """참조자 응답"""
    user_id: int
    name: Optional[str] = None
    position: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalAttachmentResponse(BaseModel):
    """첨부파일 응답"""
    id: int
    original_name: str
    file_size: int = 0
    content_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 휴가 잔여 ====================

class LeaveBalanceResponse(BaseModel):
    """휴가 연차 잔여 응답"""
    year: int
    entitlement: float
    used: float
    remaining: float


class ApprovalActionRequest(BaseModel):
    """승인/반려/회수/재상신 공용 (반려 시 comment 서비스에서 필수 검증)"""
    comment: Optional[str] = Field(None, description="의견(반려 시 필수)")
    exec_date: Optional[str] = Field(None, description="시행일(집행일) — 지출결의서 최종 승인=집행 시 기록 (v0.46.0)")


# ==================== 문서 응답 ====================

class ApprovalDocumentResponse(BaseModel):
    """문서 상세 응답"""
    id: int
    doc_number: str
    form_id: Optional[int] = None
    form_code: Optional[str] = None
    form_name: Optional[str] = None
    form_data: Optional[dict] = None
    title: str
    content: Optional[str] = None
    status: str
    current_step: int
    drafter_id: int
    drafter_name: Optional[str] = None
    drafter_position: Optional[str] = None      # 편집화면에서 문서의 실제 기안자 표시용
    drafter_department: Optional[str] = None    # 편집화면에서 문서의 실제 기안자 표시용
    drafted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_corrected: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    # 프로젝트 — project_name 은 라우터에서 주입
    project_id: Optional[int] = None
    project_name: Optional[str] = None

    # 구매 구분 + 시행자/시행전후 (v0.64.0) — *_name 은 라우터에서 주입
    purchase_category: Optional[str] = None
    executor_id: Optional[int] = None
    executor_name: Optional[str] = None
    execution_status: Optional[str] = None  # NULL/PENDING(시행전)/DONE(시행후)
    executed_at: Optional[datetime] = None
    can_execute: bool = False  # 내가 시행자 + 승인완료 + 시행전 → True

    # 관련 문서 연결 (정산서→출장신청서 등) — *_number/*_title 은 라우터에서 주입
    related_document_id: Optional[int] = None
    related_doc_number: Optional[str] = None
    related_title: Optional[str] = None
    # 다중 관련 문서 (v0.55.0) — 라우터에서 주입 [{id, doc_number, title, status, form_name}]
    related_documents: list = []

    # 단계형(사전→사후) 연계 — 라우터에서 주입
    form_phase: Optional[str] = None  # 이 문서 양식의 단계(NONE/PRE/POST)
    followups: list = []  # 이 문서가 PRE 일 때 후속 POST 양식들 [{"form_code","form_name"}, ...]
    followup_form_code: Optional[str] = None  # 하위호환 — followups 첫 항목의 form_code
    followup_form_name: Optional[str] = None  # 하위호환 — followups 첫 항목의 form_name
    can_create_followup: bool = False  # PRE + APPROVED + 후속 POST 양식 1개 이상 존재 시 True
    linked_documents: list = []  # 이 문서를 related_document_id 로 가리키는 후속 문서들

    lines: List[ApprovalLineResponse] = []
    actions: List[ApprovalActionResponse] = []
    references: List[ApprovalReferenceResponse] = []
    attachments: List[ApprovalAttachmentResponse] = []

    # 서비스/라우터 주입
    verify_code: Optional[str] = None
    can_act: bool = False
    can_reject: bool = False  # 이미 승인한 결재자도 진행 중이면 반려 가능(v0.90.x)

    model_config = ConfigDict(from_attributes=True)


class ApprovalDocumentListItem(BaseModel):
    """문서 목록 아이템"""
    id: int
    doc_number: str
    title: str
    drafter_name: Optional[str] = None
    current_approver_name: Optional[str] = None
    status: str
    current_step: int
    drafted_at: Optional[datetime] = None
    created_at: datetime
    # 양식/프로젝트 표시·필터용 — 라우터에서 주입
    form_code: Optional[str] = None
    form_name: Optional[str] = None
    project_name: Optional[str] = None
    purchase_category: Optional[str] = None
    executor_name: Optional[str] = None
    execution_status: Optional[str] = None
    is_my_turn: bool = False  # 조회자 기준 현재 내 결재 차례 여부(결재대기함 구분용)

    model_config = ConfigDict(from_attributes=True)


class LinkableTripItem(BaseModel):
    """정산서 작성 시 연결할 출장신청서 후보 (본인 기안 + APPROVED + TRIP)."""
    id: int
    doc_number: str
    title: str
    expense: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class LinkablePredecessorItem(BaseModel):
    """사후(POST) 문서 작성 시 연결할 사전(PRE) 문서 후보.

    본인 기안 + APPROVED + 짝 PRE 양식. form_data 전체 + 편의 필드 제공.
    """
    id: int
    doc_number: str
    title: str
    form_data: Optional[dict] = None
    expense: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ApprovalListResponse(BaseModel):
    """문서 목록 페이지네이션 응답"""
    items: List[ApprovalDocumentListItem]
    total: int
    skip: int
    limit: int


# ==================== 관리자 / 정정 ====================

class DefaultApproverUpdate(BaseModel):
    """디폴트 결재자 설정"""
    approver_id: Optional[int] = Field(None, description="디폴트 결재자 ID (None=해제)")


class AdminDatesUpdate(BaseModel):
    """관리자: 시행일자/결제일 사후 수정 (해당 필드만 전송; 미전송=미변경). 이력 미기록."""
    executed_at: Optional[str] = None  # 시행일자(YYYY-MM-DD). '' = 지움
    exec_date: Optional[str] = None    # 결제/집행일(YYYY-MM-DD). '' = 지움


class CorrectionRequest(BaseModel):
    """관리자 사후 정정 요청 (reason 필수)"""
    target_table: str = Field(..., max_length=40, description="대상 테이블(actions/lines/documents)")
    target_id: int = Field(..., description="대상 row ID")
    field_name: str = Field(..., max_length=40, description="고친 필드")
    new_value: str = Field(..., description="새 값")
    reason: str = Field(..., min_length=1, description="수정 사유(필수)")


class ApprovalCorrectionResponse(BaseModel):
    """정정 이력 응답"""
    id: int
    document_id: int
    target_table: str
    target_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: str
    corrected_by: int
    corrected_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
