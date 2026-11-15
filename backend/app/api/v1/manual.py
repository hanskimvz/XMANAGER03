"""사용자 매뉴얼 다운로드 (v0.82.0).

docs/manual/ 에 등록된 매뉴얼 파일(.pptx/.pdf)을 로그인 사용자에게 제공한다.
파일을 그 폴더에 교체해 넣으면 재배포 없이 최신본이 다운로드된다.
"""
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/manual", tags=["사용자 매뉴얼"])

# .../backend/app/api/v1/manual.py → parents[3] = .../backend, .parent = 프로젝트 루트
_PROJECT_ROOT = Path(__file__).resolve().parents[3].parent
MANUAL_DIR = _PROJECT_ROOT / "docs" / "manual"
ALLOWED_EXT = {".pptx", ".pdf"}
PREFERRED_STEM = "X-Manager_사용자매뉴얼"  # 이 이름을 최우선, 없으면 최근 수정 파일

_MEDIA = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pdf": "application/pdf",
}


def _pick(pool: list[Path]) -> Path:
    """PDF > PPTX 우선(웹 열람 편의), 같은 형식이면 최근 수정본."""
    pdfs = [p for p in pool if p.suffix.lower() == ".pdf"]
    chosen = pdfs or pool
    return max(chosen, key=lambda p: p.stat().st_mtime)


def _find_manual() -> Path | None:
    if not MANUAL_DIR.is_dir():
        return None
    cands = [p for p in MANUAL_DIR.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_EXT]
    if not cands:
        return None
    # 선호 파일명 우선 → 그 안에서 PDF 우선 → 최근 수정본
    preferred = [p for p in cands if p.stem == PREFERRED_STEM]
    return _pick(preferred or cands)


def _disposition(filename: str) -> str:
    try:
        filename.encode("latin-1")
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        return f"attachment; filename*=UTF-8''{quote(filename)}"


@router.get("")
def manual_info():
    """매뉴얼 존재 여부/파일명/크기 — 프론트 버튼 노출 판단용."""
    f = _find_manual()
    if not f:
        return {"available": False}
    st = f.stat()
    return {"available": True, "filename": f.name, "size": st.st_size, "updated_at": st.st_mtime}


@router.get("/download")
def download_manual():
    f = _find_manual()
    if not f:
        raise HTTPException(status_code=404, detail="등록된 매뉴얼이 없습니다.")
    media = _MEDIA.get(f.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(f), media_type=media,
                        headers={"Content-Disposition": _disposition(f.name)})
