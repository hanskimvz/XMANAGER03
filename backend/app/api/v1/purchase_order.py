"""
발주서 API
발주서 관리 CRUD API를 제공합니다.

Service Layer를 통해 비즈니스 로직을 처리합니다.

v0.6.0: 입출고 관리 기능 추가
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import date
from urllib.parse import quote
import os
import uuid
from pathlib import Path

from app.api.v1.deps import get_purchase_order_service, handle_service_exception, get_db
from app.core.auth import require_auth
from app.models.user import User
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.services.pdf_service import PurchaseOrderPDFService
from app.services.purchase_order_service import PurchaseOrderService
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    PurchaseOrderListResponse,
    PurchaseOrderPaginatedResponse,
    PurchaseOrderItemCreate,
    PurchaseOrderItemUpdate,
    PurchaseOrderStatus,
    ReceiveRequest,
    ConfirmDeliveryRequest,
    PaymentRequest,
)
from app.core.exceptions import AppException
from app.core.config import settings

router = APIRouter(prefix="/purchase-orders", tags=["발주서 관리"])

# 파일 업로드 경로
UPLOAD_DIR = settings.uploads_path / "purchase_orders"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 부품 가격 이력 ====================

@router.get("/parts/{part_id}/price-history")
def get_part_price_history(
    part_id: int,
    limit: int = Query(5, ge=1, le=20, description="조회 개수"),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """부품별 이전 구매 가격 이력 조회"""
    try:
        return service.get_part_price_history(part_id, limit)
    except AppException as e:
        handle_service_exception(e)


# ==================== 발주서 조회 ====================

@router.get("", response_model=PurchaseOrderPaginatedResponse)
def get_purchase_order_list(
    keyword: Optional[str] = Query(None, description="검색 키워드 (발주번호, 비고)"),
    po_status: Optional[PurchaseOrderStatus] = Query(None, alias="status", description="상태 필터"),
    supplier_id: Optional[int] = Query(None, description="공급업체 ID"),
    from_date: Optional[date] = Query(None, description="발주일 시작"),
    to_date: Optional[date] = Query(None, description="발주일 종료"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(50, ge=1, le=1000, description="조회 개수"),
    order_by: str = Query("created_at", description="정렬 기준"),
    order_desc: bool = Query(True, description="내림차순 정렬 여부"),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주서 목록 조회 (검색 및 필터링)"""
    items, total = service.search_purchase_orders_with_count(
        keyword=keyword,
        status=po_status,
        supplier_id=supplier_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_desc=order_desc
    )

    # 항목 수 추가
    list_items = []
    for po in items:
        po_dict = {
            "id": po.id,
            "po_number": po.po_number,
            "supplier_id": po.supplier_id,
            "order_date": po.order_date,
            "expected_delivery_date": po.expected_delivery_date,
            "total_amount": po.total_amount,
            "status": po.status,
            "created_at": po.created_at,
            "supplier": po.supplier,
            "item_count": len(po.items) if po.items else 0,
        }
        list_items.append(po_dict)

    return {
        "items": list_items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(
    po_id: int,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주서 상세 조회"""
    try:
        return service.get_or_raise(po_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{po_id}/create-approval")
def create_purchase_approval_from_po(
    po_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """이 발주건으로 구매기안서(임시저장)를 자동 생성 — 업체·품목 자동 등록. (중복 시 기존 반환)"""
    from app.services.approval_service import ApprovalService
    try:
        doc = ApprovalService(db).create_purchase_draft_from_po(po_id, user)
        return {"approval_id": doc.id, "doc_number": doc.doc_number, "title": doc.title}
    except AppException as e:
        handle_service_exception(e)


@router.get("/{po_id}/pdf")
def download_purchase_order_pdf(
    po_id: int,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """
    발주서 PDF 다운로드

    발주서를 PDF 파일로 생성하여 다운로드합니다.
    """
    try:
        po = service.get_or_raise(po_id)

        # PDF 생성
        pdf_service = PurchaseOrderPDFService()
        pdf_buffer = pdf_service.generate(po)

        # 파일명 (한글 인코딩 처리)
        filename = f"발주서_{po.po_number}.pdf"
        encoded_filename = quote(filename)

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except AppException as e:
        handle_service_exception(e)


# ==================== 발주서 생성/수정/삭제 ====================

@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    po_in: PurchaseOrderCreate,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주서 생성"""
    try:
        return service.create_purchase_order(po_in)
    except AppException as e:
        handle_service_exception(e)


@router.put("/{po_id}", response_model=PurchaseOrderResponse)
def update_purchase_order(
    po_id: int,
    po_in: PurchaseOrderUpdate,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주서 수정 (DRAFT 상태에서만)"""
    try:
        return service.update_purchase_order(po_id, po_in)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_order(
    po_id: int,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주서 삭제 (DRAFT 상태에서만)"""
    try:
        service.delete_purchase_order(po_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 발주서 항목 관리 ====================

@router.post("/{po_id}/items", response_model=PurchaseOrderResponse)
def add_purchase_order_item(
    po_id: int,
    item_in: PurchaseOrderItemCreate,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주서 항목 추가"""
    try:
        return service.add_item(po_id, item_in)
    except AppException as e:
        handle_service_exception(e)


@router.put("/{po_id}/items/{item_id}", response_model=PurchaseOrderResponse)
def update_purchase_order_item(
    po_id: int,
    item_id: int,
    item_in: PurchaseOrderItemUpdate,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주서 항목 수정"""
    try:
        return service.update_item(po_id, item_id, item_in)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{po_id}/items/{item_id}", response_model=PurchaseOrderResponse)
def delete_purchase_order_item(
    po_id: int,
    item_id: int,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주서 항목 삭제"""
    try:
        return service.delete_item(po_id, item_id)
    except AppException as e:
        handle_service_exception(e)


# ==================== 상태 전이 ====================

@router.post("/{po_id}/order", response_model=PurchaseOrderResponse)
def order_purchase_order(
    po_id: int,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """주문 확정 (DRAFT → ORDERED)"""
    try:
        return service.order(po_id)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{po_id}/confirm", response_model=PurchaseOrderResponse)
def confirm_purchase_order(
    po_id: int,
    request: ConfirmDeliveryRequest,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """납기 확정 (ORDERED → CONFIRMED)"""
    try:
        return service.confirm_delivery(po_id, request)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{po_id}/receive", response_model=PurchaseOrderResponse)
def receive_purchase_order(
    po_id: int,
    request: ReceiveRequest,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """
    입고 처리 (→ RECEIVED)

    입고된 수량만큼 재고가 자동으로 증가합니다.
    불량 수량은 재고에서 제외됩니다.
    """
    try:
        return service.receive(po_id, request)
    except AppException as e:
        handle_service_exception(e)


# complete 엔드포인트는 더 이상 사용하지 않음 - 결재는 PATCH /payment 로 별도 관리
# @router.post("/{po_id}/complete", response_model=PurchaseOrderResponse)
# def complete_purchase_order(...): ...


@router.post("/{po_id}/rollback", response_model=PurchaseOrderResponse)
def rollback_purchase_order(
    po_id: int,
    reason: Optional[str] = Query(None, description="롤백 사유"),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """
    상태 롤백 (이전 상태로 되돌리기)

    입고완료 상태에서 롤백 시 재고가 차감됩니다.
    - ORDERED -> DRAFT
    - CONFIRMED -> ORDERED
    - RECEIVED -> CONFIRMED (재고 차감)
    """
    try:
        return service.rollback(po_id, reason)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
def cancel_purchase_order(
    po_id: int,
    reason: Optional[str] = Query(None, description="취소 사유"),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """발주 취소"""
    try:
        return service.cancel(po_id, reason)
    except AppException as e:
        handle_service_exception(e)


# ==================== 파일 첨부 ====================

@router.post("/{po_id}/upload/document", response_model=PurchaseOrderResponse)
async def upload_document(
    po_id: int,
    file: UploadFile = File(...),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """문서 파일 첨부"""
    try:
        # 파일 저장
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # 파일 정보
        file_info = {
            "file_name": file.filename,
            "file_path": str(file_path),
            "file_size": len(content),
            "content_type": file.content_type,
        }

        return service.add_document_file(po_id, file_info)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{po_id}/files/{file_index}", response_model=PurchaseOrderResponse)
def delete_document(
    po_id: int,
    file_index: int,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """문서 파일 삭제"""
    try:
        return service.remove_document_file(po_id, file_index)
    except AppException as e:
        handle_service_exception(e)


# ==================== 결제 처리 ====================

class MarkSentRequest(BaseModel):
    sent: bool = True


class DisbursementFromPOsRequest(BaseModel):
    po_ids: List[int]


@router.post("/disbursement")
def create_disbursement_from_pos(
    request: DisbursementFromPOsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
):
    """선택한 여러 발주서(입고분)를 하나의 지출결의서(임시저장)로 묶어 생성."""
    from app.services.approval_service import ApprovalService
    try:
        doc = ApprovalService(db).create_disbursement_from_pos(request.po_ids, user)
        return {"id": doc.id, "doc_number": getattr(doc, "doc_number", None), "title": doc.title}
    except AppException as e:
        handle_service_exception(e)


@router.post("/{po_id}/mark-sent", response_model=PurchaseOrderResponse)
def mark_purchase_order_sent(
    po_id: int,
    request: MarkSentRequest,
    service: PurchaseOrderService = Depends(get_purchase_order_service),
    user: User = Depends(require_auth),
):
    """발주서 발송 완료/취소 — 발송 완료 시 발송일자 기록."""
    try:
        return service.mark_sent(po_id, request.sent, actor_id=getattr(user, "id", None))
    except AppException as e:
        handle_service_exception(e)


@router.patch("/{po_id}/payment", response_model=PurchaseOrderResponse)
def update_payment_status(
    po_id: int,
    request: PaymentRequest,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """
    결제 상태 업데이트

    발주서의 결제 여부를 업데이트합니다.
    결제는 발주 프로세스 상태와 별도로 관리됩니다.
    """
    try:
        return service.update_payment(po_id, request)
    except AppException as e:
        handle_service_exception(e)
