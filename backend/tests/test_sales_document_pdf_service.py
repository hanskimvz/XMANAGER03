"""SalesDocumentPdfService — DB upsert + storage 저장 통합 테스트

DB는 mock(SQLAlchemy session) 대신 in-process SQLite로 가볍게 테스트.
storage는 tmp 디렉토리 기반 LocalFilesystemStorage.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 모든 모델을 로드해 SQLAlchemy mapper 초기화 의존성 충족
import app.models  # noqa: F401
from app.models.sales_document_pdf import SalesDocumentPdf
from app.services.pdf.storage import LocalFilesystemStorage
from app.services.sales_document_pdf_service import (
    SalesDocumentPdfService,
    build_pdf_relative_path,
)


@pytest.fixture
def db_session(tmp_path):
    """SQLite in-memory DB로 sales_document_pdf 테이블만 빠르게 사용."""
    engine = create_engine("sqlite:///:memory:", future=True)
    # FK 사용하지 않는 단독 테스트라 sales_document_pdf 만 만든다
    SalesDocumentPdf.__table__.create(engine, checkfirst=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def storage(tmp_path):
    return LocalFilesystemStorage(tmp_path / "pdfs")


@pytest.fixture
def service(db_session, storage):
    return SalesDocumentPdfService(db_session, storage=storage)


class TestBuildPath:
    def test_basic(self):
        assert build_pdf_relative_path(562, "Q-BI260306", 1, "ko") == "562/Q-BI260306_v1_ko.pdf"

    def test_version_in_filename(self):
        assert "_v3_" in build_pdf_relative_path(7, "Q-X", 3, "en")

    def test_special_chars_sanitized(self):
        # 슬래시·콜론 등 제거
        result = build_pdf_relative_path(1, "Q/A:B*", 1, "ko")
        assert "/" not in result.split("/", 1)[1]
        assert ":" not in result


class TestStorePdf:
    def test_first_save_creates_row_with_count_1(self, service, db_session):
        record = service.store_pdf(
            document_id=1, document_number="Q-T-001", document_type="QUOTATION",
            document_version=1, language="ko", pdf_bytes=b"%PDF-fake1",
        )
        assert record.id is not None
        assert record.download_count == 1
        assert record.file_size == len(b"%PDF-fake1")
        assert record.file_hash and len(record.file_hash) == 64
        assert record.first_generated_at is not None
        assert record.last_downloaded_at is not None
        # 파일도 storage에 저장됐는지
        assert service.storage.exists("1/Q-T-001_v1_ko.pdf")

    def test_repeat_save_increments_count_and_overwrites(self, service):
        service.store_pdf(
            document_id=1, document_number="Q-T-001", document_type="QUOTATION",
            document_version=1, language="ko", pdf_bytes=b"%PDF-v1",
        )
        record = service.store_pdf(
            document_id=1, document_number="Q-T-001", document_type="QUOTATION",
            document_version=1, language="ko", pdf_bytes=b"%PDF-v1-updated",
        )
        assert record.download_count == 2
        # 파일 내용이 덮어써졌는지
        assert service.storage.read("1/Q-T-001_v1_ko.pdf") == b"%PDF-v1-updated"

    def test_different_version_creates_separate_row_and_file(self, service, db_session):
        service.store_pdf(
            document_id=1, document_number="Q-T-001", document_type="QUOTATION",
            document_version=1, language="ko", pdf_bytes=b"v1",
        )
        service.store_pdf(
            document_id=1, document_number="Q-T-001", document_type="QUOTATION",
            document_version=2, language="ko", pdf_bytes=b"v2",
        )
        rows = db_session.query(SalesDocumentPdf).filter_by(document_id=1).all()
        assert len(rows) == 2
        # 두 파일 모두 보존됨
        assert service.storage.exists("1/Q-T-001_v1_ko.pdf")
        assert service.storage.exists("1/Q-T-001_v2_ko.pdf")
        assert service.storage.read("1/Q-T-001_v1_ko.pdf") == b"v1"
        assert service.storage.read("1/Q-T-001_v2_ko.pdf") == b"v2"

    def test_different_language_creates_separate_row(self, service, db_session):
        service.store_pdf(
            document_id=1, document_number="Q-T-001", document_type="QUOTATION",
            document_version=1, language="ko", pdf_bytes=b"ko",
        )
        service.store_pdf(
            document_id=1, document_number="Q-T-001", document_type="QUOTATION",
            document_version=1, language="en", pdf_bytes=b"en",
        )
        rows = db_session.query(SalesDocumentPdf).filter_by(document_id=1).all()
        assert len(rows) == 2
        assert {r.language for r in rows} == {"ko", "en"}

    def test_hash_changes_when_content_changes(self, service):
        r1 = service.store_pdf(
            document_id=2, document_number="Q-T-002", document_type="QUOTATION",
            document_version=1, language="ko", pdf_bytes=b"hello",
        )
        old_hash = r1.file_hash
        r2 = service.store_pdf(
            document_id=2, document_number="Q-T-002", document_type="QUOTATION",
            document_version=1, language="ko", pdf_bytes=b"world",
        )
        assert r2.file_hash != old_hash

    def test_generated_by_recorded(self, service):
        record = service.store_pdf(
            document_id=3, document_number="Q-T-003", document_type="QUOTATION",
            document_version=1, language="ko", pdf_bytes=b"x",
            generated_by="MJ Kim",
        )
        assert record.last_generated_by == "MJ Kim"


class TestGetHistory:
    def test_returns_all_versions_and_langs(self, service):
        for v in (1, 2):
            for lang in ("ko", "en"):
                service.store_pdf(
                    document_id=10, document_number="Q-H-010", document_type="QUOTATION",
                    document_version=v, language=lang, pdf_bytes=b"x",
                )
        history = service.get_history(10)
        assert len(history) == 4

    def test_empty_for_unknown_doc(self, service):
        assert service.get_history(99999) == []
