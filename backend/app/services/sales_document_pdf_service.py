"""영업 문서 PDF 보관 서비스 (Phase 3)

PDF 바이트를 받아:
1. 파일 시스템(또는 클라우드)에 저장
2. sales_document_pdf 테이블에 메타정보 upsert (download_count++)

매 다운로드마다 호출되어 동일 (document, version, language) 조합은 덮어쓰기,
새 조합은 INSERT.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.sales_document_pdf import SalesDocumentPdf
from app.services.pdf.storage import PdfStorage, get_default_storage


def _sanitize_filename_part(value: str) -> str:
    """파일명에 부적합한 문자(/, \\, : 등)를 _로 치환."""
    bad = '/\\:*?"<>|'
    return "".join("_" if ch in bad else ch for ch in value)


def build_pdf_relative_path(
    document_id: int,
    document_number: str,
    document_version: int,
    language: str,
) -> str:
    """저장소 상대 경로 생성: '{doc_id}/{document_number}_v{ver}_{lang}.pdf'"""
    safe_num = _sanitize_filename_part(document_number)
    return f"{document_id}/{safe_num}_v{document_version}_{language}.pdf"


class SalesDocumentPdfService:
    """sales_document_pdf 테이블 + PDF 파일 저장소 결합."""

    def __init__(self, db: Session, storage: Optional[PdfStorage] = None):
        self.db = db
        self.storage = storage or get_default_storage()

    def store_pdf(
        self,
        document_id: int,
        document_number: str,
        document_type: str,
        document_version: int,
        language: str,
        pdf_bytes: bytes,
        generated_by: Optional[str] = None,
    ) -> SalesDocumentPdf:
        """PDF 바이트를 저장하고 메타 row를 upsert.

        - 같은 (document_id, version, language) 조합 존재 시:
          파일 덮어쓰기 + download_count++ + last_downloaded_at 갱신
        - 없으면 INSERT (download_count=1).
        """
        relative_path = build_pdf_relative_path(
            document_id, document_number, document_version, language
        )

        # 1) 파일 저장 (덮어쓰기)
        self.storage.save(relative_path, pdf_bytes)

        # 1-b) 연결된 영업 건에 Nextcloud 폴더가 있으면 그곳에도 저장(best-effort, 다운로드 실패 안 시킴)
        try:
            from app.services import nextcloud_service as ncs
            if ncs.enabled():
                from app.models.sales_document import SalesDocument
                from app.models.sales_activity import SalesActivity
                from app.api.v1.sales_document import _resolve_activity_id
                _doc = self.db.query(SalesDocument).filter(SalesDocument.id == document_id).first()
                _aid = _resolve_activity_id(self.db, _doc) if _doc else None
                if _aid:
                    _act = self.db.query(SalesActivity).filter(SalesActivity.id == _aid).first()
                    if _act and _act.nextcloud_folder:
                        ncs.save_file(_act.nextcloud_folder, f"{document_number}.pdf", pdf_bytes)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Nextcloud PDF 저장 실패(무시)")

        # 2) 해시·크기 계산
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        file_size = len(pdf_bytes)
        now = datetime.now(timezone.utc)

        # 3) DB upsert
        existing = (
            self.db.query(SalesDocumentPdf)
            .filter(
                SalesDocumentPdf.document_id == document_id,
                SalesDocumentPdf.document_version == document_version,
                SalesDocumentPdf.language == language,
            )
            .first()
        )

        if existing:
            existing.file_path = relative_path
            existing.file_size = file_size
            existing.file_hash = file_hash
            existing.download_count = (existing.download_count or 0) + 1
            existing.last_downloaded_at = now
            if generated_by:
                existing.last_generated_by = generated_by
            self.db.commit()
            self.db.refresh(existing)
            return existing

        record = SalesDocumentPdf(
            document_id=document_id,
            document_type=document_type,
            document_version=document_version,
            language=language,
            file_path=relative_path,
            file_size=file_size,
            file_hash=file_hash,
            download_count=1,
            first_generated_at=now,
            last_downloaded_at=now,
            last_generated_by=generated_by,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_history(self, document_id: int) -> list[SalesDocumentPdf]:
        """문서별 PDF 보관 이력 (모든 버전·언어, 최근 다운로드 순)."""
        return (
            self.db.query(SalesDocumentPdf)
            .filter(SalesDocumentPdf.document_id == document_id)
            .order_by(SalesDocumentPdf.last_downloaded_at.desc())
            .all()
        )
