"""
첨부파일 저장 경로 도우미

저장 위치는 모두 config.json 의 "storage" 섹션에서 온다 (app.core.config.settings):
    settings.uploads_path          = {path}/{upload}
    settings.approvals_path        = {path}/{approval}
    settings.sales_documents_path  = {path}/{sales_document}

DB 에는 과거 방식으로 기록된 경로가 섞여 있다:
  - 실행 폴더 기준 상대 경로   : uploads\\sales_documents\\po\\xxx.pdf
  - 이전 서버의 절대 경로      : D:\\XMANAGER\\storage\\uploads\\work_orders\\xxx.pdf
resolve_stored_path() 가 이런 값을 현재 스토리지 위치로 다시 맞춰 준다
(실행 폴더의 uploads/ 가 아니라 항상 settings.uploads_path 를 먼저 본다).
"""

import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_MISSING = Path("__no_such_file__")

# 이전 서버에서 DB 에 기록된 경로에 들어 있는 업로드 폴더 이름 (과거 데이터 해석용)
_LEGACY_UPLOAD_DIR = "uploads"


def _segments(stored) -> list:
    text = str(stored or "").strip().replace("\\", "/")
    return [s for s in text.split("/") if s]


def upload_dir(*parts: str) -> Path:
    """업로드 폴더 아래 하위 폴더 경로 (없으면 생성)."""
    path = settings.uploads_path.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_stored_path(stored) -> Path:
    """DB 에 저장된 첨부 경로 → 현재 서버의 실제 경로.

    항상 config.json 의 storage 위치(settings.uploads_path)를 우선한다.
    1) 경로의 마지막 업로드 폴더 뒷부분을 현재 uploads_path 아래로 옮겨 해석한다
       (예: uploads/sales_documents/po/x.pdf, /옛경로/uploads/work_orders/x.pdf)
    2) 업로드 폴더 이름이 없는 상대 경로는 uploads_path 기준 상대 경로로 본다
    3) 스토리지에 파일이 없고 저장된 경로 그대로 파일이 남아 있을 때만 그 파일을 쓴다
       (아직 스토리지로 옮기지 않은 과거 파일 — 경고 로그를 남긴다)
    """
    segments = _segments(stored)
    if not segments:
        return _MISSING

    as_is = Path(str(stored).strip().replace("\\", "/"))

    candidate = None
    markers = {_LEGACY_UPLOAD_DIR, settings.STORAGE_UPLOAD_DIR}
    for i in range(len(segments) - 1, -1, -1):
        if segments[i] in markers:
            rest = segments[i + 1:]
            if rest and ".." not in rest:
                candidate = settings.uploads_path.joinpath(*rest)
            break
    else:
        if not as_is.is_absolute() and ".." not in segments:
            candidate = settings.uploads_path.joinpath(*segments)

    if candidate is None:
        return as_is
    if candidate.is_file() or not as_is.is_file():
        return candidate
    logger.warning("첨부파일이 스토리지에 없어 과거 경로에서 읽습니다: %s (스토리지 위치: %s)", as_is, candidate)
    return as_is


def approval_stored_path(doc_id: int, stored_name: str) -> str:
    """결재 첨부의 DB 저장용 상대 경로: {approval 폴더}/{문서 id}/{파일명}"""
    return f"{settings.STORAGE_APPROVAL_DIR}/{doc_id}/{stored_name}"


def resolve_approval_path(stored) -> Path:
    """결재 첨부의 DB 저장 경로({폴더}/{문서 id}/{파일명}) → 실제 경로.

    첫 번째 폴더 이름은 기록 당시 설정값이므로 버리고 현재 approvals_path 를 쓴다.
    """
    rest = _segments(stored)[1:]
    if not rest or ".." in rest:
        return _MISSING
    return settings.approvals_path.joinpath(*rest)
