"""
작업지시서 API
작업지시서 관리 CRUD API를 제공합니다.

Service Layer를 통해 비즈니스 로직을 처리합니다.

v0.6.0: 입출고 관리 기능 추가
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Header
from fastapi.responses import FileResponse
from typing import List, Optional
from urllib.parse import unquote
from datetime import date
from decimal import Decimal
import os
import uuid
import traceback
from pathlib import Path
from urllib.parse import quote

from app.api.v1.deps import get_work_order_service, handle_service_exception
from app.services.work_order_service import WorkOrderService
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderResponse,
    WorkOrderListResponse,
    WorkOrderPaginatedResponse,
    WorkOrderStatus,
    IssueRequest,
    AdditionalIssueRequest,
    ReturnRequest,
    ProductionCompleteRequest,
    StatusChangeRequest,
    BOMPreviewResponse,
)
from app.schemas.inventory_lot import (
    WorkOrderIssueRequest,
    ProductionAvailabilityResponse,
    WorkOrderItemIssueResponse,
)
from app.core.exceptions import AppException
from app.core.config import settings
from app.core.storage_paths import resolve_stored_path

router = APIRouter(prefix="/work-orders", tags=["작업지시서 관리"])

# 파일 업로드 경로
UPLOAD_DIR = settings.uploads_path / "work_orders"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 생산 가용수량 체크 (v0.7.0) ====================
# NOTE: 이 엔드포인트는 /{wo_id} 패턴보다 먼저 정의되어야 합니다.

@router.get("/check-availability", response_model=ProductionAvailabilityResponse)
def check_production_availability(
    product_part_id: int = Query(..., description="완제품 부품 ID"),
    quantity: float = Query(..., gt=0, description="생산 수량"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    BOM 기준 생산 가용수량 체크

    현재 재고로 몇 개까지 생산 가능한지 확인합니다.
    병목 부품(가장 부족한 부품)과 각 BOM 항목별 재고 상태를 반환합니다.
    """
    return service.check_production_availability(product_part_id, Decimal(str(quantity)))


# ==================== 수정된 작업지시서 조회 (v0.23.0) ====================

@router.get("/modified", response_model=List[WorkOrderListResponse])
def get_modified_work_orders(
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(20, ge=1, le=100, description="조회 개수"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    원본 생산요청서가 수정된 작업지시서 목록 조회 (v0.23.0)

    source_request_modified=True인 작업지시서를 반환합니다.
    출하완료/취소 상태는 제외됩니다.
    """
    items = service.get_modified_work_orders(skip=skip, limit=limit)
    list_items = []
    for wo in items:
        wo_dict = {
            "id": wo.id,
            "wo_number": wo.wo_number,
            "product_part_id": wo.product_part_id,
            "customer_id": wo.customer_id,
            "order_quantity": wo.order_quantity,
            "completed_quantity": wo.completed_quantity,
            "status": wo.status,
            "priority": wo.priority,
            "shipping_scheduled_date": wo.shipping_scheduled_date,
            "created_at": wo.created_at,
            "source_request_modified": True,
            "product_part": wo.product_part,
            "customer": wo.customer,
            "item_count": len(wo.items) if wo.items else 0,
            "product_count": len(wo.products) if wo.products else 0,
            "products": wo.products,
        }
        list_items.append(wo_dict)
    return list_items


# ==================== 작업지시서 조회 ====================

@router.get("", response_model=WorkOrderPaginatedResponse)
def get_work_order_list(
    keyword: Optional[str] = Query(None, description="검색 키워드 (지시번호, 고객주문번호, 비고)"),
    wo_status: Optional[WorkOrderStatus] = Query(None, alias="status", description="상태 필터"),
    customer_id: Optional[int] = Query(None, description="고객사 ID"),
    product_part_id: Optional[int] = Query(None, description="완제품 ID"),
    priority: Optional[int] = Query(None, ge=0, le=2, description="우선순위"),
    from_date: Optional[date] = Query(None, description="접수일 시작"),
    to_date: Optional[date] = Query(None, description="접수일 종료"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(50, ge=1, le=1000, description="조회 개수"),
    order_by: str = Query("created_at", description="정렬 기준"),
    order_desc: bool = Query(True, description="내림차순 정렬 여부"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """작업지시서 목록 조회 (검색 및 필터링)"""
    items, total = service.search_work_orders_with_count(
        keyword=keyword,
        status=wo_status,
        customer_id=customer_id,
        product_part_id=product_part_id,
        priority=priority,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_desc=order_desc
    )

    # 항목 수 추가 (v0.19.0 다중 제품 지원)
    list_items = []
    for wo in items:
        wo_dict = {
            "id": wo.id,
            "wo_number": wo.wo_number,
            "product_part_id": wo.product_part_id,  # deprecated
            "customer_id": wo.customer_id,
            "order_quantity": wo.order_quantity,  # deprecated
            "completed_quantity": wo.completed_quantity,  # deprecated
            "status": wo.status,
            "priority": wo.priority,
            "shipping_scheduled_date": wo.shipping_scheduled_date,
            "created_at": wo.created_at,
            "source_request_modified": wo.source_request_modified or False,  # v0.21.0
            "product_part": wo.product_part,  # deprecated
            "customer": wo.customer,
            "item_count": len(wo.items) if wo.items else 0,
            "product_count": len(wo.products) if wo.products else 0,  # v0.19.0
            "products": wo.products,  # v0.19.0
        }
        list_items.append(wo_dict)

    return {
        "items": list_items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }


@router.get("/{wo_id}", response_model=WorkOrderResponse)
def get_work_order(
    wo_id: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """작업지시서 상세 조회 (v0.22.0: 생산요청서 첨부파일 참조 포함)"""
    try:
        wo = service.get_or_raise(wo_id)

        # v0.22.0: 연결된 생산요청서의 첨부파일 포함
        response_data = WorkOrderResponse.model_validate(wo)
        if wo.production_request_id and wo.production_request:
            pr = wo.production_request
            response_data.source_request_attachments = pr.attachment_files or []
            response_data.source_request_number = pr.request_number
            response_data.production_request_id = wo.production_request_id

        return response_data
    except AppException as e:
        handle_service_exception(e)


@router.get("/{wo_id}/bom-preview", response_model=BOMPreviewResponse)
def get_bom_preview(
    wo_id: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """작업지시서 BOM 전개 미리보기"""
    try:
        wo = service.get_or_raise(wo_id)
        return service.get_bom_preview(wo.product_part_id, wo.order_quantity)
    except AppException as e:
        handle_service_exception(e)


@router.get("/preview/bom")
def preview_bom(
    product_part_id: int = Query(..., description="완제품 부품 ID"),
    order_quantity: Decimal = Query(..., gt=0, description="지시 수량"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """BOM 전개 미리보기 (작업지시서 생성 전)"""
    try:
        return service.get_bom_preview(product_part_id, order_quantity)
    except AppException as e:
        handle_service_exception(e)


# ==================== 작업지시서 생성/수정/삭제 ====================

@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
def create_work_order(
    wo_in: WorkOrderCreate,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    작업지시서 생성

    auto_expand_bom=True(기본값)이면 BOM을 자동으로 전개하여 항목을 생성합니다.
    """
    try:
        return service.create_work_order(wo_in)
    except AppException as e:
        handle_service_exception(e)


@router.put("/{wo_id}", response_model=WorkOrderResponse)
def update_work_order(
    wo_id: int,
    wo_in: WorkOrderUpdate,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """작업지시서 수정 (RECEIVED 상태에서만)"""
    try:
        return service.update_work_order(wo_id, wo_in)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{wo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order(
    wo_id: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """작업지시서 삭제 (RECEIVED 상태에서만)"""
    try:
        service.delete_work_order(wo_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 원본 요청서 수정 알림 (v0.21.0) ====================

@router.post("/{wo_id}/acknowledge-modification", response_model=WorkOrderResponse)
def acknowledge_source_modification(
    wo_id: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    원본 요청서 수정 알림 확인 (v0.21.0)

    source_request_modified 플래그를 False로 리셋합니다.
    작업지시자가 원본 요청서의 수정 내역을 확인했음을 표시합니다.
    """
    try:
        return service.acknowledge_source_modification(wo_id)
    except AppException as e:
        handle_service_exception(e)


# ==================== 작업지시 체인 (v0.31.0) ====================

@router.get("/{wo_id}/chain")
def get_work_order_chain(
    wo_id: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    작업지시 체인 조회 (선행/후속 관계)

    - parent: 이 WO의 산출물이 투입되는 상위 WO
    - children: 이 WO에 투입물을 제공하는 하위(선행) WO
    """
    from app.models.work_order import WorkOrder
    from app.models.parts import Part

    try:
        wo = service.get_or_raise(wo_id)
    except Exception:
        raise HTTPException(status_code=404, detail="작업지시서를 찾을 수 없습니다")

    db = service.db

    def wo_brief(w):
        target = None
        if w.target_part_id:
            part = db.query(Part).filter(Part.id == w.target_part_id).first()
            if part:
                target = {"id": part.id, "part_number_display": part.part_number_display, "part_name": part.part_name}
        return {
            "id": w.id,
            "wo_number": w.wo_number,
            "status": w.status,
            "order_type": w.order_type,
            "target_part": target,
            "product_part_id": w.product_part_id,
        }

    # 상위 WO (이 WO의 산출물이 투입되는 곳)
    parent = None
    if wo.parent_wo_id:
        parent_wo = db.query(WorkOrder).filter(WorkOrder.id == wo.parent_wo_id).first()
        if parent_wo:
            parent = wo_brief(parent_wo)

    # 하위 WO (이 WO에 투입물을 제공하는 선행 WO)
    children = db.query(WorkOrder).filter(
        WorkOrder.parent_wo_id == wo_id
    ).order_by(WorkOrder.created_at).all()

    return {
        "wo_id": wo_id,
        "wo_number": wo.wo_number,
        "parent": parent,
        "children": [wo_brief(c) for c in children],
    }


# ==================== 공정 로그 조회 (v0.31.0) ====================

@router.get("/{wo_id}/process-logs")
def get_process_logs(
    wo_id: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """작업지시서 공정 로그 (진행 이력) 조회"""
    from app.models.process_log import WorkOrderProcessLog

    db = service.db
    logs = db.query(WorkOrderProcessLog).filter(
        WorkOrderProcessLog.work_order_id == wo_id
    ).order_by(WorkOrderProcessLog.completed_at.desc()).all()

    return [
        {
            "id": log.id,
            "process_type": log.process_type,
            "process_name": log.process_name,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "duration_hours": float(log.duration_hours) if log.duration_hours else None,
            "worker_name": log.worker_name,
        }
        for log in logs
    ]


# ==================== 상태 전이 ====================

@router.post("/{wo_id}/approve", response_model=WorkOrderResponse)
def approve_work_order(
    wo_id: int,
    approved_by: Optional[int] = Query(None, description="승인자 ID"),
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """승인 (RECEIVED → APPROVED)"""
    try:
        wn = unquote(x_user_name) if x_user_name else None
        return service.approve(wo_id, approved_by, worker_name=wn)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/issue", response_model=WorkOrderResponse)
def issue_parts(
    wo_id: int,
    request: Optional[IssueRequest] = None,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    부품 출고 (APPROVED → ISSUED)

    출고된 수량만큼 재고가 자동으로 감소합니다.
    request가 None이면 전체 필요수량을 출고합니다.
    """
    try:
        wn = unquote(x_user_name) if x_user_name else None
        return service.issue_parts(wo_id, request, worker_name=wn)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/items/{item_id}/issue-additional", response_model=WorkOrderResponse)
def issue_additional(
    wo_id: int,
    item_id: int,
    request: AdditionalIssueRequest,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """추가 출고 (불량 대응 등)"""
    try:
        return service.issue_additional(wo_id, item_id, request)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/items/{item_id}/return", response_model=WorkOrderResponse)
def return_parts(
    wo_id: int,
    item_id: int,
    request: ReturnRequest,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """부품 반납"""
    try:
        return service.return_parts(wo_id, item_id, request)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/start-production", response_model=WorkOrderResponse)
def start_production(
    wo_id: int,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """작업 시작 (ISSUED → IN_PROGRESS)"""
    try:
        wn = unquote(x_user_name) if x_user_name else None
        return service.start_production(wo_id, worker_name=wn)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/complete-production", response_model=WorkOrderResponse)
def complete_production(
    wo_id: int,
    request: ProductionCompleteRequest,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """작업 완료 (IN_PROGRESS → INSPECTION)"""
    try:
        wn = unquote(x_user_name) if x_user_name else None
        return service.complete_production(wo_id, request, worker_name=wn)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/complete-inspection", response_model=WorkOrderResponse)
def complete_inspection(
    wo_id: int,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """검사 완료 (INSPECTION → PACKED)"""
    try:
        wn = unquote(x_user_name) if x_user_name else None
        return service.complete_inspection(wo_id, worker_name=wn)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/ship", response_model=WorkOrderResponse)
def ship_work_order(
    wo_id: int,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """출하 (PACKED → SHIPPED)"""
    try:
        wn = unquote(x_user_name) if x_user_name else None
        return service.ship(wo_id, worker_name=wn)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/quick-complete")
def quick_complete_work_order(
    wo_id: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    간편 출고 완료 (v0.31.0)

    재고 검증 없이 현재 상태에서 SHIPPED까지 한 번에 전환합니다.
    간편 처리 화면에서 사용합니다.
    세밀한 재고/공정 관리는 기존 작업지시 관리 탭에서 수행하세요.
    """
    from datetime import datetime, timezone

    try:
        wo = service.get_or_raise(wo_id)
    except AppException as e:
        handle_service_exception(e)
        return

    if wo.status == 'SHIPPED':
        raise HTTPException(status_code=400, detail="이미 출하 완료된 작업입니다")
    if wo.status == 'CANCELLED':
        raise HTTPException(status_code=400, detail="취소된 작업입니다")

    now = datetime.now(timezone.utc)
    db = service.db

    # 상태를 SHIPPED로 직접 전환 (중간 단계 생략)
    wo.status = 'SHIPPED'
    if not wo.approved_date:
        wo.approved_date = now
    if not wo.issue_completed_date:
        wo.issue_completed_date = now
    if not wo.production_start_date:
        wo.production_start_date = now
    if not wo.production_end_date:
        wo.production_end_date = now
    if not wo.inspection_completed_date:
        wo.inspection_completed_date = now
    if not wo.packing_completed_date:
        wo.packing_completed_date = now
    if not wo.shipping_completed_date:
        wo.shipping_completed_date = now
    wo.updated_at = now

    # 완료 수량 = 지시 수량
    if wo.order_quantity and (not wo.completed_quantity or wo.completed_quantity == 0):
        wo.completed_quantity = wo.order_quantity

    db.commit()

    return {"message": "출고 완료 처리되었습니다", "wo_number": wo.wo_number, "status": wo.status}


@router.post("/{wo_id}/cancel", response_model=WorkOrderResponse)
def cancel_work_order(
    wo_id: int,
    reason: Optional[str] = Query(None, description="취소 사유"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    작업지시 취소

    출고된 부품은 재고로 자동 복구됩니다.
    """
    try:
        return service.cancel(wo_id, reason)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/rollback", response_model=WorkOrderResponse)
def rollback_work_order(
    wo_id: int,
    reason: Optional[str] = Query(None, description="롤백 사유"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    상태 롤백 (이전 상태로 되돌리기)

    출고 상태에서 롤백 시 재고가 자동 복구됩니다.
    - APPROVED -> RECEIVED
    - ISSUED -> APPROVED (재고 복구)
    - IN_PROGRESS -> ISSUED
    - INSPECTION -> IN_PROGRESS
    - PACKED -> INSPECTION
    """
    try:
        return service.rollback(wo_id, reason)
    except AppException as e:
        handle_service_exception(e)


@router.post("/{wo_id}/restore", response_model=WorkOrderResponse)
def restore_work_order(
    wo_id: int,
    reason: Optional[str] = Query(None, description="복원 사유"),
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    취소된 작업지시서 복원

    취소 전 상태로 되돌립니다.
    단, 출고 상태였던 경우 APPROVED 상태로 복원됩니다 (재고 재차감 방지).
    """
    try:
        return service.restore(wo_id, reason)
    except AppException as e:
        handle_service_exception(e)


# ==================== 파일 첨부 ====================

@router.post("/{wo_id}/upload/document", response_model=WorkOrderResponse)
async def upload_document(
    wo_id: int,
    file: UploadFile = File(...),
    service: WorkOrderService = Depends(get_work_order_service)
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

        return service.add_document_file(wo_id, file_info)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{wo_id}/files/{file_index}", response_model=WorkOrderResponse)
def delete_document(
    wo_id: int,
    file_index: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """문서 파일 삭제"""
    try:
        return service.remove_document_file(wo_id, file_index)
    except AppException as e:
        handle_service_exception(e)


@router.get("/{wo_id}/files/{file_index}/preview")
def preview_document(
    wo_id: int,
    file_index: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    작업지시서 첨부파일 미리보기 (v0.22.0)

    PDF, 이미지 등을 브라우저에서 바로 열람합니다.
    """
    try:
        wo = service.get_or_raise(wo_id)
        files = wo.document_files or []
        if file_index < 0 or file_index >= len(files):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        file_info = files[file_index]
        file_path = resolve_stored_path(file_info.get("file_path", ""))
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다.")

        filename = file_info.get("file_name", "file")
        mimetype = file_info.get("content_type", "application/octet-stream")
        try:
            filename.encode('latin-1')
            disposition = f'inline; filename="{filename}"'
        except UnicodeEncodeError:
            encoded = quote(filename)
            disposition = f"inline; filename*=UTF-8''{encoded}"

        return FileResponse(
            path=str(file_path),
            media_type=mimetype,
            headers={"Content-Disposition": disposition}
        )
    except AppException as e:
        handle_service_exception(e)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"파일 미리보기 오류: {str(e)}")


@router.get("/{wo_id}/files/{file_index}/download")
def download_document(
    wo_id: int,
    file_index: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    작업지시서 첨부파일 다운로드 (v0.22.0)
    """
    try:
        wo = service.get_or_raise(wo_id)
        files = wo.document_files or []
        if file_index < 0 or file_index >= len(files):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        file_info = files[file_index]
        file_path = resolve_stored_path(file_info.get("file_path", ""))
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다.")

        filename = file_info.get("file_name", "file")
        mimetype = file_info.get("content_type", "application/octet-stream")
        try:
            filename.encode('latin-1')
            disposition = f'attachment; filename="{filename}"'
        except UnicodeEncodeError:
            encoded = quote(filename)
            disposition = f"attachment; filename*=UTF-8''{encoded}"

        return FileResponse(
            path=str(file_path),
            media_type=mimetype,
            headers={"Content-Disposition": disposition}
        )
    except AppException as e:
        handle_service_exception(e)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"파일 다운로드 오류: {str(e)}")


# ==================== 로트 선택 출고 (v0.7.0) ====================

@router.post("/{wo_id}/issue-with-lots", response_model=WorkOrderResponse)
def issue_parts_with_lots(
    wo_id: int,
    request: WorkOrderIssueRequest,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    로트 선택 부품 출고 (APPROVED → ISSUED)

    각 항목별로 FIFO 자동 또는 수동 로트 선택으로 출고합니다.

    요청 예시:
    ```json
    {
      "items": [
        {
          "item_id": 1,
          "issue_quantity": 100,
          "use_fifo": true
        },
        {
          "item_id": 2,
          "issue_quantity": 50,
          "use_fifo": false,
          "lot_selections": [
            { "lot_id": 5, "quantity": 30 },
            { "lot_id": 7, "quantity": 20 }
          ]
        }
      ]
    }
    ```
    """
    try:
        return service.issue_parts_with_lots(wo_id, request)
    except AppException as e:
        handle_service_exception(e)


@router.get("/{wo_id}/items/{item_id}/issue-records", response_model=List[WorkOrderItemIssueResponse])
def get_issue_records(
    wo_id: int,
    item_id: int,
    service: WorkOrderService = Depends(get_work_order_service)
):
    """
    작업지시서 항목별 출고 기록 조회

    어느 로트에서 얼마나 출고되었는지 확인합니다.
    """
    try:
        return service.get_issue_records(wo_id, item_id)
    except AppException as e:
        handle_service_exception(e)
