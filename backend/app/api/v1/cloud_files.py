"""
파일 허브 (Nextcloud 동기화 폴더 브라우저) — v0.81.0

X-Manager를 '파일 입구'로: 서버에 동기화된 Nextcloud 폴더를 거래처/주문 컨텍스트로
탐색·미리보기·다운로드·업로드한다. 모든 경로는 NEXTCLOUD_BASE_PATH 내부로 강제(../ 차단).
접근 통제는 라우터 등록 시 _guard("sales")로 영업 권한 상속(생산팀 등 차단).
"""

import os
from urllib.parse import quote
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import nextcloud_service as ncs

router = APIRouter(prefix="/cloud-files", tags=["파일 허브"])

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB (대용량 아티팩트 허용)


def _require_enabled():
    if not ncs.enabled():
        raise HTTPException(status_code=503, detail="파일 연동이 비활성화되어 있습니다 (NEXTCLOUD_BASE_PATH 미설정).")


def _abs_or_400(relpath: str) -> str:
    try:
        return ncs.safe_abs(relpath)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _disposition(filename: str, inline: bool) -> str:
    kind = "inline" if inline else "attachment"
    try:
        filename.encode("latin-1")
        return f'{kind}; filename="{filename}"'
    except UnicodeEncodeError:
        return f"{kind}; filename*=UTF-8''{quote(filename)}"


def _norm(relpath: str) -> str:
    return (relpath or "").replace("\\", "/").strip("/")


# ==================== 진입점(엔티티→폴더) ====================

@router.get("/entry")
def entry(
    scope: str = Query(..., description="customer | order"),
    customer_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """거래처/주문의 표준 폴더를 보장(생성)하고 그 경로 + 목록을 반환."""
    _require_enabled()

    if scope == "customer":
        from app.models.business_partner import BusinessPartner
        if not customer_id:
            raise HTTPException(status_code=400, detail="customer_id가 필요합니다.")
        c = db.query(BusinessPartner).filter(BusinessPartner.id == customer_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다.")
        root = ncs.resolve_customer_root(c)  # 저장값 우선(불변 링크)
        # 최초 진입 시 계산 경로를 엔티티에 저장 → 이후 거래처명 변경에도 링크 유지
        if not (c.nextcloud_folder or "").strip():
            c.nextcloud_folder = root
            db.commit()
        ncs.ensure_dir(root)
        # 표준 골격(_공통)은 전용 트리에만 주입 — 수동 링크된 레거시 폴더는 있는 그대로 표시
        managed = ncs.is_managed_root(root)
        if managed:
            ncs.ensure_dir(os.path.join(root, "_공통"))
        return {"scope": "customer", "path": _norm(root), "items": ncs.list_dir(root), "managed": managed}

    if scope == "order":
        from app.models.sales_document import SalesDocument
        from app.models.business_partner import BusinessPartner
        if not document_id:
            raise HTTPException(status_code=400, detail="document_id가 필요합니다.")
        doc = db.query(SalesDocument).filter(SalesDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        c = doc.customer if getattr(doc, "customer", None) else (
            db.query(BusinessPartner).filter(BusinessPartner.id == doc.customer_id).first() if doc.customer_id else None
        )
        # 연결된 영업대응건이 있으면 그 대응건 폴더 하나로 묶는다(문서별 폴더 생성 안 함)
        activity = None
        if getattr(doc, "sales_activity_id", None):
            from app.models.sales_activity import SalesActivity
            activity = db.query(SalesActivity).filter(SalesActivity.id == doc.sales_activity_id).first()
        rel = ncs.resolve_order_relpath(doc, c, activity=activity)  # 저장값 > 대응건 > 문서별
        dirty = False
        if activity is not None and not (getattr(activity, "nextcloud_folder", None) or "").strip() \
                and not (getattr(doc, "nextcloud_folder", None) or "").strip():
            activity.nextcloud_folder = rel
            dirty = True
        if not (getattr(doc, "nextcloud_folder", None) or "").strip():
            doc.nextcloud_folder = rel
            dirty = True
        if dirty:
            db.commit()
        # 표준 골격(01~06)은 전용 트리에만 주입 — 수동 링크된 레거시 폴더는 있는 그대로 표시
        managed = ncs.is_managed_root(rel)
        if managed:
            ncs.ensure_order_skeleton(rel)
        else:
            ncs.ensure_dir(rel)
        return {"scope": "order", "path": _norm(rel), "items": ncs.list_dir(rel), "managed": managed}

    raise HTTPException(status_code=400, detail="scope는 customer 또는 order 여야 합니다.")


# ==================== 레거시 '기존 폴더 연결'(수동 링크) — Phase 2a ====================

def _get_customer_or_404(db, customer_id):
    from app.models.business_partner import BusinessPartner
    c = db.query(BusinessPartner).filter(BusinessPartner.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다.")
    return c


def _get_doc_or_404(db, document_id):
    from app.models.sales_document import SalesDocument
    doc = db.query(SalesDocument).filter(SalesDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    return doc


@router.post("/link")
def link_folder(
    scope: str = Query(..., description="customer | order"),
    path: str = Query(..., description="연결할 기존(레거시) 폴더의 상대경로"),
    customer_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """기존 폴더를 거래처/주문에 수동 연결 — 이후 파일함이 이 경로를 가리킨다.

    폴더를 추측하지 않는다(§3): 사람이 고른 실재 폴더 경로만 nextcloud_folder에 저장.
    """
    _require_enabled()
    full = _abs_or_400(path)
    if not os.path.isdir(full):
        raise HTTPException(status_code=400, detail="선택한 경로가 폴더가 아니거나 존재하지 않습니다.")
    rel = _norm(path)
    if scope == "customer":
        if not customer_id:
            raise HTTPException(status_code=400, detail="customer_id가 필요합니다.")
        c = _get_customer_or_404(db, customer_id)
        c.nextcloud_folder = rel
        db.commit()
    elif scope == "order":
        if not document_id:
            raise HTTPException(status_code=400, detail="document_id가 필요합니다.")
        doc = _get_doc_or_404(db, document_id)
        doc.nextcloud_folder = rel
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="scope는 customer 또는 order 여야 합니다.")
    return {"scope": scope, "path": rel, "items": ncs.list_dir(rel), "managed": ncs.is_managed_root(rel)}


@router.post("/unlink")
def unlink_folder(
    scope: str = Query(..., description="customer | order"),
    customer_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """수동 연결 해제 — nextcloud_folder를 비워 다음 진입 시 전용 트리(자동)로 복귀."""
    _require_enabled()
    if scope == "customer":
        if not customer_id:
            raise HTTPException(status_code=400, detail="customer_id가 필요합니다.")
        c = _get_customer_or_404(db, customer_id)
        c.nextcloud_folder = None
        db.commit()
    elif scope == "order":
        if not document_id:
            raise HTTPException(status_code=400, detail="document_id가 필요합니다.")
        doc = _get_doc_or_404(db, document_id)
        doc.nextcloud_folder = None
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="scope는 customer 또는 order 여야 합니다.")
    return {"ok": True}


# ==================== 탐색 ====================

@router.get("/list")
def list_folder(path: str = Query(..., description="베이스 기준 상대경로")):
    _require_enabled()
    full = _abs_or_400(path)
    if not os.path.isdir(full):
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    return {"path": _norm(path), "items": ncs.list_dir(path)}


@router.get("/preview")
def preview(path: str = Query(...)):
    _require_enabled()
    full = _abs_or_400(path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return FileResponse(path=full, headers={"Content-Disposition": _disposition(os.path.basename(full), inline=True)})


@router.get("/download")
def download(path: str = Query(...)):
    _require_enabled()
    full = _abs_or_400(path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return FileResponse(path=full, headers={"Content-Disposition": _disposition(os.path.basename(full), inline=False)})


# ==================== 쓰기 ====================

@router.post("/upload")
async def upload(
    path: str = Query(..., description="업로드할 대상 폴더(베이스 기준 상대경로)"),
    file: UploadFile = File(...),
):
    _require_enabled()
    folder = _abs_or_400(path)
    if not os.path.isdir(folder):
        # 대상 폴더가 없으면 생성(표준 하위 등)
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            raise HTTPException(status_code=400, detail="업로드 대상 폴더를 만들 수 없습니다.")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"파일이 너무 큽니다. 최대: {MAX_FILE_SIZE // 1024 // 1024}MB")
    safe_name = ncs.sanitize(file.filename or "무제", limit=200)
    dest = os.path.join(folder, safe_name)
    # 동일명 존재 시 (1),(2)… 접미사
    if os.path.exists(dest):
        stem, ext = os.path.splitext(safe_name)
        i = 1
        while os.path.exists(os.path.join(folder, f"{stem} ({i}){ext}")):
            i += 1
        safe_name = f"{stem} ({i}){ext}"
        dest = os.path.join(folder, safe_name)
    try:
        with open(dest, "wb") as f:
            f.write(contents)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {e}")
    return {"message": "업로드되었습니다.", "name": safe_name, "path": _norm(os.path.join(path, safe_name))}


@router.post("/mkdir")
def mkdir(path: str = Query(...), name: str = Query(...)):
    _require_enabled()
    clean = ncs.sanitize(name, limit=150)
    rel = os.path.join(_norm(path), clean)
    _abs_or_400(rel)  # 경로 검증
    ncs.ensure_dir(rel)
    return {"message": "폴더가 생성되었습니다.", "path": _norm(rel)}


@router.delete("")
def delete_file(path: str = Query(...)):
    """파일 삭제(폴더 삭제는 안전상 미허용)."""
    _require_enabled()
    full = _abs_or_400(path)
    if os.path.isdir(full):
        raise HTTPException(status_code=400, detail="폴더는 여기서 삭제할 수 없습니다.")
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    try:
        os.remove(full)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"삭제 실패: {e}")
    return {"message": "삭제되었습니다."}
