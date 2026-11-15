"""
전자결재 첨부파일 서비스 (v0.34.0)

저장 위치: settings.approvals_path / <doc_id> / <uuid>_<safe_name>  (config.json storage.approval)
DB stored_path 는 storage root 기준 상대경로(approvals/<doc_id>/<file>).
files.py 의 저장 방식 참고. 단일 트랜잭션(commit) 유지.
"""

import os
import re
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage_paths import approval_stored_path, resolve_approval_path
from app.core.exceptions import (
    BusinessRuleException,
    NotFoundException,
    ValidationException,
)
from app.models.approval import ApprovalAttachment, ApprovalDocument
from app.models.user import User

# 첨부 가능 상태(기안자가 업로드 가능한 단계)
# REJECTED: 반려 문서를 수정·재상신하기 전 첨부 누락 보완/교체 허용
UPLOADABLE_STATUSES = ("DRAFT", "IN_PROGRESS", "REJECTED")
# IN_PROGRESS 는 아직 아무도 승인하지 않은 경우만(기안서 수정 허용 조건과 동일) — delete() 에서 추가 검사
DELETABLE_STATUSES = ("DRAFT", "IN_PROGRESS", "REJECTED")

# 허용 확장자(문서/이미지/PDF 등 관대하게)
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".hwp", ".hwpx",
    ".txt", ".csv", ".rtf",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg",
    ".zip", ".dwg", ".dxf", ".step", ".stp", ".igs",
}


def _safe_name(name: str) -> str:
    """경로 분리/위험 문자 제거한 안전 파일명."""
    name = os.path.basename(name or "file")
    name = name.replace("\\", "_").replace("/", "_")
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name)
    return name.strip() or "file"


class ApprovalAttachmentService:
    """첨부 업로드/조회/다운로드/삭제 (열람권한은 ApprovalService.get_detail 로 검증)."""

    def __init__(self, db: Session):
        self.db = db

    def _doc(self, doc_id: int) -> ApprovalDocument:
        doc = self.db.query(ApprovalDocument).filter(ApprovalDocument.id == doc_id).first()
        if not doc:
            raise NotFoundException("결재 문서", doc_id)
        return doc

    def save(
        self,
        doc_id: int,
        original_name: str,
        content: bytes,
        content_type: Optional[str],
        actor: User,
    ) -> ApprovalAttachment:
        """첨부 저장. 기안자 & DRAFT/IN_PROGRESS 단계만 허용. 단일 commit."""
        try:
            doc = self._doc(doc_id)
            if doc.drafter_id != actor.id:
                raise BusinessRuleException("기안자만 첨부를 업로드할 수 있습니다.", rule="DRAFTER_ONLY")
            if doc.status not in UPLOADABLE_STATUSES:
                raise BusinessRuleException(
                    "임시저장/결재중 단계에서만 첨부를 업로드할 수 있습니다.",
                    rule="ATTACH_STAGE",
                )

            ext = Path(original_name or "").suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ValidationException(
                    f"허용되지 않는 파일 형식입니다: {ext or '(없음)'}",
                    field="file",
                )
            if len(content) > settings.MAX_UPLOAD_SIZE:
                max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
                raise ValidationException(
                    f"파일 크기가 너무 큽니다. 최대 {max_mb}MB까지 허용됩니다.",
                    field="file",
                )

            save_dir = settings.approvals_path / str(doc.id)
            save_dir.mkdir(parents=True, exist_ok=True)

            safe = _safe_name(original_name)
            stored_name = f"{uuid.uuid4()}_{safe}"
            abs_path = save_dir / stored_name
            with open(abs_path, "wb") as f:
                f.write(content)

            rel_path = approval_stored_path(doc.id, stored_name)
            att = ApprovalAttachment(
                document_id=doc.id,
                original_name=safe,
                stored_path=rel_path,
                content_type=content_type,
                file_size=len(content),
                uploaded_by=actor.id,
            )
            self.db.add(att)
            self.db.commit()
            self.db.refresh(att)
            return att
        except Exception:
            self.db.rollback()
            raise

    def list(self, doc_id: int):
        """첨부 목록(읽기)."""
        return (
            self.db.query(ApprovalAttachment)
            .filter(ApprovalAttachment.document_id == doc_id)
            .order_by(ApprovalAttachment.uploaded_at)
            .all()
        )

    def get(self, doc_id: int, att_id: int) -> ApprovalAttachment:
        att = (
            self.db.query(ApprovalAttachment)
            .filter(
                ApprovalAttachment.id == att_id,
                ApprovalAttachment.document_id == doc_id,
            )
            .first()
        )
        if not att:
            raise NotFoundException("첨부파일", att_id)
        return att

    def abs_path(self, att: ApprovalAttachment) -> Path:
        return resolve_approval_path(att.stored_path)

    def delete(self, doc_id: int, att_id: int, actor: User) -> None:
        """첨부 삭제. 기안자 & (임시저장 | 반려 | 진행중이면서 아직 아무도 승인 안 함). 단일 commit."""
        try:
            doc = self._doc(doc_id)
            if doc.drafter_id != actor.id:
                raise BusinessRuleException("기안자만 첨부를 삭제할 수 있습니다.", rule="DRAFTER_ONLY")
            approved_exists = any(l.status == "APPROVED" for l in doc.lines)
            if doc.status not in DELETABLE_STATUSES or (doc.status == "IN_PROGRESS" and approved_exists):
                raise BusinessRuleException(
                    "임시저장·반려 상태이거나, 결재중이라도 아직 아무도 승인하지 않은 문서만 첨부를 삭제할 수 있습니다.",
                    rule="ATTACH_DELETE_STAGE",
                )
            att = self.get(doc_id, att_id)
            abs_path = self.abs_path(att)
            self.db.delete(att)
            self.db.commit()
            # DB 커밋 후 실제 파일 삭제(실패해도 무시)
            try:
                if abs_path.exists():
                    os.remove(abs_path)
            except Exception:
                pass
        except Exception:
            self.db.rollback()
            raise
