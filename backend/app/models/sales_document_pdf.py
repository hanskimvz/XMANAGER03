"""영업 문서 PDF 보관 메타데이터 (Phase 3)

매 다운로드 시 PDF 파일을 storage에 저장하고 본 테이블에 메타정보 기록.
- (document_id, document_version, language) 3중 키로 1:1 — 같은 조합이면 파일·DB 모두 덮어쓰기
- 문서 버전 변경(v1→v2) 시 별도 row + 별도 파일로 보존되어 수정 이력 확인 가능
- 다운로드 횟수·해시 추적으로 감사 로그 역할
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SalesDocumentPdf(Base):
    """영업 문서 PDF 파일 보관 이력"""
    __tablename__ = "sales_document_pdf"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "document_version", "language",
            name="uq_sales_document_pdf_doc_version_lang",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # 어느 문서의 PDF인지
    document_id = Column(
        Integer,
        ForeignKey("sales_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="대상 영업 문서 ID",
    )
    document_type = Column(String(20), nullable=False, comment="문서 유형 (QUOTATION/PI)")
    document_version = Column(Integer, nullable=False, default=1, comment="문서 버전 (sales_document.version snapshot)")
    language = Column(String(10), nullable=False, comment="언어 (ko/en)")

    # 파일 정보
    file_path = Column(String(500), nullable=False, comment="storage root 기준 상대 경로")
    file_size = Column(BigInteger, nullable=False, comment="파일 크기 (bytes)")
    file_hash = Column(String(64), nullable=False, comment="SHA-256 해시 (데이터 변경 감지)")

    # 다운로드 추적
    download_count = Column(Integer, nullable=False, default=1, server_default="1", comment="누적 다운로드 횟수")
    first_generated_at = Column(DateTime(timezone=True), nullable=False, comment="최초 생성 시각")
    last_downloaded_at = Column(DateTime(timezone=True), nullable=False, comment="최근 다운로드 시각")
    last_generated_by = Column(String(100), comment="최근 생성/다운로드 트리거한 사용자 (인증 적용 시)")

    # 감사 필드
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계
    document = relationship("SalesDocument", foreign_keys=[document_id])

    def __repr__(self):
        return (
            f"<SalesDocumentPdf(doc_id={self.document_id}, "
            f"type={self.document_type}, v{self.document_version}, "
            f"lang={self.language}, downloads={self.download_count})>"
        )
