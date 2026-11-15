"""
영업 문서 API 라우터
Quotation / PI / CI CRUD + 전환 + 엑셀 다운로드
"""

import os
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Response
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import require_admin, require_auth
from app.models.user import User
from app.models.sales_document import SalesDocument
from app.services.sales_document_service import SalesDocumentService
from app.schemas.sales_document import (
    SalesDocumentCreate,
    SalesDocumentUpdate,
    SalesDocumentResponse,
    SalesDocumentListItem,
    SalesDocumentListResponse,
    ConvertToNextRequest,
    ConvertMultipleRequest,
    PaymentUpdateRequest,
    PoNumberUpdateRequest,
    PoNumberUpdateResponse,
    CollectionSummary,
)

router = APIRouter(prefix="/sales-documents", tags=["영업 문서"])
# 문서 삭제 전용 — main.py 에서 module_guard 없이(로그인만) 부착. module_guard 는 DELETE 를
# sales:delete 로 추론하는데, 그 권한은 다수 역할이 보유해 삭제 판정에 쓸 수 없으므로
# 권한 판정(관리자 / CI 는 sales:ci_delete)을 엔드포인트 안에서 직접 한다.
delete_router = APIRouter(prefix="/sales-documents", tags=["영업 문서"])

# PO 첨부파일 업로드 디렉토리
from app.core.storage_paths import resolve_stored_path, upload_dir

# 업로드 폴더(config.json storage.upload) 아래에 저장 — 과거 경로는 resolve_stored_path 가 맞춰 준다
PO_UPLOAD_DIR = upload_dir("sales_documents", "po")
PO_ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".doc", ".docx", ".png", ".jpg", ".jpeg"}
PO_MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

# 운송장 업로드 디렉토리 (CI 첨부)
SHIPPING_UPLOAD_DIR = upload_dir("sales_documents", "shipping")
SHIPPING_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
SHIPPING_MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


@router.get("/payment-counts")
def get_payment_counts(
    document_type: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """문서 유형별 입금 상태 건수 (전체 기준)"""
    from sqlalchemy import func as sa_func, case, or_, and_
    from app.models.sales_document import SalesDocument
    query = db.query(
        sa_func.count(SalesDocument.id).label('total'),
        sa_func.sum(case(
            # 견적대용 PI는 미입금 집계에서 제외(실제 미수 아님)
            (and_(
                or_(SalesDocument.payment_status == 'UNPAID', SalesDocument.payment_status.is_(None), SalesDocument.payment_status == ''),
                SalesDocument.is_quote_only.is_(False),
            ), 1),
            else_=0
        )).label('unpaid'),
        sa_func.sum(case((SalesDocument.payment_status == 'PARTIAL', 1), else_=0)).label('partial'),
        sa_func.sum(case((SalesDocument.payment_status == 'PAID', 1), else_=0)).label('paid'),
    ).filter(
        SalesDocument.is_latest == True,
    )
    if document_type:
        query = query.filter(SalesDocument.document_type == document_type)
    if customer_id:
        query = query.filter(SalesDocument.customer_id == customer_id)
    r = query.first()
    return {
        "ALL": r.total or 0,
        "UNPAID": r.unpaid or 0,
        "PARTIAL": r.partial or 0,
        "PAID": r.paid or 0,
    }


@router.get("", response_model=SalesDocumentListResponse)
@router.get("/", response_model=SalesDocumentListResponse, include_in_schema=False)
def get_list(
    document_type: Optional[str] = Query(None, description="문서 유형 (QUOTATION/PI/CI)"),
    customer_id: Optional[int] = Query(None, description="고객사 ID"),
    status: Optional[str] = Query(None, description="상태 (DRAFT/SENT/CONFIRMED/CANCELLED)"),
    payment_status: Optional[str] = Query(None, description="입금 상태 필터 (UNPAID/PARTIAL/PAID)"),
    keyword: Optional[str] = Query(None, description="검색 (문서번호, PO번호)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    order_by: Optional[str] = Query(None, description="정렬 기준 (document_number/document_date/total_amount/status)"),
    order_desc: bool = Query(True, description="내림차순 여부"),
    include_old_versions: bool = Query(False, description="이전 버전 포함 여부"),
    db: Session = Depends(get_db),
):
    """영업 문서 목록 조회"""
    service = SalesDocumentService(db)
    items, total = service.get_list(
        document_type=document_type,
        customer_id=customer_id,
        status=status,
        payment_status=payment_status,
        keyword=keyword,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_desc=order_desc,
        include_old_versions=include_old_versions,
    )

    # PI 생산 진행 집계: 이 페이지의 PI들에 연결된 생산요청을 한 번에 조회(N+1 방지)
    progress_map = {}
    pi_numbers = [i.document_number for i in items if i.document_type == "PI"]
    if pi_numbers:
        from app.models.production_request import ProductionRequest
        from app.services.sales_document_service import compute_pi_production_progress
        prs = db.query(ProductionRequest).filter(
            ProductionRequest.pi_number.in_(pi_numbers),
            ProductionRequest.is_draft.is_(False),   # 초안은 아직 생산 착수 전 → 제외
        ).all()
        by_pi = {}
        for pr in prs:
            by_pi.setdefault(pr.pi_number, []).append(pr)
        for num, prlist in by_pi.items():
            progress_map[num] = compute_pi_production_progress(prlist)

    # v0.31.0: 대표 제품 정보 주입
    response_items = []
    for item in items:
        list_item = SalesDocumentListItem.model_validate(item)
        list_item.representative_product = getattr(item, '_representative_product', None)
        list_item.item_count = getattr(item, '_item_count', 0)
        if item.document_type == "PI":
            list_item.production_progress = progress_map.get(item.document_number)
        response_items.append(list_item)

    return SalesDocumentListResponse(items=response_items, total=total, skip=skip, limit=limit)


@router.get("/customer-defaults/{customer_id}")
def get_customer_defaults(customer_id: int, db: Session = Depends(get_db)):
    """고객사 문서 기본값 자동 로드 (payment terms, bank info 등)"""
    service = SalesDocumentService(db)
    defaults = service.get_customer_defaults(customer_id)
    if not defaults:
        raise HTTPException(status_code=404, detail="고객사를 찾을 수 없습니다")
    return defaults


class SuggestPriceRequest(BaseModel):
    """견적 자동산출 입력(라인 1건)."""
    order_code: str
    length_m: float = 0
    quantity: int = 1
    customer_id: Optional[int] = None
    currency: str = "KRW"
    overrides: Optional[dict] = None   # 상세 산출 패널에서 손댄 값(서버가 재계산)


@router.post("/suggest-price")
def suggest_price(req: SuggestPriceRequest, db: Session = Depends(get_db)):
    """오더코드 → 단가 자동산출 (백엔드 권위 계산, Phase 1 = 인터림 원가표).

    입력: order_code, length_m, quantity, customer_id, currency, overrides
    출력: unit_price, amount, cost_breakdown{커넥터A/B·케이블·조립비·옵션델타·기타}, applied{마진·환율·프리미엄}, warnings, parsed
    unit_price=None 이면 산출 불가(수기 입력) — warnings 참조. overrides로 각 항목 수정 시 서버가 재계산.
    """
    from app.services import quote_service
    from app.models.business_partner import BusinessPartner
    customer = None
    if req.customer_id:
        customer = db.query(BusinessPartner).filter(BusinessPartner.id == req.customer_id).first()
    config = quote_service.load_config(db)
    return quote_service.suggest_price(
        order_code=req.order_code, length_m=req.length_m, quantity=req.quantity,
        currency=req.currency, customer=customer, config=config,
        overrides=req.overrides,
    )


@router.get("/quote-config")
def get_quote_config(db: Session = Depends(get_db)):
    """견적 자동산출 설정 조회(채널마진·환율·국내프리미엄·인상률). 로그인 필요."""
    from app.services import quote_service
    return quote_service.config_to_dict(quote_service.load_config(db))


@router.put("/quote-config")
def update_quote_config(payload: dict, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """견적 자동산출 설정 저장(관리자 전용).

    payload: {channel_margins:{"2":60,...}, exchange_rate, domestic_premium,
              price_increase_global, price_increase_by_item:{CODE:%}}
    """
    from app.services import quote_service
    return quote_service.save_config(db, payload)


@router.get("/{doc_id}", response_model=SalesDocumentResponse)
def get_by_id(doc_id: int, db: Session = Depends(get_db)):
    """영업 문서 상세 조회"""
    service = SalesDocumentService(db)
    doc = service.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return doc


@router.get("/{doc_id}/remaining-quantities")
def get_pi_remaining_quantities(doc_id: int, db: Session = Depends(get_db)):
    """PI 품목별 잔여 생산요청 수량 조회"""
    service = SalesDocumentService(db)
    result = service.get_pi_remaining_quantities(doc_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


def _resolve_activity_id(db, start_doc, max_depth: int = 5):
    """문서 자체에 영업활동이 없으면 소스 체인(CI→PI→Q)을 거슬러 올라가 영업활동을 찾는다.
    CI의 sales_activity_id 가 비어도 상위 PI/Q 에 연결돼 있으면 그걸 사용."""
    if getattr(start_doc, "sales_activity_id", None):
        return start_doc.sales_activity_id
    from app.models.sales_document import SalesDocument, SalesDocumentLink
    visited = set()
    frontier = [start_doc.id]
    for _ in range(max_depth):
        rows = db.query(SalesDocumentLink.source_id).filter(
            SalesDocumentLink.target_id.in_(frontier)
        ).all()
        src_ids = [r[0] for r in rows if r[0] not in visited]
        if not src_ids:
            break
        for s in db.query(SalesDocument).filter(SalesDocument.id.in_(src_ids)).all():
            if s.sales_activity_id:
                return s.sales_activity_id
            visited.add(s.id)
        frontier = src_ids
    return None


@router.get("/{doc_id}/related")
def get_related_documents(doc_id: int, db: Session = Depends(get_db)):
    """
    연결된 문서 체인 조회 (양방향)
    - source: 이 문서의 선행 문서 (Q → PI → CI)
    - forward: 이 문서에서 파생된 다음 문서들
    - production_requests: 이 PI로 생성된 생산요청 목록
    - sales_activity: 연결된 영업활동 (v0.31.0)
    """
    from app.models.sales_document import SalesDocument
    from app.models.production_request import ProductionRequest
    from app.models.sales_activity import SalesActivity

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    result = {
        "source": None,
        "forward": [],
        "production_requests": [],
        "sales_activity": None,
    }

    # 연결된 영업활동 (없으면 소스 체인에서 조회 — CI가 직접 연결 안 돼도 상위 PI/Q 활동 표시)
    activity_id = _resolve_activity_id(db, doc)
    if activity_id:
        activity = db.query(SalesActivity).filter(SalesActivity.id == activity_id).first()
        if activity:
            result["sales_activity"] = {
                "id": activity.id,
                "title": activity.title,
                "status": activity.status,
                "customer_name": activity.customer_name,
            }

    # 선행 문서 (N:M - link 테이블 사용)
    from app.models.sales_document import SalesDocumentLink
    source_links = db.query(SalesDocumentLink).filter(SalesDocumentLink.target_id == doc_id).all()
    sources = []
    for link in source_links:
        s = db.query(SalesDocument).filter(SalesDocument.id == link.source_id).first()
        if s:
            sources.append({
                "id": s.id,
                "document_type": s.document_type,
                "document_number": s.document_number,
                "document_date": s.document_date.isoformat() if s.document_date else None,
                "status": s.status,
            })
    result["sources"] = sources
    # 하위호환: 단일 source (기존 UI용)
    if sources:
        result["source"] = sources[0]

    # 파생 문서 (이 문서가 소스인 문서들)
    forward_links = db.query(SalesDocumentLink).filter(SalesDocumentLink.source_id == doc_id).all()
    forward_docs = []
    for link in forward_links:
        d = db.query(SalesDocument).filter(SalesDocument.id == link.target_id).first()
        if d:
            forward_docs.append({
                "id": d.id,
                "document_type": d.document_type,
                "document_number": d.document_number,
                "document_date": d.document_date.isoformat() if d.document_date else None,
                "status": d.status,
            })
    result["forward"] = forward_docs

    # 이 문서가 PI인 경우: 연결된 생산요청 조회
    if doc.document_type == "PI":
        prs = db.query(ProductionRequest).filter(
            ProductionRequest.pi_number == doc.document_number
        ).all()
        result["production_requests"] = [
            {
                "id": pr.id,
                "request_number": pr.request_number,
                "status": pr.status,
                "due_date": pr.due_date.isoformat() if pr.due_date else None,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
            }
            for pr in prs
        ]

    return result


_PDF_SUPPORTED_TYPES = {"QUOTATION", "PI", "CI", "INVOICE"}


@router.get("/{doc_id}/pdf")
def download_sales_document_pdf(
    doc_id: int,
    lang: str = Query("ko", pattern="^(ko|en)$", description="언어 (ko/en). PI는 en만 지원."),
    disposition: str = Query(
        "attachment",
        pattern="^(attachment|inline)$",
        description="응답 헤더 — attachment(다운로드, 기본) / inline(브라우저 미리보기)",
    ),
    db: Session = Depends(get_db),
):
    """영업 문서 PDF 다운로드 또는 미리보기.

    지원 문서: QUOTATION (한·영), PI (영문 전용).
    CI는 다음 Phase에서.

    disposition=inline 으로 호출 시 브라우저가 PDF를 바로 렌더 (미리보기용).
    """
    import logging
    from app.schemas.quotation_pdf import Language
    from app.services.pdf.mapper import from_sales_document
    from app.services.pdf.quotation_pdf import (
        QuotationPdfRenderError,
        get_default_service,
    )

    logger = logging.getLogger(__name__)

    service = SalesDocumentService(db)
    doc = service.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    if doc.document_type not in _PDF_SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"PDF 생성은 {sorted(_PDF_SUPPORTED_TYPES)} 문서만 지원합니다 "
                   f"(현재: {doc.document_type})",
        )

    if doc.document_type in ("PI", "CI", "INVOICE") and lang != "en":
        raise HTTPException(
            status_code=400,
            detail=f"{doc.document_type} 문서는 영문(lang=en)만 지원합니다",
        )

    try:
        data = from_sales_document(doc, language=Language(lang))
        pdf_bytes = get_default_service().render(data, lang=lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except QuotationPdfRenderError as exc:
        logger.exception("PDF 생성 실패: doc_id=%s", doc_id)
        raise HTTPException(status_code=500, detail=f"PDF 생성 중 오류: {exc}")

    # Phase 3: PDF를 storage에 저장 + 메타 이력 upsert
    from app.services.sales_document_pdf_service import SalesDocumentPdfService
    from app.services.pdf.storage import PdfStorageError
    try:
        SalesDocumentPdfService(db).store_pdf(
            document_id=doc.id,
            document_number=doc.document_number,
            document_type=doc.document_type,
            document_version=doc.version or 1,
            language=lang,
            pdf_bytes=pdf_bytes,
            generated_by=None,  # TODO: 인증 도입 시 현재 사용자
        )
    except PdfStorageError as exc:
        # 저장 실패는 다운로드를 막을 정도는 아니므로 경고 로그만 남기고 진행
        logger.warning("PDF 저장 실패 (다운로드는 정상 진행): doc_id=%s err=%s", doc_id, exc)

    filename = doc.document_number
    if doc.version and doc.version > 1:
        filename = f"{filename}_v{doc.version}"
    filename = f"{filename}.pdf"

    # 파일 허브(Phase 1c): 생성 PDF를 주문 폴더 02_영업문서로 자동 사본 (best-effort)
    try:
        import os
        from app.services import nextcloud_service as ncs
        if ncs.enabled():
            # 연결된 영업대응건이 있으면 그 대응건 폴더 하나로 묶는다(문서별 폴더 생성 안 함)
            activity = None
            if getattr(doc, "sales_activity_id", None):
                from app.models.sales_activity import SalesActivity
                activity = db.query(SalesActivity).filter(SalesActivity.id == doc.sales_activity_id).first()
            order_rel = ncs.resolve_order_relpath(doc, getattr(doc, "customer", None), activity=activity)
            dirty = False
            # 대응건 폴더를 이번에 처음 계산했으면 대응건에도 저장(불변 링크 고정)
            if activity is not None and not (getattr(activity, "nextcloud_folder", None) or "").strip() \
                    and not (getattr(doc, "nextcloud_folder", None) or "").strip():
                activity.nextcloud_folder = order_rel
                dirty = True
            if not (getattr(doc, "nextcloud_folder", None) or "").strip():
                doc.nextcloud_folder = order_rel
                dirty = True
            if dirty:
                db.commit()
            ncs.save_file(os.path.join(order_rel, ncs.ORDER_SALES_DOC_SUBFOLDER), filename, pdf_bytes)
    except Exception as exc:  # 사본 실패가 다운로드를 막지 않도록
        logger.warning("Nextcloud PDF 사본 저장 실패(다운로드는 정상): doc_id=%s err=%s", doc_id, exc)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


@router.post("", response_model=SalesDocumentResponse, status_code=201)
@router.post("/", response_model=SalesDocumentResponse, status_code=201, include_in_schema=False)
def create(data: SalesDocumentCreate, db: Session = Depends(get_db)):
    """영업 문서 생성 (Q/PI/CI)"""
    service = SalesDocumentService(db)
    return service.create(data)


@router.put("/{doc_id}", response_model=SalesDocumentResponse)
def update(doc_id: int, data: SalesDocumentUpdate, db: Session = Depends(get_db)):
    """영업 문서 수정"""
    service = SalesDocumentService(db)
    doc = service.update(doc_id, data)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return doc


@router.post("/merge", response_model=SalesDocumentResponse)
def merge_documents(
    source_ids: List[int],
    db: Session = Depends(get_db),
):
    """
    같은 유형의 문서 여러 건을 합쳐서 새 문서 1건 생성 (v0.32.0)
    - CI 합배송, PI 통합 등
    - 기존 문서는 is_latest=false로 보관 (히스토리)
    """
    from decimal import Decimal
    from datetime import date
    from app.models.sales_document import SalesDocumentLink

    if not source_ids or len(source_ids) < 2:
        raise HTTPException(status_code=400, detail="2건 이상 선택하세요")

    sources = db.query(SalesDocument).filter(SalesDocument.id.in_(source_ids)).all()
    if len(sources) != len(source_ids):
        raise HTTPException(status_code=400, detail="일부 문서를 찾을 수 없습니다")

    doc_types = set(s.document_type for s in sources)
    if len(doc_types) != 1:
        raise HTTPException(status_code=400, detail="같은 유형의 문서만 합칠 수 있습니다")

    doc_type = doc_types.pop()
    primary = sources[0]

    service = SalesDocumentService(db)
    new_number = service._generate_document_number(doc_type, primary.customer_id, date.today())

    new_doc = SalesDocument(
        document_type=doc_type,
        document_number=new_number,
        document_date=date.today(),
        customer_id=primary.customer_id,
        currency=primary.currency,
        status="DRAFT",
        prepared_by=primary.prepared_by,
        prepared_email=primary.prepared_email,
        payment_terms=primary.payment_terms,
        delivery_terms=primary.delivery_terms,
        hs_code=primary.hs_code,
        country_of_origin=primary.country_of_origin,
        bank_name=primary.bank_name,
        bank_address=primary.bank_address,
        swift_code=primary.swift_code,
        account_name=primary.account_name,
        account_number=primary.account_number,
        version=1,
        is_latest=True,
        version_group=new_number,
    )
    db.add(new_doc)
    db.flush()

    line_no = 1
    total_amount = Decimal("0")
    for src in sources:
        for item in sorted(src.items or [], key=lambda x: x.line_no or 0):
            from app.models.sales_document import SalesDocumentItem
            new_item = SalesDocumentItem(
                document_id=new_doc.id,
                line_no=line_no,
                product_code=item.product_code,
                description=item.description,
                quantity=item.quantity,
                uom=item.uom,
                unit_price=item.unit_price,
                amount=item.amount,
                currency=item.currency,
                line_remarks=item.line_remarks,
            )
            db.add(new_item)
            total_amount += item.amount or Decimal("0")
            line_no += 1

    new_doc.total_amount = total_amount

    # 기존 문서 히스토리 보관
    for src in sources:
        src.is_latest = False

    # 기존 문서의 소스 링크도 새 문서에 연결
    for src in sources:
        existing_links = db.query(SalesDocumentLink).filter(SalesDocumentLink.target_id == src.id).all()
        for link in existing_links:
            db.add(SalesDocumentLink(source_id=link.source_id, target_id=new_doc.id))

    db.commit()
    db.refresh(new_doc)
    return new_doc


@delete_router.delete("/{doc_id}", status_code=204)
def delete(
    doc_id: int,
    force: bool = Query(False, description="강제 삭제 (데이터 정리용, 모든 상태 삭제 가능)"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """영업 문서 삭제 — 관리자는 전체, CI 는 'CI 삭제'(sales:ci_delete) 권한자도 가능"""
    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    if user.role != "ADMIN":
        from app.services.rbac_service import has_permission
        if not (doc.document_type == "CI" and has_permission(db, user, "sales:ci_delete")):
            raise HTTPException(
                status_code=403,
                detail="삭제 권한이 없습니다 (CI는 'CI 삭제' 권한 필요, 견적·PI는 관리자 전용)",
            )
    service = SalesDocumentService(db)
    if not service.delete(doc_id, force=force):
        raise HTTPException(status_code=400, detail="삭제할 수 없는 문서입니다")


@router.post("/{doc_id}/status/{new_status}", response_model=SalesDocumentResponse)
def update_status(doc_id: int, new_status: str, db: Session = Depends(get_db)):
    """문서 상태 변경 (DRAFT→SENT→CONFIRMED / CANCELLED)"""
    valid_statuses = {"DRAFT", "SENT", "CONFIRMED", "CANCELLED"}
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 상태: {new_status}")
    service = SalesDocumentService(db)
    doc = service.update_status(doc_id, new_status)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return doc


@router.post("/{doc_id}/link-activity")
def link_activity(
    doc_id: int,
    activity_id: int = Query(..., description="영업활동 ID"),
    db: Session = Depends(get_db),
):
    """문서에 영업활동 연결 (연결된 문서 체인도 자동 연결)"""
    from app.models.sales_document import SalesDocument, SalesDocumentLink

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    # 연결 대상 문서 수집 (자신 + 체인 전체)
    linked_ids = set()
    linked_ids.add(doc_id)

    def collect_chain(did):
        # forward (이 문서가 소스인 것)
        forwards = db.query(SalesDocumentLink).filter(SalesDocumentLink.source_id == did).all()
        for link in forwards:
            if link.target_id not in linked_ids:
                linked_ids.add(link.target_id)
                collect_chain(link.target_id)
        # backward (이 문서가 타겟인 것)
        backwards = db.query(SalesDocumentLink).filter(SalesDocumentLink.target_id == did).all()
        for link in backwards:
            if link.source_id not in linked_ids:
                linked_ids.add(link.source_id)
                collect_chain(link.source_id)

    collect_chain(doc_id)

    # 전체 체인에 activity_id 설정
    updated = db.query(SalesDocument).filter(
        SalesDocument.id.in_(linked_ids)
    ).update({"sales_activity_id": activity_id}, synchronize_session=False)

    db.commit()

    return {
        "id": doc.id,
        "document_number": doc.document_number,
        "sales_activity_id": activity_id,
        "linked_count": updated,
    }


@router.post("/{doc_id}/shipment-date")
def update_shipment_date(
    doc_id: int,
    shipment_date: Optional[str] = Query(None, description="선적일자 (YYYY-MM-DD, 비우면 해제)"),
    db: Session = Depends(get_db),
):
    """CI 출고일자(선적일자) 설정/해제"""
    from datetime import date as date_type
    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    if shipment_date:
        try:
            doc.shipment_date = date_type.fromisoformat(shipment_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")
    else:
        doc.shipment_date = None
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "document_number": doc.document_number, "shipment_date": doc.shipment_date.isoformat() if doc.shipment_date else None}


@router.post("/{doc_id}/convert", response_model=SalesDocumentResponse)
def convert_to_next(doc_id: int, data: ConvertToNextRequest, db: Session = Depends(get_db)):
    """
    문서 전환
    - Q → PI (고객 PO 수령 시)
    - PI → CI (출하 시)

    원본 문서 데이터가 복사되고, 원본은 CONFIRMED로 변경됨
    """
    service = SalesDocumentService(db)
    new_doc = service.convert_to_next(doc_id, data)
    if not new_doc:
        raise HTTPException(status_code=400, detail="전환할 수 없는 문서입니다")
    return new_doc


@router.post("/convert-multiple", response_model=SalesDocumentResponse)
def convert_multiple_to_next(
    req: ConvertMultipleRequest,
    db: Session = Depends(get_db),
):
    """
    다중 문서 전환 (N:M, v0.32.0)
    - 여러 Q → 1 PI (통합 PI)
    - 여러 PI → 1 CI (합배송 CI)
    - 1개만 보내도 정상 동작
    """
    convert_data = ConvertToNextRequest(
        customer_po_number=req.customer_po_number,
        customer_po_date=req.customer_po_date,
        po_attachment_files=req.po_attachment_files,
        document_date=req.document_date,
        target_type=req.target_type,
    )
    service = SalesDocumentService(db)
    new_doc = service.convert_multiple_to_next(req.source_ids, convert_data)
    if not new_doc:
        raise HTTPException(status_code=400, detail="전환할 수 없는 문서입니다. 같은 유형의 문서만 선택하세요.")
    return new_doc


@router.get("/{doc_id}/versions")
def get_document_versions(doc_id: int, db: Session = Depends(get_db)):
    """문서의 모든 버전 이력 조회 (v0.32.0)"""
    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    group = doc.version_group or doc.document_number
    versions = db.query(SalesDocument).filter(
        SalesDocument.version_group == group
    ).order_by(SalesDocument.version.desc()).all()
    return [
        {
            "id": v.id,
            "document_number": v.document_number,
            "version": v.version,
            "is_latest": v.is_latest,
            "status": v.status,
            "total_amount": float(v.total_amount) if v.total_amount else 0,
            "currency": v.currency,
            "document_date": v.document_date.isoformat() if v.document_date else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.get("/{doc_id}/process-status")
def get_pi_process_status(doc_id: int, db: Session = Depends(get_db)):
    """PI 영업 프로세스 진행 상태 조회 (PI발송→입금→생산요청→생산완료→CI→출하)"""
    service = SalesDocumentService(db)
    result = service.get_pi_process_status(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="PI 문서를 찾을 수 없습니다")
    return result


@router.post("/{doc_id}/create-production-request-draft")
def create_production_request_draft(doc_id: int, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    """
    PI 문서에서 생산요청 초안 자동 생성
    PI 데이터(고객, PI/PO번호, 품목, 수량)를 자동 채움
    → 영업팀이 특이사항/도면 추가 후 제출. 생성자(영업담당자)=로그인 사용자로 기록.
    """
    service = SalesDocumentService(db)
    result = service.create_production_request_draft(doc_id, actor_id=user.id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "생산요청 초안 생성 실패"))
    return result


@router.get("/{doc_id}/export/excel")
def export_excel(doc_id: int, db: Session = Depends(get_db)):
    """영업 문서를 엑셀 파일로 다운로드 (기존 양식 기반)"""
    service = SalesDocumentService(db)
    doc = service.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    from app.services.sales_excel_service import SalesExcelService
    excel_service = SalesExcelService()
    output = excel_service.generate(doc)

    filename = f"{doc.document_number}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.xlsx",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==================== 수금 관리 (Phase 3) ====================

@router.post("/{doc_id}/payment", response_model=SalesDocumentResponse)
def update_payment(doc_id: int, data: PaymentUpdateRequest, db: Session = Depends(get_db)):
    """입금 상태 변경 (영업 담당자 수동 입력)"""
    valid = {"UNPAID", "PARTIAL", "PAID"}
    if data.payment_status not in valid:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 입금 상태: {data.payment_status}")
    service = SalesDocumentService(db)
    doc = service.update_payment(
        doc_id,
        payment_status=data.payment_status,
        paid_amount=data.paid_amount,
        paid_date=data.paid_date,
        payment_remarks=data.payment_remarks,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return doc


@router.patch("/{doc_id}/po-number", response_model=PoNumberUpdateResponse)
def update_po_number(doc_id: int, data: PoNumberUpdateRequest, db: Session = Depends(get_db)):
    """고객 PO 번호 정정 — 이미 발행된 문서도 버전 생성 없이 제자리 수정.

    고객사가 잘못 준 PO 번호를 바로잡는 용도. 일반 수정(PUT /{doc_id})은
    SENT/CONFIRMED 문서에 새 버전을 만들어 문서번호가 재발행되고 상태가
    DRAFT 로 돌아가는데, PO 번호는 고객측 참조값이라 그럴 이유가 없다.
    문서번호·상태·금액·품목은 건드리지 않는다.
    """
    service = SalesDocumentService(db)
    doc, count = service.update_po_number(
        doc_id,
        customer_po_number=(data.customer_po_number or None),
        customer_po_date=data.customer_po_date,
        cascade=data.cascade,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    return PoNumberUpdateResponse(document=doc, updated_count=count)


@router.get("/collection/summary", response_model=CollectionSummary)
def get_collection_summary(db: Session = Depends(get_db)):
    """수금 현황 요약 (PI 기준)"""
    service = SalesDocumentService(db)
    return service.get_collection_summary()


@router.get("/collection/documents")
def get_collection_documents(db: Session = Depends(get_db)):
    """수금 현황 목록 (PI 기준) + 배송완료 여부 — '배송 후 미수' 예외 식별용"""
    service = SalesDocumentService(db)
    return {"items": service.get_collection_documents()}


# ==================== 고객별 가격 이력 ====================

@router.get("/price-history/{customer_id}")
def get_customer_price_history(
    customer_id: int,
    product_code: Optional[str] = Query(None, description="제품 코드 필터"),
    db: Session = Depends(get_db),
):
    """
    고객별 제품 가격 이력 조회
    해당 고객에게 보낸 모든 Q/PI/CI의 제품별 가격 이력
    """
    service = SalesDocumentService(db)
    return service.get_customer_price_history(customer_id, product_code)


@router.get("/last-price/{customer_id}/{product_code}")
def get_last_quoted_price(
    customer_id: int,
    product_code: str,
    db: Session = Depends(get_db),
):
    """
    특정 고객 × 특정 제품의 마지막 견적 가격 조회
    견적 작성 시 이전 가격 비교용
    """
    service = SalesDocumentService(db)
    result = service.get_last_quoted_price(customer_id, product_code)
    if not result:
        return {"found": False, "message": "이전 견적 이력 없음"}
    return {"found": True, **result}


# ==================== PO 첨부파일 ====================

@router.post("/{doc_id}/po-attachments")
async def upload_po_attachment(
    doc_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """PO 파일 업로드 (PI/CI 문서에 첨부)"""
    from app.models.sales_document import SalesDocument

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in PO_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {file_ext}"
        )

    if file.size and file.size > PO_MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일이 200MB를 초과합니다")

    unique_filename = f"{doc_id}_{uuid.uuid4().hex}{file_ext}"
    file_path = PO_UPLOAD_DIR / unique_filename

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    attachment_info = {
        "filename": file.filename,
        "filepath": str(file_path),
        "mimetype": file.content_type or "application/octet-stream",
        "size": len(contents),
    }

    current_files = doc.po_attachment_files or []
    current_files.append(attachment_info)
    doc.po_attachment_files = current_files
    flag_modified(doc, "po_attachment_files")
    db.commit()

    return {"message": "PO 파일이 업로드되었습니다", "file": attachment_info, "total_files": len(current_files)}


@router.delete("/{doc_id}/po-attachments/{file_index}")
def delete_po_attachment(doc_id: int, file_index: int, db: Session = Depends(get_db)):
    """PO 첨부파일 삭제"""
    from app.models.sales_document import SalesDocument

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    current_files = doc.po_attachment_files or []
    if file_index < 0 or file_index >= len(current_files):
        raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다")

    file_info = current_files[file_index]
    fp = resolve_stored_path(file_info["filepath"])
    if fp.exists():
        fp.unlink()

    current_files.pop(file_index)
    doc.po_attachment_files = current_files
    flag_modified(doc, "po_attachment_files")
    db.commit()
    return {"message": "삭제되었습니다", "remaining": len(current_files)}


@router.get("/{doc_id}/po-attachments/{file_index}/download")
def download_po_attachment(doc_id: int, file_index: int, db: Session = Depends(get_db)):
    """PO 첨부파일 다운로드"""
    from app.models.sales_document import SalesDocument

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    current_files = doc.po_attachment_files or []
    if file_index < 0 or file_index >= len(current_files):
        raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다")

    file_info = current_files[file_index]
    fp = resolve_stored_path(file_info["filepath"])
    if not fp.exists():
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")

    return FileResponse(
        path=str(fp),
        filename=file_info["filename"],
        media_type=file_info.get("mimetype", "application/octet-stream"),
    )


# ==================== 운송장 첨부 (CI 전용) ====================

@router.post("/{doc_id}/shipping-invoices")
async def upload_shipping_invoice(
    doc_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """운송장 파일 업로드 (CI 문서에 첨부, PDF/이미지)"""
    from app.models.sales_document import SalesDocument
    from datetime import datetime

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in SHIPPING_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {file_ext} (PDF/PNG/JPG만 가능)"
        )

    if file.size and file.size > SHIPPING_MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일이 200MB를 초과합니다")

    unique_filename = f"{doc_id}_{uuid.uuid4().hex}{file_ext}"
    file_path = SHIPPING_UPLOAD_DIR / unique_filename

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    attachment_info = {
        "filename": file.filename,
        "filepath": str(file_path),
        "mimetype": file.content_type or "application/octet-stream",
        "size": len(contents),
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    current_files = doc.shipping_invoice_files or []
    current_files.append(attachment_info)
    doc.shipping_invoice_files = current_files
    flag_modified(doc, "shipping_invoice_files")
    db.commit()

    return {"message": "운송장이 업로드되었습니다", "file": attachment_info, "total_files": len(current_files)}


@router.delete("/{doc_id}/shipping-invoices/{file_index}")
def delete_shipping_invoice(doc_id: int, file_index: int, db: Session = Depends(get_db)):
    """운송장 삭제"""
    from app.models.sales_document import SalesDocument

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    current_files = doc.shipping_invoice_files or []
    if file_index < 0 or file_index >= len(current_files):
        raise HTTPException(status_code=404, detail="운송장을 찾을 수 없습니다")

    file_info = current_files[file_index]
    fp = resolve_stored_path(file_info["filepath"])
    if fp.exists():
        fp.unlink()

    current_files.pop(file_index)
    doc.shipping_invoice_files = current_files
    flag_modified(doc, "shipping_invoice_files")
    db.commit()
    return {"message": "삭제되었습니다", "remaining": len(current_files)}


@router.get("/{doc_id}/shipping-invoices/{file_index}/preview")
def preview_shipping_invoice(doc_id: int, file_index: int, db: Session = Depends(get_db)):
    """운송장 미리보기 (브라우저 inline 표시)"""
    from app.models.sales_document import SalesDocument
    from urllib.parse import quote

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    current_files = doc.shipping_invoice_files or []
    if file_index < 0 or file_index >= len(current_files):
        raise HTTPException(status_code=404, detail="운송장을 찾을 수 없습니다")

    file_info = current_files[file_index]
    fp = resolve_stored_path(file_info["filepath"])
    if not fp.exists():
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")

    filename = file_info["filename"]
    try:
        filename.encode('latin-1')
        disposition = f"inline; filename=\"{filename}\""
    except UnicodeEncodeError:
        encoded = quote(filename)
        disposition = f"inline; filename*=UTF-8''{encoded}"

    return FileResponse(
        path=str(fp),
        media_type=file_info.get("mimetype", "application/octet-stream"),
        headers={"Content-Disposition": disposition},
    )


@router.get("/{doc_id}/shipping-invoices/{file_index}/download")
def download_shipping_invoice(doc_id: int, file_index: int, db: Session = Depends(get_db)):
    """운송장 다운로드"""
    from app.models.sales_document import SalesDocument

    doc = db.query(SalesDocument).filter(SalesDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    current_files = doc.shipping_invoice_files or []
    if file_index < 0 or file_index >= len(current_files):
        raise HTTPException(status_code=404, detail="운송장을 찾을 수 없습니다")

    file_info = current_files[file_index]
    fp = resolve_stored_path(file_info["filepath"])
    if not fp.exists():
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")

    return FileResponse(
        path=str(fp),
        filename=file_info["filename"],
        media_type=file_info.get("mimetype", "application/octet-stream"),
    )


# ==================== 영업 데이터 집계 (v0.32.0) ====================

@router.get("/analytics/summary")
def get_sales_analytics(
    year: int = Query(None, description="연도 (기본: 올해)"),
    db: Session = Depends(get_db),
):
    """
    영업 데이터 집계 API
    - 이달/다음달 예상 매출
    - 미입금 금액
    - 월별 매출 추이 (12개월)
    - 거래처별 매출 랭킹
    - 문서 유형별 현황
    - 담당자별 실적
    """
    from sqlalchemy import func as sa_func, extract, case, and_
    from datetime import date, timedelta
    from app.models.sales_document import SalesDocument
    from app.models.sales_activity import SalesActivity
    from app.models.business_partner import BusinessPartner

    today = date.today()
    target_year = year or today.year
    this_month = today.month

    # === 1. 이달 매출 (CI 기준) ===
    this_month_ci = db.query(
        sa_func.coalesce(sa_func.sum(SalesDocument.total_amount), 0),
        sa_func.count(SalesDocument.id),
    ).filter(
        SalesDocument.document_type == "CI",
        SalesDocument.is_latest == True,
        SalesDocument.status != "CANCELLED",
        extract('year', SalesDocument.document_date) == target_year,
        extract('month', SalesDocument.document_date) == this_month,
    ).first()

    # === 2. 다음달 예상 (CI + 파이프라인) ===
    next_month = this_month + 1 if this_month < 12 else 1
    next_year = target_year if this_month < 12 else target_year + 1
    next_month_ci = db.query(
        sa_func.coalesce(sa_func.sum(SalesDocument.total_amount), 0),
        sa_func.count(SalesDocument.id),
    ).filter(
        SalesDocument.document_type == "CI",
        SalesDocument.is_latest == True,
        SalesDocument.status != "CANCELLED",
        extract('year', SalesDocument.document_date) == next_year,
        extract('month', SalesDocument.document_date) == next_month,
    ).first()

    # 진행중 영업활동의 예상 금액 합계 (다음달 잠재 매출)
    pipeline_amount = db.query(
        sa_func.coalesce(sa_func.sum(SalesActivity.expected_amount), 0),
    ).filter(
        SalesActivity.status == "IN_PROGRESS",
    ).scalar() or 0

    # === 3. 미입금 PI ===
    unpaid = db.query(
        sa_func.coalesce(sa_func.sum(SalesDocument.total_amount), 0),
        sa_func.count(SalesDocument.id),
    ).filter(
        SalesDocument.document_type == "PI",
        SalesDocument.is_latest == True,
        SalesDocument.status != "CANCELLED",
        SalesDocument.is_quote_only == False,  # 견적 대용 PI 제외  # noqa: E712
        SalesDocument.payment_status.in_(["UNPAID", None, ""]),
    ).first()

    partial_paid = db.query(
        sa_func.coalesce(sa_func.sum(SalesDocument.total_amount - sa_func.coalesce(SalesDocument.paid_amount, 0)), 0),
        sa_func.count(SalesDocument.id),
    ).filter(
        SalesDocument.document_type == "PI",
        SalesDocument.is_latest == True,
        SalesDocument.is_quote_only == False,  # 견적 대용 PI 제외  # noqa: E712
        SalesDocument.payment_status == "PARTIAL",
    ).first()

    # === 3.5 미실현 매출 (확정 주문 대기분) ===
    # 정의: 상태가 CONFIRMED(주문 확정)인 PI 중, 아직 CI가 발행되지 않은 것.
    #  - CI 발행 = 매출 실현이므로, "PI는 확정됐는데 CI 미발행" = 앞으로 실현될 매출.
    #  - 견적 대용 PI(is_quote_only)는 제외. SENT/DRAFT PI는 확정 전이라 제외.
    from sqlalchemy.orm import aliased
    from app.models.sales_document import SalesDocumentLink
    CIDoc = aliased(SalesDocument)
    PISrc = aliased(SalesDocument)

    # CI로 전환(발행)된 PI들의 version_group 집합 — N:M 링크 + source_document_id(레거시) 양쪽 수집
    converted_vgs = set()
    link_rows = db.query(
        sa_func.coalesce(PISrc.version_group, PISrc.document_number)
    ).select_from(SalesDocumentLink).join(
        CIDoc, SalesDocumentLink.target_id == CIDoc.id
    ).join(
        PISrc, SalesDocumentLink.source_id == PISrc.id
    ).filter(
        CIDoc.document_type == "CI",
        CIDoc.status != "CANCELLED",
        PISrc.document_type == "PI",
    ).distinct().all()
    legacy_rows = db.query(
        sa_func.coalesce(PISrc.version_group, PISrc.document_number)
    ).select_from(CIDoc).join(
        PISrc, CIDoc.source_document_id == PISrc.id
    ).filter(
        CIDoc.document_type == "CI",
        CIDoc.status != "CANCELLED",
        PISrc.document_type == "PI",
    ).distinct().all()
    for (vg,) in list(link_rows) + list(legacy_rows):
        if vg:
            converted_vgs.add(vg)

    unrealized_filters = [
        SalesDocument.document_type == "PI",
        SalesDocument.is_latest == True,
        SalesDocument.status == "CONFIRMED",
        SalesDocument.is_quote_only == False,  # 견적 대용 PI 제외  # noqa: E712
        extract('year', SalesDocument.document_date) == target_year,
    ]
    if converted_vgs:
        unrealized_filters.append(
            sa_func.coalesce(SalesDocument.version_group, SalesDocument.document_number).notin_(list(converted_vgs))
        )
    unrealized_row = db.query(
        sa_func.coalesce(sa_func.sum(SalesDocument.total_amount), 0),
        sa_func.count(SalesDocument.id),
    ).filter(*unrealized_filters).first()
    unrealized_amount = float(unrealized_row[0] or 0)
    unconverted_pi_count = unrealized_row[1] or 0

    # === 4. 월별 매출 추이 (CI 기준, 최근 12개월) ===
    twelve_months_ago = today.replace(day=1) - timedelta(days=365)
    monthly_data = db.query(
        sa_func.to_char(SalesDocument.document_date, 'YYYY-MM').label('month'),
        SalesDocument.document_type,
        sa_func.sum(SalesDocument.total_amount).label('amount'),
        sa_func.count(SalesDocument.id).label('count'),
    ).filter(
        SalesDocument.is_latest == True,
        SalesDocument.status != "CANCELLED",
        SalesDocument.document_date >= twelve_months_ago,
    ).group_by('month', SalesDocument.document_type).order_by('month').all()

    monthly_map = {}
    for row in monthly_data:
        m = row.month
        if m not in monthly_map:
            monthly_map[m] = {"month": m, "quotation_amount": 0, "quotation_count": 0,
                              "pi_amount": 0, "pi_count": 0, "ci_amount": 0, "ci_count": 0}
        key = row.document_type.lower()
        monthly_map[m][f"{key}_amount"] = float(row.amount or 0)
        monthly_map[m][f"{key}_count"] = row.count

    monthly_trend = sorted(monthly_map.values(), key=lambda x: x["month"])

    # === 5. 거래처별 매출 랭킹 (CI 기준, 올해) ===
    customer_ranking = db.query(
        BusinessPartner.partner_name,
        BusinessPartner.country_name,
        sa_func.sum(SalesDocument.total_amount).label('total'),
        sa_func.count(SalesDocument.id).label('count'),
    ).join(
        BusinessPartner, SalesDocument.customer_id == BusinessPartner.id
    ).filter(
        SalesDocument.document_type == "CI",
        SalesDocument.is_latest == True,
        SalesDocument.status != "CANCELLED",
        extract('year', SalesDocument.document_date) == target_year,
    ).group_by(BusinessPartner.partner_name, BusinessPartner.country_name
    ).order_by(sa_func.sum(SalesDocument.total_amount).desc()
    ).limit(10).all()

    # === 6. 담당자별 실적 (영업활동 기준) ===
    assignee_stats = db.query(
        SalesActivity.assigned_to,
        sa_func.count(SalesActivity.id).label('activity_count'),
        sa_func.sum(case(
            (SalesActivity.status == "COMPLETED", 1), else_=0
        )).label('completed_count'),
        sa_func.sum(case(
            (SalesActivity.status == "IN_PROGRESS", 1), else_=0
        )).label('in_progress_count'),
    ).filter(
        SalesActivity.assigned_to.isnot(None),
        SalesActivity.assigned_to != "",
    ).group_by(SalesActivity.assigned_to).all()

    # === 7. 연간 누적 (CI 기준) ===
    yearly_total = db.query(
        sa_func.coalesce(sa_func.sum(SalesDocument.total_amount), 0),
        sa_func.count(SalesDocument.id),
    ).filter(
        SalesDocument.document_type == "CI",
        SalesDocument.is_latest == True,
        SalesDocument.status != "CANCELLED",
        extract('year', SalesDocument.document_date) == target_year,
    ).first()

    # === 8. 견적 전환율 ===
    total_quotations = db.query(sa_func.count(SalesDocument.id)).filter(
        SalesDocument.document_type == "QUOTATION",
        extract('year', SalesDocument.document_date) == target_year,
    ).scalar() or 0
    confirmed_quotations = db.query(sa_func.count(SalesDocument.id)).filter(
        SalesDocument.document_type == "QUOTATION",
        SalesDocument.status == "CONFIRMED",
        extract('year', SalesDocument.document_date) == target_year,
    ).scalar() or 0

    return {
        "year": target_year,
        "this_month": {
            "month": f"{target_year}-{this_month:02d}",
            "ci_amount": float(this_month_ci[0]),
            "ci_count": this_month_ci[1],
        },
        "next_month": {
            "month": f"{next_year}-{next_month:02d}",
            "ci_amount": float(next_month_ci[0]),
            "ci_count": next_month_ci[1],
            "pipeline_amount": float(pipeline_amount),
        },
        "unpaid": {
            "total_amount": float(unpaid[0]) + float(partial_paid[0]),
            "unpaid_count": unpaid[1],
            "partial_count": partial_paid[1],
        },
        "unrealized": {
            "unrealized_amount": unrealized_amount,
            "unconverted_pi_count": unconverted_pi_count,
        },
        "yearly_total": {
            "ci_amount": float(yearly_total[0]),
            "ci_count": yearly_total[1],
        },
        "conversion_rate": {
            "total_quotations": total_quotations,
            "confirmed_quotations": confirmed_quotations,
            "rate": round(confirmed_quotations / total_quotations * 100, 1) if total_quotations > 0 else 0,
        },
        "monthly_trend": monthly_trend,
        "customer_ranking": [
            {"name": r.partner_name, "country": r.country_name, "amount": float(r.total), "count": r.count}
            for r in customer_ranking
        ],
        "assignee_stats": [
            {"name": r.assigned_to, "total": r.activity_count, "completed": r.completed_count, "in_progress": r.in_progress_count}
            for r in assignee_stats
        ],
    }


# ==================== 엑셀 일괄 업로드 (v0.32.0) ====================

@router.get("/bulk/template")
def download_bulk_template():
    """Q/PI/CI 일괄 등록용 엑셀 템플릿 다운로드"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from io import BytesIO

    wb = Workbook()

    # Sheet 1: 문서
    ws1 = wb.active
    ws1.title = "문서"
    headers1 = ["document_type", "document_number", "document_date", "customer_code", "customer_name",
                 "currency", "total_amount", "status", "payment_status",
                 "customer_po_number", "payment_terms", "delivery_terms",
                 "prepared_by", "remarks"]
    labels1 = ["문서유형*", "문서번호*", "문서날짜*", "거래처코드*", "거래처명(참고)",
                "통화", "총금액", "상태", "입금상태",
                "PO번호", "결제조건", "납품조건",
                "작성자", "비고"]

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    thin = Side(style="thin")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)

    for col, (h, l) in enumerate(zip(headers1, labels1), 1):
        cell = ws1.cell(row=1, column=col, value=l)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal="center")

    # 예시 데이터
    example1 = ["QUOTATION", "Q-HT260115", "2026-01-15", "HT", "HTL Limited",
                 "USD", "15000.00", "CONFIRMED", "",
                 "", "100% in advance", "EXW Seoul",
                 "유현성", ""]
    example2 = ["PI", "PI-HT260120", "2026-01-20", "HT", "HTL Limited",
                 "USD", "15000.00", "CONFIRMED", "PAID",
                 "PO-12345", "100% in advance", "EXW Seoul",
                 "유현성", ""]
    for col, v in enumerate(example1, 1):
        ws1.cell(row=2, column=col, value=v).font = Font(color="808080", italic=True)
    for col, v in enumerate(example2, 1):
        ws1.cell(row=3, column=col, value=v).font = Font(color="808080", italic=True)

    for col in range(1, len(headers1) + 1):
        ws1.column_dimensions[ws1.cell(row=1, column=col).column_letter].width = 16

    # 안내 행
    ws1.cell(row=5, column=1, value="※ document_type: QUOTATION / PI / CI").font = Font(color="FF0000", size=9)
    ws1.cell(row=6, column=1, value="※ customer_code: 거래처 관리의 거래처 코드 (예: HT, OT, TL). 거래처명은 참고용").font = Font(color="FF0000", size=9)
    ws1.cell(row=7, column=1, value="※ status: DRAFT / SENT / CONFIRMED / CANCELLED").font = Font(color="FF0000", size=9)
    ws1.cell(row=8, column=1, value="※ payment_status: UNPAID / PARTIAL / PAID (PI만 해당)").font = Font(color="FF0000", size=9)
    ws1.cell(row=9, column=1, value="※ document_date: YYYY-MM-DD 형식").font = Font(color="FF0000", size=9)
    ws1.cell(row=10, column=1, value="※ 회색 이탤릭 행은 예시입니다. 삭제하고 실제 데이터를 입력하세요.").font = Font(color="FF0000", size=9)

    # Sheet 2: 품목
    ws2 = wb.create_sheet("품목")
    headers2 = ["document_number", "line_no", "product_code", "description",
                 "quantity", "uom", "unit_price", "amount", "currency", "line_remarks"]
    labels2 = ["문서번호*", "순번*", "제품코드*", "제품설명",
                "수량*", "단위", "단가*", "금액", "통화", "비고"]

    for col, (h, l) in enumerate(zip(headers2, labels2), 1):
        cell = ws2.cell(row=1, column=col, value=l)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal="center")

    example_item1 = ["Q-HT260115", "1", "HXB13-PSD-B-O4-S1-D38", "Plug with Dust Cap\n-4CH OM3 Multimode",
                      "10", "EA", "150.00", "1500.00", "USD", ""]
    example_item2 = ["Q-HT260115", "2", "HXB13-RJS-B-O4-S1-D58", "Receptacle with LC\n-4CH OM3",
                      "5", "EA", "200.00", "1000.00", "USD", ""]
    for col, v in enumerate(example_item1, 1):
        ws2.cell(row=2, column=col, value=v).font = Font(color="808080", italic=True)
    for col, v in enumerate(example_item2, 1):
        ws2.cell(row=3, column=col, value=v).font = Font(color="808080", italic=True)

    for col in range(1, len(headers2) + 1):
        ws2.column_dimensions[ws2.cell(row=1, column=col).column_letter].width = 18

    ws2.cell(row=5, column=1, value="※ document_number는 '문서' 시트의 문서번호와 일치해야 합니다").font = Font(color="FF0000", size=9)
    ws2.cell(row=6, column=1, value="※ amount는 비워두면 수량×단가로 자동 계산됩니다").font = Font(color="FF0000", size=9)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sales_document_bulk_template.xlsx"},
    )


@router.post("/bulk/upload")
async def bulk_upload_sales_documents(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Q/PI/CI 일괄 업로드
    엑셀 파일의 '문서' + '품목' 시트를 읽어서 일괄 생성
    """
    from openpyxl import load_workbook
    from datetime import date as date_type
    from decimal import Decimal
    from app.models.sales_document import SalesDocument, SalesDocumentItem
    from app.models.business_partner import BusinessPartner

    content = await file.read()
    from io import BytesIO
    wb = load_workbook(BytesIO(content))

    # Sheet 1: 문서
    ws1 = wb["문서"] if "문서" in wb.sheetnames else wb.worksheets[0]
    ws2 = wb["품목"] if "품목" in wb.sheetnames else wb.worksheets[1] if len(wb.worksheets) > 1 else None

    results = []
    doc_map = {}  # document_number → SalesDocument id

    # 거래처코드 → ID 매핑 캐시
    partner_cache = {}
    def get_partner_id(code):
        if not code:
            return None
        code = str(code).strip()
        if code in partner_cache:
            return partner_cache[code]
        bp = db.query(BusinessPartner).filter(
            BusinessPartner.partner_code == code
        ).first()
        pid = bp.id if bp else None
        partner_cache[code] = pid
        return pid

    # 문서 읽기 (2행부터)
    doc_count = 0
    doc_skip = 0
    for row in ws1.iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue
        doc_type = str(row[0]).strip().upper()
        doc_number = str(row[1]).strip()
        if doc_type not in ("QUOTATION", "PI", "CI"):
            continue

        # 중복 체크
        existing = db.query(SalesDocument).filter(SalesDocument.document_number == doc_number).first()
        if existing:
            doc_map[doc_number] = existing.id
            doc_skip += 1
            results.append({"document_number": doc_number, "status": "skipped", "message": "이미 존재"})
            continue

        # 날짜 파싱
        doc_date_raw = row[2]
        if isinstance(doc_date_raw, date_type):
            doc_date = doc_date_raw
        elif doc_date_raw:
            try:
                doc_date = date_type.fromisoformat(str(doc_date_raw).strip()[:10])
            except ValueError:
                doc_date = date_type.today()
        else:
            doc_date = date_type.today()

        customer_code = str(row[3]).strip() if row[3] else ""
        customer_name = str(row[4]).strip() if row[4] else ""
        customer_id = get_partner_id(customer_code)
        currency = str(row[5]).strip() if row[5] else "USD"
        total_amount = Decimal(str(row[6])) if row[6] else Decimal("0")
        status = str(row[7]).strip().upper() if row[7] else "DRAFT"
        payment_status = str(row[8]).strip().upper() if row[8] else None
        po_number = str(row[9]).strip() if row[9] else None
        payment_terms = str(row[10]).strip() if row[10] else None
        delivery_terms = str(row[11]).strip() if row[11] else None
        prepared_by = str(row[12]).strip() if row[12] else None
        remarks = str(row[13]).strip() if len(row) > 13 and row[13] else None

        doc = SalesDocument(
            document_type=doc_type,
            document_number=doc_number,
            document_date=doc_date,
            customer_id=customer_id,
            currency=currency,
            total_amount=total_amount,
            status=status if status in ("DRAFT", "SENT", "CONFIRMED", "CANCELLED") else "DRAFT",
            payment_status=payment_status if payment_status in ("UNPAID", "PARTIAL", "PAID") else None,
            customer_po_number=po_number,
            payment_terms=payment_terms,
            delivery_terms=delivery_terms,
            prepared_by=prepared_by,
            remarks=remarks,
            version=1,
            is_latest=True,
            version_group=doc_number,
        )
        db.add(doc)
        db.flush()
        doc_map[doc_number] = doc.id
        doc_count += 1
        msg = f"생성됨"
        if not customer_id:
            msg += f" (거래처코드 '{customer_code}' 미매칭)"
        results.append({"document_number": doc_number, "status": "created", "message": msg})

    # 품목 읽기
    item_count = 0
    if ws2:
        for row in ws2.iter_rows(min_row=2, values_only=True):
            if not row or not row[0] or not row[2]:
                continue
            ref_number = str(row[0]).strip()
            doc_id = doc_map.get(ref_number)
            if not doc_id:
                continue

            line_no = int(row[1]) if row[1] else 1
            product_code = str(row[2]).strip()
            description = str(row[3]).strip() if row[3] else None
            quantity = Decimal(str(row[4])) if row[4] else Decimal("1")
            uom = str(row[5]).strip() if row[5] else "EA"
            unit_price = Decimal(str(row[6])) if row[6] else Decimal("0")
            amount = Decimal(str(row[7])) if row[7] else quantity * unit_price
            item_currency = str(row[8]).strip() if row[8] else "USD"
            line_remarks = str(row[9]).strip() if len(row) > 9 and row[9] else None

            item = SalesDocumentItem(
                document_id=doc_id,
                line_no=line_no,
                product_code=product_code,
                description=description,
                quantity=quantity,
                uom=uom,
                unit_price=unit_price,
                amount=amount,
                currency=item_currency,
                line_remarks=line_remarks,
            )
            db.add(item)
            item_count += 1

    db.commit()

    return {
        "success": True,
        "summary": {
            "documents_created": doc_count,
            "documents_skipped": doc_skip,
            "items_created": item_count,
        },
        "results": results,
    }


@router.post("/bulk/import-sales-tracking")
async def import_sales_tracking_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    해외영업 주문/수금/출고 현황 엑셀에서 PI/CI 자동 생성 (v0.32.0)
    기존 영업팀 관리 파일을 그대로 업로드하면 PI + CI를 자동 생성합니다.
    """
    from openpyxl import load_workbook
    from datetime import date as date_type, datetime as dt_type
    from decimal import Decimal
    from io import BytesIO
    from app.models.sales_document import SalesDocument, SalesDocumentItem
    from app.models.business_partner import BusinessPartner

    content = await file.read()
    wb = load_workbook(BytesIO(content), data_only=True)
    ws = wb.active

    # 업체명 → 거래처ID 매칭 (유사 매칭 포함)
    all_partners = db.query(BusinessPartner).filter(BusinessPartner.is_customer == True).all()
    name_to_id = {}
    for bp in all_partners:
        name_to_id[bp.partner_name.lower()] = bp.id
        if bp.partner_name_en:
            name_to_id[bp.partner_name_en.lower()] = bp.id
        # short name 매칭 (BIMEL→Bimel, HTL→HTL Limited 등)
        name_to_id[bp.partner_code.lower()] = bp.id

    def find_partner_id(name):
        if not name:
            return None, name
        name_str = str(name).strip()
        # 정확 매칭
        pid = name_to_id.get(name_str.lower())
        if pid:
            return pid, name_str
        # 부분 매칭 (엑셀 이름이 DB 이름에 포함되거나 반대)
        for key, pid in name_to_id.items():
            if name_str.lower() in key or key in name_str.lower():
                return pid, name_str
        return None, name_str

    def parse_date(val):
        if isinstance(val, date_type):
            return val
        if isinstance(val, dt_type):
            return val.date()
        if val:
            s = str(val).strip()
            try:
                return date_type.fromisoformat(s[:10])
            except (ValueError, IndexError):
                pass
        return None

    results = []
    pi_created = 0
    ci_created = 0
    skipped = 0

    for row_idx in range(5, ws.max_row + 1):
        seq = ws.cell(row=row_idx, column=2).value  # B: 순번
        if not seq:
            continue

        prod_no = str(ws.cell(row=row_idx, column=3).value or '').strip()  # C: 생산번호
        sales_rep = str(ws.cell(row=row_idx, column=4).value or '').strip()  # D: 영업담당자
        company = str(ws.cell(row=row_idx, column=5).value or '').strip()  # E: 업체명
        po_number = str(ws.cell(row=row_idx, column=6).value or '').strip()  # F: PO
        order_date = parse_date(ws.cell(row=row_idx, column=7).value)  # G: 주문수령일
        pi_number = str(ws.cell(row=row_idx, column=8).value or '').strip()  # H: PI
        product_info = str(ws.cell(row=row_idx, column=9).value or '').strip()  # I: 품명
        payment_terms = str(ws.cell(row=row_idx, column=10).value or '').strip()  # J: 결제조건
        total_amount_raw = ws.cell(row=row_idx, column=11).value  # K: 총 주문 금액
        prepay = ws.cell(row=row_idx, column=13).value  # M: 실수령 선금
        balance_pay = ws.cell(row=row_idx, column=14).value  # N: 실수령 잔금
        prepay_date = parse_date(ws.cell(row=row_idx, column=15).value)  # O: 선금 수령일
        balance_date = parse_date(ws.cell(row=row_idx, column=16).value)  # P: 잔금 수령일
        remaining = ws.cell(row=row_idx, column=17).value  # Q: 잔금
        ci_number = str(ws.cell(row=row_idx, column=18).value or '').strip()  # R: CI
        ship_date = parse_date(ws.cell(row=row_idx, column=19).value)  # S: 선적일자
        export_no = str(ws.cell(row=row_idx, column=20).value or '').strip()  # T: 수출신고번호
        remarks = str(ws.cell(row=row_idx, column=21).value or '').strip()  # U: 비고

        customer_id, customer_name = find_partner_id(company)
        total_amount = Decimal(str(total_amount_raw)) if total_amount_raw else Decimal("0")
        paid_total = Decimal(str(prepay or 0)) + Decimal(str(balance_pay or 0))

        # 입금 상태 판정
        if total_amount > 0:
            if paid_total >= total_amount:
                payment_status = "PAID"
            elif paid_total > 0:
                payment_status = "PARTIAL"
            else:
                payment_status = "UNPAID"
        else:
            payment_status = None

        # === PI 생성 ===
        if pi_number and pi_number != 'None':
            existing = db.query(SalesDocument).filter(SalesDocument.document_number == pi_number).first()
            if existing:
                results.append({"row": row_idx, "doc": pi_number, "status": "skipped", "message": "이미 존재"})
                skipped += 1
            else:
                pi_status = "CONFIRMED" if ci_number else ("SENT" if payment_status == "PAID" else "DRAFT")
                pi_doc = SalesDocument(
                    document_type="PI",
                    document_number=pi_number,
                    document_date=order_date or date_type.today(),
                    customer_id=customer_id,
                    currency="USD",
                    total_amount=total_amount,
                    status=pi_status,
                    payment_status=payment_status,
                    paid_amount=paid_total if paid_total > 0 else None,
                    paid_date=prepay_date or balance_date,
                    customer_po_number=po_number or None,
                    payment_terms=payment_terms or None,
                    prepared_by=sales_rep or None,
                    remarks=f"[{prod_no}] {remarks}".strip() if prod_no else remarks or None,
                    version=1,
                    is_latest=True,
                    version_group=pi_number,
                )
                db.add(pi_doc)
                db.flush()

                # 품목 (축약 형태지만 1줄이라도 등록)
                if product_info:
                    pi_item = SalesDocumentItem(
                        document_id=pi_doc.id,
                        line_no=1,
                        product_code=product_info.split(' ')[0] if product_info else "",
                        description=product_info,
                        quantity=Decimal("1"),
                        uom="EA",
                        unit_price=total_amount,
                        amount=total_amount,
                        currency="USD",
                    )
                    db.add(pi_item)

                pi_created += 1
                msg = f"PI 생성"
                if not customer_id:
                    msg += f" (거래처 '{company}' 미매칭)"
                results.append({"row": row_idx, "doc": pi_number, "status": "created", "message": msg})

        # === CI 생성 ===
        if ci_number and ci_number != 'None':
            existing_ci = db.query(SalesDocument).filter(SalesDocument.document_number == ci_number).first()
            if not existing_ci:
                ci_doc = SalesDocument(
                    document_type="CI",
                    document_number=ci_number,
                    document_date=ship_date or order_date or date_type.today(),
                    customer_id=customer_id,
                    currency="USD",
                    total_amount=total_amount,
                    status="DRAFT",
                    remarks=f"수출신고: {export_no}" if export_no else None,
                    version=1,
                    is_latest=True,
                    version_group=ci_number,
                )
                db.add(ci_doc)
                db.flush()

                if product_info:
                    ci_item = SalesDocumentItem(
                        document_id=ci_doc.id,
                        line_no=1,
                        product_code=product_info.split(' ')[0] if product_info else "",
                        description=product_info,
                        quantity=Decimal("1"),
                        uom="EA",
                        unit_price=total_amount,
                        amount=total_amount,
                        currency="USD",
                    )
                    db.add(ci_item)

                ci_created += 1
                results.append({"row": row_idx, "doc": ci_number, "status": "created", "message": "CI 생성"})

    db.commit()

    return {
        "success": True,
        "summary": {
            "pi_created": pi_created,
            "ci_created": ci_created,
            "skipped": skipped,
            "total_rows": len(results),
        },
        "results": results[:50],
    }

