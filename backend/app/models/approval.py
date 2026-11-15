"""
전자결재 모듈 모델 (v0.33.0)

Phase 1: 자유 기안 1종(form_id=NULL).
ApprovalDocument 를 중심으로 결재선/감사이력/정정이력/PDF 보관을 한 파일에 모은다.
(sales_document.py 가 SalesDocument/Item/Link 를 함께 두는 연관 도메인 그룹핑 관행 모방)
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

# 결재 기록 시각은 분 단위까지만 남긴다(초/마이크로초 절사).
# 문서 표시·인쇄가 모두 분 단위이므로 저장 정밀도를 표시 정밀도에 맞춘다.
# ApprovalService._now() 와 같은 규칙이며, 여기는 DB 기본값/onupdate 경로용.
MINUTE_NOW = text("date_trunc('minute', now())")


def minute_now() -> datetime:
    """분 단위로 절사한 현재 시각(UTC). onupdate 콜러블용."""
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)


class ApprovalForm(Base):
    """프리폼 양식 정의 (v0.34.0)

    fields_schema: 사용자 입력 가이드용 필드 정의 배열.
        각 필드 = {"key","label","type","required","placeholder"?,"help"?,"options"?}
        type ∈ text|textarea|number|date|select
    """
    __tablename__ = "approval_forms"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    code = Column(String(30), unique=True, nullable=False, index=True, comment="양식 코드 FREE/PURCHASE/...")
    name = Column(String(100), nullable=False, comment="양식 이름")
    fields_schema = Column(JSONB, nullable=False, server_default="[]", comment="입력 필드 정의 배열")
    default_line = Column(JSONB, nullable=True, comment="기본 결재선 정의(선택)")
    phase = Column(String(10), nullable=False, default="NONE", server_default="NONE",
                   comment="절차 단계: 단독/사전/사후 (NONE/PRE/POST)")
    linked_form_code = Column(String(30), nullable=True,
                              comment="사후(POST) 양식이 짝이 되는 사전(PRE) 양식 code")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true", comment="활성 여부")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0", comment="정렬 순서")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

    def __repr__(self):
        return f"<ApprovalForm(code={self.code}, name={self.name})>"


class ApprovalDocument(Base):
    """전자결재 문서 (Phase 1: 자유 기안 1종)

    status: DRAFT(임시저장) / IN_PROGRESS(결재중) / APPROVED(승인완료)
            / REJECTED(반려) / CANCELED(회수)
    """
    __tablename__ = "approval_documents"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    doc_number = Column(String(30), unique=True, nullable=False, index=True, comment="문서번호 AP-2026-0001")
    form_id = Column(Integer, ForeignKey("approval_forms.id"), nullable=True, comment="양식 ID (NULL=일반 자유기안)")
    form_data = Column(JSONB, nullable=True, comment="양식별 입력값 (Phase 2)")
    related_document_id = Column(Integer, ForeignKey("approval_documents.id"), nullable=True,
                                 comment="관련 문서(정산서→출장신청서 등). related_document_ids 첫 항목 하위호환")
    # v0.55.0: 관련 문서 다중 연결(예: 1 지출결의서 ← 여러 구매기안서). id 정수 배열.
    related_document_ids = Column(JSONB, nullable=True, comment="관련 문서 ID 배열(다중 연결)")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, comment="프로젝트")
    title = Column(String(200), nullable=False, comment="제목")
    content = Column(Text, nullable=True, comment="본문 HTML (TipTap 출력)")
    content_hash = Column(String(64), nullable=True, comment="본문 SHA-256 해시(상신/승인 시점 스냅샷, 위변조 대조용)")
    status = Column(String(20), nullable=False, default="DRAFT", server_default="DRAFT", index=True,
                    comment="상태 DRAFT/IN_PROGRESS/APPROVED/REJECTED/CANCELED")
    current_step = Column(Integer, nullable=False, default=0, server_default="0", comment="현재 결재 차례(1부터, 0=미상신)")
    drafter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="기안자")
    drafted_at = Column(DateTime(timezone=True), nullable=True, comment="상신 시각")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="최종 승인/반려 시각")
    is_corrected = Column(Boolean, nullable=False, default=False, server_default="false", comment="관리자 사후 정정 여부 표식")
    created_at = Column(DateTime(timezone=True), server_default=MINUTE_NOW, comment="생성일시(분 단위)")
    updated_at = Column(DateTime(timezone=True), server_default=MINUTE_NOW, onupdate=minute_now, comment="수정일시(분 단위)")

    # 소프트 삭제 (관리자 전용, 승인 완료건 포함) — 목록/상세/휴가집계에서 제외, 감사용으로 행은 보존
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="false", index=True, comment="소프트 삭제")
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="삭제 일시")
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="삭제자")

    # 구매 구분 + 시행자/시행전후 (v0.64.0)
    purchase_category = Column(String(10), nullable=True, index=True, comment="구매 구분: 일반/과제/개발")
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="시행자(집행자) — 승인 후 실제 구매/집행")
    execution_status = Column(String(10), nullable=True, comment="시행 상태: NULL/PENDING(시행전)/DONE(시행후)")
    executed_at = Column(DateTime(timezone=True), nullable=True, comment="시행 완료 일시")

    drafter = relationship("User", foreign_keys=[drafter_id])
    executor = relationship("User", foreign_keys=[executor_id])
    form = relationship("ApprovalForm", foreign_keys=[form_id])
    project = relationship("Project", foreign_keys=[project_id])
    related_document = relationship(
        "ApprovalDocument",
        remote_side=[id],
        foreign_keys=[related_document_id],
    )
    lines = relationship("ApprovalLine", back_populates="document",
                         cascade="all, delete-orphan", order_by="ApprovalLine.step_order")
    actions = relationship("ApprovalAction", back_populates="document", order_by="ApprovalAction.acted_at")
    references = relationship("ApprovalReference", back_populates="document",
                             cascade="all, delete-orphan")
    attachments = relationship("ApprovalAttachment", back_populates="document",
                              cascade="all, delete-orphan", order_by="ApprovalAttachment.uploaded_at")

    def __repr__(self):
        return f"<ApprovalDocument(number={self.doc_number}, status={self.status}, step={self.current_step})>"


class ApprovalReference(Base):
    """참조자(CC) — 결재권 없음, 열람만 (v0.34.0)."""
    __tablename__ = "approval_references"
    __table_args__ = (
        UniqueConstraint("document_id", "user_id", name="uq_approval_references_doc_user"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="문서 ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="참조 사용자")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

    document = relationship("ApprovalDocument", back_populates="references")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ApprovalReference(doc={self.document_id}, user={self.user_id})>"


class ApprovalAttachment(Base):
    """결재 문서 첨부파일 (v0.34.0).

    stored_path: storage root 기준 상대 경로 (approvals/<doc_id>/<uuid>_<safe_name>)
    """
    __tablename__ = "approval_attachments"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="문서 ID")
    original_name = Column(String(255), nullable=False, comment="원본 파일명")
    stored_path = Column(String(500), nullable=False, comment="storage root 기준 상대 경로")
    content_type = Column(String(120), nullable=True, comment="MIME 타입")
    file_size = Column(BigInteger, nullable=False, default=0, server_default="0", comment="파일 크기(bytes)")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="업로더")
    uploaded_at = Column(DateTime(timezone=True), server_default=MINUTE_NOW, comment="업로드 시각(분 단위)")

    document = relationship("ApprovalDocument", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<ApprovalAttachment(doc={self.document_id}, name={self.original_name})>"


class ApprovalLine(Base):
    """결재선 — 누가 몇 번째로 결재하는가. 상신 후 수정 금지."""
    __tablename__ = "approval_lines"
    __table_args__ = (
        UniqueConstraint("document_id", "step_order", name="uq_approval_lines_doc_step"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="문서 ID")
    step_order = Column(Integer, nullable=False, comment="결재 순서(1,2,3)")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="결재자")
    status = Column(String(20), nullable=False, default="WAITING", server_default="WAITING",
                    comment="WAITING/PENDING(내 차례)/APPROVED/REJECTED")
    acted_at = Column(DateTime(timezone=True), nullable=True, comment="처리 시각")
    comment = Column(Text, nullable=True, comment="승인/반려 의견")
    seal_snapshot = Column(String(300), nullable=True, comment="승인 시점 도장(자동 SVG 식별자 또는 업로드 경로) 스냅샷")
    approver_name = Column(String(100), nullable=True, comment="승인 시점 결재자 이름 스냅샷")
    approver_position = Column(String(20), nullable=True, comment="승인 시점 직급 스냅샷")

    document = relationship("ApprovalDocument", back_populates="lines")
    approver = relationship("User", foreign_keys=[approver_id])

    def __repr__(self):
        return f"<ApprovalLine(doc={self.document_id}, step={self.step_order}, status={self.status})>"


class ApprovalAction(Base):
    """결재 행위 감사 이력. INSERT 전용 — UPDATE/DELETE API 없음."""
    __tablename__ = "approval_actions"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id"),
                         nullable=False, index=True, comment="문서 ID")
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="행위자")
    action = Column(String(20), nullable=False, comment="SUBMIT/APPROVE/REJECT/CANCEL/RESUBMIT")
    comment = Column(Text, nullable=True, comment="의견")
    acted_at = Column(DateTime(timezone=True), server_default=MINUTE_NOW, comment="행위 시각(분 단위)")
    ip_address = Column(String(45), nullable=True, comment="감사 추적용 요청 IP")

    document = relationship("ApprovalDocument", back_populates="actions")
    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self):
        return f"<ApprovalAction(doc={self.document_id}, action={self.action})>"


class ApprovalCorrection(Base):
    """관리자 사후 정정 이력. 원본 덮어쓰지 않고 변경분만 기록. INSERT 전용(삭제 불가)."""
    __tablename__ = "approval_corrections"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id"),
                         nullable=False, index=True, comment="문서 ID")
    target_table = Column(String(40), nullable=False, comment="대상 테이블(actions/lines/documents)")
    target_id = Column(Integer, nullable=False, comment="대상 row ID")
    field_name = Column(String(40), nullable=False, comment="고친 필드(acted_at, comment ...)")
    old_value = Column(Text, nullable=True, comment="원래 값")
    new_value = Column(Text, nullable=True, comment="새 값")
    reason = Column(Text, nullable=False, comment="수정 사유(필수 — 없으면 저장 실패)")
    corrected_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="정정 관리자")
    corrected_at = Column(DateTime(timezone=True), server_default=func.now(), comment="정정 시각")
    ip_address = Column(String(45), nullable=True, comment="요청 IP")

    document = relationship("ApprovalDocument")
    corrector = relationship("User", foreign_keys=[corrected_by])

    def __repr__(self):
        return f"<ApprovalCorrection(doc={self.document_id}, target={self.target_table}.{self.field_name})>"


class ApprovalDocumentPdf(Base):
    """결재 문서 PDF 보관 이력 (sales_document_pdf 패턴 복제 + 검증번호)."""
    __tablename__ = "approval_document_pdf"
    __table_args__ = (
        UniqueConstraint("document_id", "language", name="uq_approval_document_pdf_doc_lang"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    document_id = Column(Integer, ForeignKey("approval_documents.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="대상 결재 문서 ID")
    language = Column(String(10), nullable=False, default="ko", server_default="ko", comment="언어(ko)")
    file_path = Column(String(500), nullable=False, comment="storage root 기준 상대 경로")
    file_size = Column(BigInteger, nullable=False, comment="파일 크기(bytes)")
    file_hash = Column(String(64), nullable=False, comment="PDF 바이트 SHA-256")
    content_hash = Column(String(64), nullable=True, comment="본문(content) SHA-256 — 생성 시점 스냅샷")
    verify_code = Column(String(4), nullable=False, comment="검증번호 = SHA256(doc_number+content) 앞 4 hex 대문자")
    download_count = Column(Integer, nullable=False, default=1, server_default="1", comment="누적 다운로드")
    first_generated_at = Column(DateTime(timezone=True), nullable=False, comment="최초 생성 시각")
    last_downloaded_at = Column(DateTime(timezone=True), nullable=False, comment="최근 다운로드 시각")
    last_generated_by = Column(String(100), nullable=True, comment="최근 생성/다운로드 사용자")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document = relationship("ApprovalDocument", foreign_keys=[document_id])

    def __repr__(self):
        return f"<ApprovalDocumentPdf(doc_id={self.document_id}, lang={self.language}, downloads={self.download_count})>"
