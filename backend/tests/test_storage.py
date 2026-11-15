"""LocalFilesystemStorage 테스트"""

import pytest

from app.services.pdf.storage import LocalFilesystemStorage, PdfStorageError


@pytest.fixture
def storage(tmp_path):
    return LocalFilesystemStorage(tmp_path / "pdfs")


def test_save_and_read_roundtrip(storage):
    storage.save("doc/test.pdf", b"hello pdf")
    assert storage.read("doc/test.pdf") == b"hello pdf"


def test_save_creates_subdirectories(storage, tmp_path):
    storage.save("a/b/c/file.pdf", b"x")
    assert (tmp_path / "pdfs" / "a" / "b" / "c" / "file.pdf").is_file()


def test_overwrite(storage):
    storage.save("doc/x.pdf", b"v1")
    storage.save("doc/x.pdf", b"v2")
    assert storage.read("doc/x.pdf") == b"v2"


def test_exists(storage):
    assert storage.exists("missing.pdf") is False
    storage.save("ok.pdf", b"y")
    assert storage.exists("ok.pdf") is True


def test_delete_existing(storage):
    storage.save("doc/d.pdf", b"to-delete")
    storage.delete("doc/d.pdf")
    assert storage.exists("doc/d.pdf") is False


def test_delete_missing_is_noop(storage):
    # 없는 파일 삭제는 예외 없이 통과
    storage.delete("never-existed.pdf")


def test_read_missing_raises(storage):
    with pytest.raises(PdfStorageError, match="파일이 없습니다"):
        storage.read("missing.pdf")


def test_path_traversal_blocked(storage):
    # ".." 경로로 root 밖 접근 시도 차단
    with pytest.raises(PdfStorageError, match="저장소 루트 밖"):
        storage.save("../escaped.pdf", b"bad")


def test_absolute_path_within_root(storage, tmp_path):
    abs_path = storage.absolute_path("a/b.pdf")
    assert str(tmp_path / "pdfs") in abs_path
