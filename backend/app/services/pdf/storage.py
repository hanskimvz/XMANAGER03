"""PDF 파일 저장소 추상화 (Phase 3).

현재 LocalFilesystemStorage 한 가지 구현. 향후 S3/Azure Blob 추가 시
PdfStorage 인터페이스만 따르면 비즈니스 로직 변경 없이 교체 가능.

settings.PDF_STORAGE_BACKEND 값으로 구현체 선택.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings


class PdfStorageError(Exception):
    """저장소 입출력 실패"""


class PdfStorage(ABC):
    """PDF 저장소 인터페이스.

    relative_path 는 storage root 기준 상대 경로 (예: "562/Q-XXX_v1_ko.pdf").
    """

    @abstractmethod
    def save(self, relative_path: str, content: bytes) -> None:
        """저장 (덮어쓰기)."""

    @abstractmethod
    def read(self, relative_path: str) -> bytes:
        """읽기. 없으면 PdfStorageError."""

    @abstractmethod
    def exists(self, relative_path: str) -> bool: ...

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        """삭제. 없으면 무시."""

    @abstractmethod
    def absolute_path(self, relative_path: str) -> str:
        """디버그/로깅용 — 클라우드 백엔드의 경우 URL 또는 키."""


class LocalFilesystemStorage(PdfStorage):
    """파일 시스템 저장소 — Phase 3 기본 구현."""

    def __init__(self, root: Path):
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _full(self, relative_path: str) -> Path:
        # 경로 traversal 방어 (".." 등 차단)
        full = (self._root / relative_path).resolve()
        if not str(full).startswith(str(self._root)):
            raise PdfStorageError(
                f"저장소 루트 밖 경로 시도: {relative_path!r}"
            )
        return full

    def save(self, relative_path: str, content: bytes) -> None:
        full = self._full(relative_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        try:
            full.write_bytes(content)
        except OSError as exc:
            raise PdfStorageError(f"파일 저장 실패: {full} ({exc})") from exc

    def read(self, relative_path: str) -> bytes:
        full = self._full(relative_path)
        if not full.is_file():
            raise PdfStorageError(f"파일이 없습니다: {full}")
        return full.read_bytes()

    def exists(self, relative_path: str) -> bool:
        try:
            return self._full(relative_path).is_file()
        except PdfStorageError:
            return False

    def delete(self, relative_path: str) -> None:
        try:
            full = self._full(relative_path)
        except PdfStorageError:
            return
        if full.is_file():
            full.unlink()

    def absolute_path(self, relative_path: str) -> str:
        return str(self._full(relative_path))


_default_storage: Optional[PdfStorage] = None


def get_default_storage() -> PdfStorage:
    """settings.PDF_STORAGE_BACKEND 기반 기본 저장소 인스턴스 (싱글턴)."""
    global _default_storage
    if _default_storage is not None:
        return _default_storage

    backend = settings.PDF_STORAGE_BACKEND.lower()
    if backend == "local":
        _default_storage = LocalFilesystemStorage(settings.sales_documents_path)
    else:
        raise PdfStorageError(
            f"지원하지 않는 저장소 백엔드: {backend!r} (현재 'local'만 구현)"
        )
    return _default_storage
