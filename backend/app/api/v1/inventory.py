"""
재고 관리 API
재고 관리 CRUD API를 제공합니다.

Service Layer를 통해 비즈니스 로직을 처리합니다.

v0.5.0: 재고관리 기능 추가
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional
from io import BytesIO
from datetime import datetime
import os
import uuid
from pathlib import Path

from app.api.v1.deps import get_inventory_service, get_inventory_lot_service, handle_service_exception
from app.services.inventory_service import InventoryService
from app.services.inventory_lot_service import InventoryLotService
from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryAdjust,
    InventoryResponse,
    InventoryListResponse,
    InventoryPaginatedResponse,
    InventoryTransactionResponse,
    InventoryTransactionPaginatedResponse,
    InventoryStatus,
    TransactionType,
)
from app.schemas.inventory_lot import (
    InventoryLotCreate,
    InventoryLotUpdate,
    InventoryLotResponse,
    InventoryLotListItem,
    PaginatedLotResponse,
    FIFOSuggestionResponse,
)
from app.core.exceptions import AppException
from app.core.config import settings

router = APIRouter(prefix="/inventory", tags=["재고 관리"])

# 파일 업로드 경로
UPLOAD_DIR = settings.uploads_path / "inventory_transactions"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 재고 조회 ====================

@router.get("", response_model=InventoryPaginatedResponse)
def get_inventory_list(
    keyword: Optional[str] = Query(None, description="검색 키워드 (품번, 부품명)"),
    inventory_status: Optional[InventoryStatus] = Query(None, alias="status", description="상태 필터"),
    low_stock_only: bool = Query(False, description="부족 재고만 조회"),
    product_line_id: Optional[int] = Query(None, description="대분류(제품라인) ID"),
    part_group_id: Optional[int] = Query(None, description="소분류(품목군) ID"),
    level_id: Optional[int] = Query(None, description="레벨 ID"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(50, ge=1, le=1000, description="조회 개수"),
    order_by: str = Query("updated_at", description="정렬 기준"),
    order_desc: bool = Query(True, description="내림차순 정렬 여부"),
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 목록 조회 (검색 및 필터링)"""
    items, total = service.search_inventory_with_count(
        keyword=keyword,
        status=inventory_status,
        low_stock_only=low_stock_only,
        product_line_id=product_line_id,
        part_group_id=part_group_id,
        level_id=level_id,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_desc=order_desc
    )
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }


@router.get("/low-stock", response_model=List[InventoryListResponse])
def get_low_stock(
    limit: int = Query(100, ge=1, le=500, description="조회 개수"),
    service: InventoryService = Depends(get_inventory_service)
):
    """부족 재고 목록 조회"""
    return service.get_low_stock(limit)


@router.get("/out-of-stock", response_model=List[InventoryListResponse])
def get_out_of_stock(
    limit: int = Query(100, ge=1, le=500, description="조회 개수"),
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 없음 목록 조회"""
    return service.get_out_of_stock(limit)


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(
    inventory_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 단건 조회"""
    try:
        return service.get_or_raise(inventory_id)
    except AppException as e:
        handle_service_exception(e)


@router.get("/part/{part_id}", response_model=InventoryResponse)
def get_inventory_by_part(
    part_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """부품 ID로 재고 조회"""
    try:
        return service.get_by_part_id_or_raise(part_id)
    except AppException as e:
        handle_service_exception(e)


# ==================== 재고 생성/수정/삭제 ====================

@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(
    inventory: InventoryCreate,
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 생성 (부품에 재고 등록)"""
    try:
        return service.create_inventory(inventory)
    except AppException as e:
        handle_service_exception(e)


@router.post("/initialize-all")
def initialize_inventory_for_all_parts(
    service: InventoryService = Depends(get_inventory_service)
):
    """
    모든 기존 부품에 대해 재고 레코드 일괄 생성

    재고가 없는 부품에 대해서만 새로 생성합니다 (초기 수량 0).
    이미 재고가 있는 부품은 건너뜁니다.
    """
    result = service.initialize_inventory_for_all_parts()
    return {
        "message": f"재고 초기화 완료: {result['created']}건 생성, {result['skipped']}건 건너뜀",
        **result
    }


@router.put("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(
    inventory_id: int,
    inventory: InventoryUpdate,
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 정보 수정 (재주문점, 단가 등 - 수량 제외)"""
    try:
        return service.update_inventory(inventory_id, inventory)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(
    inventory_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 삭제"""
    try:
        service.delete_inventory(inventory_id)
        return None
    except AppException as e:
        handle_service_exception(e)


# ==================== 재고 조정 ====================

@router.post("/{inventory_id}/adjust", response_model=InventoryResponse)
def adjust_inventory(
    inventory_id: int,
    adjust: InventoryAdjust,
    service: InventoryService = Depends(get_inventory_service)
):
    """
    재고 조정 (입고/출고/조정)

    거래 유형:
    - IN: 입고 (수량 증가)
    - OUT: 출고 (수량 감소)
    - ADJUST: 조정 (수량 직접 설정)
    - RETURN: 반품 (수량 증가)
    - COUNT: 실사 (수량 직접 설정 + 실사일 업데이트)
    """
    try:
        return service.adjust_inventory(inventory_id, adjust)
    except AppException as e:
        handle_service_exception(e)


# ==================== 거래 이력 ====================

@router.get("/{inventory_id}/transactions", response_model=InventoryTransactionPaginatedResponse)
def get_inventory_transactions(
    inventory_id: int,
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(50, ge=1, le=500, description="조회 개수"),
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 ID로 거래 이력 조회"""
    try:
        # 재고 존재 확인
        service.get_or_raise(inventory_id)

        items, total = service.get_transactions(
            inventory_id=inventory_id,
            skip=skip,
            limit=limit
        )
        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + len(items) < total
        }
    except AppException as e:
        handle_service_exception(e)


@router.get("/part/{part_id}/transactions", response_model=InventoryTransactionPaginatedResponse)
def get_part_transactions(
    part_id: int,
    transaction_type: Optional[TransactionType] = Query(None, description="거래 유형 필터"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(50, ge=1, le=500, description="조회 개수"),
    service: InventoryService = Depends(get_inventory_service)
):
    """부품 ID로 거래 이력 조회"""
    items, total = service.get_transactions_by_part(
        part_id=part_id,
        transaction_type=transaction_type,
        skip=skip,
        limit=limit
    )
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }


@router.get("/{inventory_id}/transactions/export/excel")
def export_inventory_transactions_excel(
    inventory_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 거래 이력 엑셀 내보내기 (사유 포함)"""
    try:
        import openpyxl
        from openpyxl.utils import get_column_letter

        inv = service.get_or_raise(inventory_id)
        items, _ = service.get_transactions(inventory_id=inventory_id, skip=0, limit=10000)

        type_labels = {"IN": "입고", "OUT": "출고", "ADJUST": "조정", "RETURN": "반품", "COUNT": "실사"}

        def _num(q):
            if q is None:
                return ""
            f = float(q)
            return int(f) if f == int(f) else f

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "거래 이력"

        part = inv.part if inv else None
        part_no = part.part_number_display if part else ""
        part_name = part.part_name if part else ""

        # 상단 부품 정보(1행) + 헤더(2행)
        ws.cell(row=1, column=1, value=f"거래 이력 — {part_no} {part_name}".strip())
        headers = ["일시", "유형", "변동수량", "변동 전", "변동 후", "사유", "참조", "비고"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=2, column=col, value=header)

        for idx, tx in enumerate(items, 3):
            sign = "+" if tx.transaction_type in ("IN", "RETURN") else ("-" if tx.transaction_type == "OUT" else "")
            ref = ""
            if tx.reference_type or tx.reference_id:
                ref = f"{tx.reference_type or ''}" + (f": {tx.reference_id}" if tx.reference_id else "")
            qty = _num(tx.quantity)
            ws.cell(row=idx, column=1, value=tx.transaction_date.strftime("%Y-%m-%d %H:%M") if tx.transaction_date else "")
            ws.cell(row=idx, column=2, value=type_labels.get(tx.transaction_type, tx.transaction_type))
            ws.cell(row=idx, column=3, value=f"{sign}{qty}" if qty != "" else "")
            ws.cell(row=idx, column=4, value=_num(tx.quantity_before))
            ws.cell(row=idx, column=5, value=_num(tx.quantity_after))
            ws.cell(row=idx, column=6, value=tx.reason or "")
            ws.cell(row=idx, column=7, value=ref)
            ws.cell(row=idx, column=8, value=tx.remarks or "")

        widths = [17, 8, 12, 12, 12, 40, 20, 30]
        for col, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = w

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        safe_no = (part_no or f"inv{inventory_id}").replace("/", "_").replace("\\", "_")
        filename = f"inventory_history_{safe_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="openpyxl 라이브러리가 설치되지 않았습니다."
        )
    except AppException as e:
        handle_service_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"엑셀 생성 중 오류 발생: {str(e)}"
        )


# ==================== 엑셀 내보내기 ====================

@router.get("/export/excel")
def export_inventory_excel(
    keyword: Optional[str] = Query(None, description="검색 키워드"),
    inventory_status: Optional[InventoryStatus] = Query(None, alias="status", description="상태 필터"),
    low_stock_only: bool = Query(False, description="부족 재고만"),
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 목록 엑셀 내보내기"""
    try:
        import openpyxl
        from openpyxl.utils import get_column_letter

        # 재고 목록 조회 (최대 10000건)
        items, _ = service.search_inventory_with_count(
            keyword=keyword,
            status=inventory_status,
            low_stock_only=low_stock_only,
            skip=0,
            limit=10000,
            order_by="updated_at",
            order_desc=True
        )

        # 엑셀 워크북 생성
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "재고 목록"

        # 헤더
        headers = ["품번", "부품명", "현재고", "재주문점", "재주문량", "단가", "상태", "수정일"]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        # 데이터
        for row, item in enumerate(items, 2):
            ws.cell(row=row, column=1, value=item.part.part_number_display if item.part else "")
            ws.cell(row=row, column=2, value=item.part.part_name if item.part else "")
            ws.cell(row=row, column=3, value=float(item.quantity_on_hand))
            ws.cell(row=row, column=4, value=float(item.reorder_point) if item.reorder_point else "")
            ws.cell(row=row, column=5, value=float(item.reorder_qty) if item.reorder_qty else "")
            cost_cell = ws.cell(row=row, column=6, value=float(item.unit_cost) if item.unit_cost else "")
            if item.unit_cost:
                cost_cell.number_format = "#,##0"  # 단가: 천 단위 콤마(원화)
            ws.cell(row=row, column=7, value=item.status)
            ws.cell(row=row, column=8, value=item.updated_at.strftime("%Y-%m-%d %H:%M") if item.updated_at else "")

        # 열 너비 조정
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 15

        # 파일 저장
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="openpyxl 라이브러리가 설치되지 않았습니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"엑셀 생성 중 오류 발생: {str(e)}"
        )


# ==================== 거래 이력 파일 첨부 (v0.6.0) ====================

@router.post("/transactions/{transaction_id}/upload", response_model=InventoryTransactionResponse)
async def upload_transaction_document(
    transaction_id: int,
    file: UploadFile = File(...),
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 조정 거래에 증빙서류 첨부"""
    # 보안: 확장자 허용목록 + 크기 제한(실행/스크립트성 파일 차단)
    ALLOWED_DOC_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp",
                       ".xlsx", ".xls", ".csv", ".doc", ".docx", ".hwp", ".txt"}
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_DOC_EXT:
        raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다: {file_ext or '확장자 없음'}")
    try:
        # 파일 저장 (UUID 명 — 경로 탈출/덮어쓰기 방지)
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail=f"파일이 너무 큽니다(최대 {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB)")
        with open(file_path, "wb") as f:
            f.write(content)

        # 파일 정보
        file_info = {
            "file_name": file.filename,
            "file_path": str(file_path),
            "file_size": len(content),
            "content_type": file.content_type,
        }

        return service.add_transaction_document(transaction_id, file_info)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/transactions/{transaction_id}/files/{file_index}", response_model=InventoryTransactionResponse)
def delete_transaction_document(
    transaction_id: int,
    file_index: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """재고 조정 거래 증빙서류 삭제"""
    try:
        return service.remove_transaction_document(transaction_id, file_index)
    except AppException as e:
        handle_service_exception(e)


# ==================== 로트 관리 (v0.7.0) ====================

@router.get("/lots", response_model=PaginatedLotResponse)
def get_lots(
    part_id: Optional[int] = Query(None, description="부품 ID 필터"),
    lot_status: Optional[str] = Query(None, alias="status", description="상태 필터 (ACTIVE/DEPLETED/EXPIRED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    service: InventoryLotService = Depends(get_inventory_lot_service)
):
    """로트 목록 조회 (페이지네이션)"""
    return service.get_lots_paginated(
        part_id=part_id,
        status=lot_status,
        skip=skip,
        limit=limit
    )


@router.get("/{part_id}/lots", response_model=List[InventoryLotListItem])
def get_lots_by_part(
    part_id: int,
    include_depleted: bool = Query(False, description="소진된 로트 포함 여부"),
    service: InventoryLotService = Depends(get_inventory_lot_service)
):
    """부품별 로트 목록 조회 (FIFO 순)"""
    return service.get_lots_by_part(part_id, include_depleted)


@router.get("/{part_id}/lots/available", response_model=FIFOSuggestionResponse)
def get_fifo_suggestion(
    part_id: int,
    quantity: float = Query(..., gt=0, description="필요 수량"),
    service: InventoryLotService = Depends(get_inventory_lot_service)
):
    """FIFO 출고 제안 조회 (어느 로트에서 얼마나 출고해야 하는지)"""
    from decimal import Decimal
    return service.get_fifo_suggestion(part_id, Decimal(str(quantity)))


@router.post("/lots", response_model=InventoryLotResponse, status_code=status.HTTP_201_CREATED)
def create_lot(
    data: InventoryLotCreate,
    service: InventoryLotService = Depends(get_inventory_lot_service)
):
    """로트 직접 생성 (발주 입고 외 수동 생성 시)"""
    try:
        return service.create_lot(data)
    except AppException as e:
        handle_service_exception(e)


@router.get("/lots/{lot_id}", response_model=InventoryLotResponse)
def get_lot(
    lot_id: int,
    service: InventoryLotService = Depends(get_inventory_lot_service)
):
    """로트 상세 조회"""
    try:
        return service.get_lot_or_raise(lot_id)
    except AppException as e:
        handle_service_exception(e)


@router.put("/lots/{lot_id}", response_model=InventoryLotResponse)
def update_lot(
    lot_id: int,
    data: InventoryLotUpdate,
    service: InventoryLotService = Depends(get_inventory_lot_service)
):
    """로트 수정 (유효기간, 공급업체 로트번호 등)"""
    try:
        return service.update_lot(lot_id, data)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/lots/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lot(
    lot_id: int,
    service: InventoryLotService = Depends(get_inventory_lot_service)
):
    """로트 삭제 (소진된 로트만 가능)"""
    try:
        service.delete_lot(lot_id)
        return None
    except AppException as e:
        handle_service_exception(e)


@router.post("/lots/generate-missing")
def generate_missing_lots(
    service: InventoryLotService = Depends(get_inventory_lot_service),
    inv_service: InventoryService = Depends(get_inventory_service)
):
    """
    로트가 없는 재고에 대해 임의의 로트를 자동 생성합니다.

    - 재고 수량이 0보다 큰 부품 중 로트가 없는 부품에 대해 로트 생성
    - 로트번호: INIT-YYYYMMDD-{순번}
    - 입고일: 현재일시
    - 수량: 해당 재고의 현재고 수량
    """
    try:
        result = service.generate_missing_lots()
        return {
            "message": f"{result['created_count']}개의 로트가 생성되었습니다.",
            "created_count": result['created_count'],
            "skipped_count": result['skipped_count'],
            "details": result['details']
        }
    except AppException as e:
        handle_service_exception(e)
