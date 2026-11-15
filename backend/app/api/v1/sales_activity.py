"""
영업 대응 현황 API 라우터
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Header, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_admin
from app.models.user import User
from app.services.sales_activity_service import SalesActivityService
from app.schemas.sales_activity import (
    SalesActivityCreate,
    SalesActivityUpdate,
    SalesActivityResponse,
    SalesActivityListResponse,
    SalesActivityLogCreate,
    SalesActivityLogResponse,
    SalesActivityLogUpdate,
)

router = APIRouter(prefix="/sales-activities", tags=["영업 대응 현황"])


def get_service(db: Session = Depends(get_db)) -> SalesActivityService:
    return SalesActivityService(db)


@router.get("", response_model=SalesActivityListResponse)
def get_list(
    status: Optional[List[str]] = Query(None),  # 다중 상태(합집합): ?status=IN_PROGRESS&status=WAITING
    assigned_to: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    country: Optional[str] = Query(None),
    inquiry_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    urgent: Optional[bool] = Query(None),
    important: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: SalesActivityService = Depends(get_service),
):
    items, total = service.get_list(
        statuses=status, assigned_to=assigned_to, customer_id=customer_id,
        country=country, inquiry_type=inquiry_type, keyword=keyword,
        urgent=urgent, important=important, skip=skip, limit=limit,
    )

    # 진행 단계 계산 (연결된 영업문서/생산요청 기준). Q→PI→생산요청→CI 중 가장 앞선 단계.
    stage_map = _compute_stages(service.db, [it.id for it in items])

    # log_count, last_log_date, 진행단계 주입
    response_items = []
    for item in items:
        resp = SalesActivityResponse.model_validate(item)
        resp.log_count = getattr(item, 'log_count', 0)
        resp.last_log_date = getattr(item, 'last_log_date', None)
        resp.logs = None  # 리스트에서는 로그 미포함
        st = stage_map.get(item.id)
        if st:
            resp.stage_type, resp.stage_label, resp.stage_doc_id = st
        response_items.append(resp)

    return SalesActivityListResponse(items=response_items, total=total, skip=skip, limit=limit)


def _compute_stages(db, activity_ids: list) -> dict:
    """활동 id별 진행 단계 (stage_type, stage_label, stage_doc_id) 반환.
    QUOTATION→PI→PRODUCTION(생산요청)→CI 중 가장 앞선 단계. CI가 있으면 최종(출고)."""
    if not activity_ids:
        return {}
    from app.models.sales_document import SalesDocument
    from app.models.production_request import ProductionRequest

    docs = db.query(SalesDocument).filter(
        SalesDocument.sales_activity_id.in_(activity_ids),
        SalesDocument.is_latest == True,  # noqa: E712
        SalesDocument.status != "CANCELLED",
    ).all()
    RANK = {"QUOTATION": 1, "PI": 2, "CI": 4}
    LABEL = {"QUOTATION": "견적", "PI": "PI", "CI": "CI"}
    best = {}          # aid -> (rank, doc)
    pi_numbers = {}    # aid -> {PI 문서번호}
    for d in docs:
        aid = d.sales_activity_id
        r = RANK.get(d.document_type, 0)
        cur = best.get(aid)
        if cur is None or (r, d.id) > (cur[0], cur[1].id):
            best[aid] = (r, d)
        if d.document_type == "PI":
            pi_numbers.setdefault(aid, set()).add(d.document_number)

    # 생산요청: PI 번호로 매칭
    all_pi = {num for s in pi_numbers.values() for num in s}
    pr_by_num = {}
    if all_pi:
        for pr in db.query(ProductionRequest).filter(ProductionRequest.pi_number.in_(list(all_pi))).all():
            pr_by_num.setdefault(pr.pi_number, pr)

    out = {}
    for aid, (r, d) in best.items():
        stype, slabel, sdoc = d.document_type, LABEL.get(d.document_type, d.document_type), d.id
        # CI 이전(견적/PI) 단계인데 생산요청이 있으면 '생산요청'으로 승격
        if r < 4:
            for num in pi_numbers.get(aid, ()):
                pr = pr_by_num.get(num)
                if pr is not None:
                    stype, slabel, sdoc = "PRODUCTION", "생산요청", pr.id
                    break
        out[aid] = (stype, slabel, sdoc)
    return out


@router.get("/assignees")
def get_assignees(service: SalesActivityService = Depends(get_service)):
    return service.get_assignees()


@router.get("/{activity_id}", response_model=SalesActivityResponse)
def get_by_id(activity_id: int, service: SalesActivityService = Depends(get_service)):
    item = service.get_by_id(activity_id)
    if not item:
        raise HTTPException(status_code=404, detail="영업활동을 찾을 수 없습니다")
    return item


@router.get("/{activity_id}/documents")
def get_related_documents(activity_id: int, service: SalesActivityService = Depends(get_service)):
    """영업활동에 연결된 영업 문서 목록 (견적서/PI/CI)

    직접 연결된 문서 + link 체인으로 연결된 문서도 포함
    (예: 영업활동A의 PI와 영업활동B의 PI가 합배송 CI로 묶인 경우,
     양쪽 영업활동에서 모두 해당 CI를 볼 수 있음)
    """
    from app.models.sales_document import SalesDocument, SalesDocumentLink
    from sqlalchemy import desc

    activity = service.get_by_id(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="영업활동을 찾을 수 없습니다")

    db = service.db

    # 1. 직접 연결된 문서
    direct_docs = db.query(SalesDocument).filter(
        SalesDocument.sales_activity_id == activity_id
    ).all()

    # 2. 직접 연결된 문서들의 link 체인을 따라가서 추가 문서 수집
    all_doc_ids = set(d.id for d in direct_docs)

    def collect_linked(doc_id):
        forwards = db.query(SalesDocumentLink).filter(SalesDocumentLink.source_id == doc_id).all()
        for link in forwards:
            if link.target_id not in all_doc_ids:
                all_doc_ids.add(link.target_id)
                collect_linked(link.target_id)
        backwards = db.query(SalesDocumentLink).filter(SalesDocumentLink.target_id == doc_id).all()
        for link in backwards:
            if link.source_id not in all_doc_ids:
                all_doc_ids.add(link.source_id)
                collect_linked(link.source_id)

    for d in direct_docs:
        collect_linked(d.id)

    # 전체 문서 조회
    docs = db.query(SalesDocument).filter(
        SalesDocument.id.in_(all_doc_ids)
    ).order_by(desc(SalesDocument.document_date), desc(SalesDocument.id)).all()

    return {
        "activity_id": activity_id,
        "documents": [
            {
                "id": d.id,
                "document_type": d.document_type,
                "document_number": d.document_number,
                "document_date": d.document_date.isoformat() if d.document_date else None,
                "status": d.status,
                "total_amount": float(d.total_amount or 0),
                "currency": d.currency,
                "payment_status": d.payment_status,
            }
            for d in docs
        ],
    }


@router.post("", response_model=SalesActivityResponse, status_code=201)
def create(data: SalesActivityCreate, service: SalesActivityService = Depends(get_service)):
    return service.create(data)


@router.put("/{activity_id}", response_model=SalesActivityResponse)
def update(
    activity_id: int,
    data: SalesActivityUpdate,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    service: SalesActivityService = Depends(get_service),
):
    # URL 디코딩 (한글 사용자명 처리)
    from urllib.parse import unquote
    decoded_user = unquote(x_user_name) if x_user_name else None
    item = service.update(activity_id, data, logged_by=decoded_user)
    if not item:
        raise HTTPException(status_code=404, detail="영업활동을 찾을 수 없습니다")
    return item


@router.delete("/{activity_id}", status_code=204)
def delete(
    activity_id: int,
    admin: User = Depends(require_admin),
    service: SalesActivityService = Depends(get_service),
):
    """영업활동 삭제 (관리자 전용). 연결된 견적서/PI/CI는 삭제하지 않고 연결만 해제."""
    if not service.delete(activity_id):
        raise HTTPException(status_code=404, detail="영업활동을 찾을 수 없습니다")


# ==================== 코멘트 ====================

@router.get("/{activity_id}/logs", response_model=list[SalesActivityLogResponse])
def get_logs(activity_id: int, service: SalesActivityService = Depends(get_service)):
    return service.get_logs(activity_id)


@router.post("/{activity_id}/logs", response_model=SalesActivityLogResponse, status_code=201)
def add_log(activity_id: int, data: SalesActivityLogCreate, service: SalesActivityService = Depends(get_service)):
    log = service.add_log(activity_id, data)
    if not log:
        raise HTTPException(status_code=404, detail="영업활동을 찾을 수 없습니다")
    return log


@router.put("/{activity_id}/logs/{log_id}", response_model=SalesActivityLogResponse)
def update_log(activity_id: int, log_id: int, data: SalesActivityLogUpdate, db: Session = Depends(get_db)):
    """코멘트(로그) 내용 수정 — 수정자/수정시각 기록 (v0.80.0)"""
    from datetime import datetime
    from app.models.sales_activity import SalesActivityLog
    log = db.query(SalesActivityLog).filter(
        SalesActivityLog.id == log_id,
        SalesActivityLog.activity_id == activity_id,
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="코멘트를 찾을 수 없습니다")
    log.content = data.content
    log.edited_by = data.edited_by or log.edited_by
    log.edited_at = datetime.now()
    db.commit()
    db.refresh(log)
    return log


# ==================== 코멘트 첨부(스크린샷/사진) (v0.78.0) ====================

import os  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402
from sqlalchemy.orm.attributes import flag_modified  # noqa: E402

from app.core.storage_paths import resolve_stored_path, upload_dir

# 업로드 폴더(config.json storage.upload) 아래에 저장 — 과거 경로는 resolve_stored_path 가 맞춰 준다
ACT_UPLOAD_DIR = upload_dir("sales_activities")
ACT_ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp",
                   ".xlsx", ".xls", ".doc", ".docx", ".ppt", ".pptx"}
ACT_MAX_FILE_SIZE = 200 * 1024 * 1024


def _get_activity_log(db: Session, activity_id: int, log_id: int):
    from app.models.sales_activity import SalesActivityLog
    log = db.query(SalesActivityLog).filter(
        SalesActivityLog.id == log_id,
        SalesActivityLog.activity_id == activity_id,
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="코멘트를 찾을 수 없습니다")
    return log


def _act_inline_disposition(filename: str) -> str:
    from urllib.parse import quote
    try:
        filename.encode('latin-1')
        return f'inline; filename="{filename}"'
    except UnicodeEncodeError:
        return f"inline; filename*=UTF-8''{quote(filename)}"


@router.post("/{activity_id}/logs/{log_id}/attachments")
async def upload_log_attachment(
    activity_id: int, log_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """코멘트에 스크린샷/사진/파일 첨부 (v0.78.0)"""
    try:
        log = _get_activity_log(db, activity_id, log_id)
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ACT_ALLOWED_EXT:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다. 허용: {', '.join(ACT_ALLOWED_EXT)}")
        if file.size and file.size > ACT_MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"파일이 너무 큽니다. 최대: {ACT_MAX_FILE_SIZE // 1024 // 1024}MB")
        unique_filename = f"{activity_id}_{log_id}_{uuid.uuid4().hex}{ext}"
        file_path = ACT_UPLOAD_DIR / unique_filename
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        info = {"filename": file.filename, "filepath": str(file_path),
                "mimetype": file.content_type or "application/octet-stream", "size": len(contents)}
        files = list(log.attachment_files or [])
        files.append(info)
        log.attachment_files = files
        flag_modified(log, "attachment_files")
        db.commit()
        return {"message": "첨부되었습니다.", "file": info, "total_files": len(files)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"첨부 실패: {str(e)}")


@router.get("/{activity_id}/logs/{log_id}/attachments/{file_index}/preview")
def preview_log_attachment(activity_id: int, log_id: int, file_index: int, db: Session = Depends(get_db)):
    """코멘트 첨부 미리보기(인라인)"""
    log = _get_activity_log(db, activity_id, log_id)
    files = log.attachment_files or []
    if file_index < 0 or file_index >= len(files):
        raise HTTPException(status_code=404, detail="첨부를 찾을 수 없습니다")
    info = files[file_index]
    file_path = resolve_stored_path(info["filepath"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    return FileResponse(
        path=str(file_path),
        media_type=info.get("mimetype", "application/octet-stream"),
        headers={"Content-Disposition": _act_inline_disposition(info["filename"])},
    )


@router.delete("/{activity_id}/logs/{log_id}/attachments/{file_index}")
def delete_log_attachment(activity_id: int, log_id: int, file_index: int, db: Session = Depends(get_db)):
    """코멘트 첨부 삭제"""
    log = _get_activity_log(db, activity_id, log_id)
    files = list(log.attachment_files or [])
    if file_index < 0 or file_index >= len(files):
        raise HTTPException(status_code=404, detail="첨부를 찾을 수 없습니다")
    removed = files.pop(file_index)
    try:
        resolve_stored_path(removed["filepath"]).unlink(missing_ok=True)
    except Exception:
        pass
    log.attachment_files = files
    flag_modified(log, "attachment_files")
    db.commit()
    return {"message": "삭제되었습니다.", "total_files": len(files)}


# ==================== Nextcloud 폴더 (v0.60.0) ====================

from pydantic import BaseModel, Field  # noqa: E402


class NextcloudFolderRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, description="문의건 폴더명")


@router.post("/{activity_id}/nextcloud-folder")
def create_nextcloud_folder(activity_id: int, payload: NextcloudFolderRequest,
                            db: Session = Depends(get_db)):
    """이 영업 건의 Nextcloud 폴더 생성(거래처 폴더 없으면 함께 생성) + 경로 저장."""
    from app.models.sales_activity import SalesActivity
    from app.models.business_partner import BusinessPartner
    from app.services import nextcloud_service as ncs

    if not ncs.enabled():
        raise HTTPException(status_code=400, detail="Nextcloud 연동이 설정되지 않았습니다(NEXTCLOUD_BASE_PATH)")

    act = db.query(SalesActivity).filter(SalesActivity.id == activity_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="영업활동을 찾을 수 없습니다")

    # 거래처 정보: BP 우선, 없으면 활동 자체 값
    country_code = country_name = partner_name = None
    if act.customer_id:
        bp = db.query(BusinessPartner).filter(BusinessPartner.id == act.customer_id).first()
        if bp:
            country_code, country_name, partner_name = bp.country_code, bp.country_name, bp.partner_name
    country_name = country_name or act.country
    partner_name = partner_name or act.customer_name
    if not partner_name:
        raise HTTPException(status_code=400, detail="거래처 정보가 없어 폴더 경로를 만들 수 없습니다")

    cust_rel = ncs.build_customer_relpath(country_code, country_name, partner_name)
    try:
        rel = ncs.create_project_folder(cust_rel, payload.folder_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"폴더 생성 실패: {e}")

    act.nextcloud_folder = rel
    db.commit()
    return {"folder": rel, "domestic": ncs.is_domestic(country_code, country_name)}
