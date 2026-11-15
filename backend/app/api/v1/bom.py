"""
BOM API
BOM CRUD API를 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional
from io import BytesIO
from datetime import datetime

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.bom_service import BOMService
from app.services.bom_excel_service import BOMExcelService
from app.schemas.bom import (
    BOMCreate,
    BOMUpdate,
    BOMResponse,
    BOMDetailResponse,
    BOMListItem,
    BOMPaginatedResponse,
    BOMBulkCreate,
    BOMTreeNode,
    BOMUploadValidateResponse,
    BOMUploadResult,
)
from app.core.exceptions import AppException
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bom", tags=["BOM"])


def get_bom_service(db: Session = Depends(get_db)) -> BOMService:
    return BOMService(db)


def handle_service_exception(e: AppException):
    raise HTTPException(status_code=e.status_code, detail=e.message)


# ==================== BOM 엑셀 업로드 (v0.23.0 → v2) ====================

@router.post("/upload/validate", response_model=BOMUploadValidateResponse)
async def validate_bom_upload(
    file: UploadFile = File(..., description="엑셀 파일 (.xlsx)"),
    mode: str = Query("replace", description="업로드 모드: replace (교체), append (추가)"),
    db: Session = Depends(get_db)
):
    """
    BOM 엑셀 파일 검증 (v2)

    엑셀 파일을 파싱하고 검증 결과를 반환합니다. DB에는 변경사항이 없습니다.
    L1 행이 상위 부품이 되며, 여러 L1이 있으면 여러 BOM 트리를 처리합니다.
    """
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")

    try:
        content = await file.read()
        service = BOMExcelService(db)
        header_info, rows = service.parse_excel(content)

        logger.info(f"[BOM Validate] 파일: {file.filename}, 파싱된 행 수: {len(rows)}, 모드: {mode}")
        for r in rows[:5]:
            logger.info(f"  행{r['row_number']}: L{r['level']} | {r['part_number_display']} | {r.get('part_name')}")

        if not rows:
            logger.warning("[BOM Validate] 파싱된 데이터 없음")
            return BOMUploadValidateResponse(
                is_valid=False,
                total_rows=0,
                error_count=1,
                items=[],
            )

        result = service.validate(header_info, rows, None, mode)
        logger.info(f"[BOM Validate] 결과: valid={result.valid_count}, warning={result.warning_count}, error={result.error_count}, parents={result.parent_parts}")
        return result
    except Exception as e:
        logger.error(f"[BOM Validate] 예외: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"엑셀 파싱 실패: {str(e)}")


@router.post("/upload", response_model=BOMUploadResult)
async def upload_bom_excel(
    file: UploadFile = File(..., description="엑셀 파일 (.xlsx)"),
    mode: str = Query("replace", description="업로드 모드: replace (교체), append (추가)"),
    db: Session = Depends(get_db)
):
    """
    BOM 엑셀 파일 업로드 및 일괄 등록 (v2)

    L1 행이 상위 부품, L2~ 행이 하위 부품입니다.
    - replace: 각 L1의 기존 BOM을 삭제하고 교체
    - append: 기존 BOM을 유지하고 새 항목만 추가
    - 미등록 품번은 자동 생성
    - 오류 건은 스킵 (부분 성공)
    """
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.")

    try:
        content = await file.read()
        service = BOMExcelService(db)
        header_info, rows = service.parse_excel(content)

        logger.info(f"[BOM Upload] 파일: {file.filename}, 파싱된 행 수: {len(rows)}, 모드: {mode}")
        for r in rows[:5]:
            logger.info(f"  행{r['row_number']}: L{r['level']} | {r['part_number_display']} | {r.get('part_name')}")

        if not rows:
            logger.warning("[BOM Upload] 파싱된 데이터 없음")
            return BOMUploadResult(
                success=False,
                message="엑셀 파일에서 데이터를 찾을 수 없습니다.",
                total=0,
            )

        # 바로 실행 (v2: 부분 성공 지원, execute 내부에서 검증+실행)
        result = service.execute(header_info, rows, None, mode)
        logger.info(f"[BOM Upload] 결과: success={result.success}, created={result.created_count}, skipped={result.skipped_count}, errors={result.errors}, parent_ids={result.parent_part_ids}")
        return result
    except Exception as e:
        logger.error(f"[BOM Upload] 예외: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"업로드 실패: {str(e)}")


@router.post("/children-count")
def get_children_count_batch(
    parent_part_ids: List[int],
    db: Session = Depends(get_db)
):
    """여러 부품의 하위 BOM 개수를 일괄 조회"""
    from sqlalchemy import func
    from app.models.bom import BOM as BOMModel
    counts = db.query(
        BOMModel.parent_part_id,
        func.count(BOMModel.id).label("count")
    ).filter(
        BOMModel.parent_part_id.in_(parent_part_ids),
        BOMModel.is_active == True
    ).group_by(BOMModel.parent_part_id).all()

    result = {pid: 0 for pid in parent_part_ids}
    for row in counts:
        result[row.parent_part_id] = row.count
    return result


@router.get("", response_model=BOMPaginatedResponse)
def get_bom_list(
    parent_part_id: Optional[int] = Query(None, description="상위 부품 ID"),
    child_part_id: Optional[int] = Query(None, description="하위 부품 ID"),
    is_active: Optional[bool] = Query(None, description="사용여부"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(100, ge=1, le=1000, description="조회 개수"),
    service: BOMService = Depends(get_bom_service)
):
    """BOM 목록 조회"""
    items, total = service.search_bom_with_count(
        parent_part_id=parent_part_id,
        child_part_id=child_part_id,
        is_active=is_active,
        skip=skip,
        limit=limit
    )

    result_items = []
    for bom in items:
        result_items.append(BOMListItem(
            id=bom.id,
            parent_part_id=bom.parent_part_id,
            parent_part_number=bom.parent_part.part_number if bom.parent_part else "",
            parent_part_name=bom.parent_part.part_name if bom.parent_part else "",
            child_part_id=bom.child_part_id,
            child_part_number=bom.child_part.part_number if bom.child_part else "",
            child_part_name=bom.child_part.part_name if bom.child_part else "",
            child_specification=bom.child_part.specification if bom.child_part else None,
            quantity=bom.quantity,
            unit_name=bom.unit.name_ko if bom.unit else None,
            bom_level=bom.bom_level,
            sort_order=bom.sort_order,
            is_active=bom.is_active
        ))

    return {
        "items": result_items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(result_items) < total
    }


@router.get("/parts", response_model=dict)
def get_bom_parts(
    keyword: Optional[str] = Query(None, description="검색어 (품번/품명)"),
    part_type: Optional[str] = Query(None, description="부품 유형: parent, child, all"),
    product_line_id: Optional[int] = Query(None, description="대분류/제품라인 필터"),
    part_group_id: Optional[int] = Query(None, description="소분류/품목군 필터"),
    level_id: Optional[int] = Query(None, description="레벨 필터"),
    material_id: Optional[int] = Query(None, description="재질 필터"),
    treatment_id: Optional[int] = Query(None, description="후처리 필터"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(50, ge=1, le=200, description="조회 개수"),
    service: BOMService = Depends(get_bom_service)
):
    """
    BOM에 등록된 부품 목록 조회 (v0.20.0, v0.22.0 필터 추가)

    - part_type='parent': 상위 부품(완제품/반제품)만 조회
    - part_type='child': 하위 부품만 조회
    - part_type='all' 또는 미지정: 모든 BOM 관련 부품 조회
    - product_line_id, part_group_id, level_id, material_id, treatment_id: 코드 마스터 기반 필터
    """
    try:
        items, total = service.get_bom_parts(
            keyword=keyword,
            part_type=part_type,
            product_line_id=product_line_id,
            part_group_id=part_group_id,
            level_id=level_id,
            material_id=material_id,
            treatment_id=treatment_id,
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


@router.get("/children/{parent_part_id}", response_model=List[BOMDetailResponse])
def get_children(
    parent_part_id: int,
    is_active: Optional[bool] = Query(True, description="사용여부 필터"),
    service: BOMService = Depends(get_bom_service)
):
    """상위 부품의 하위 부품 목록 조회"""
    try:
        items = service.get_children(parent_part_id, is_active)
        result = []
        for bom in items:
            child_part = bom.child_part
            result.append(BOMDetailResponse(
                id=bom.id,
                parent_part_id=bom.parent_part_id,
                child_part_id=bom.child_part_id,
                quantity=bom.quantity,
                unit_id=bom.unit_id,
                bom_level=bom.bom_level,
                sort_order=bom.sort_order,
                effective_date=bom.effective_date,
                expiry_date=bom.expiry_date,
                remark=bom.remark,
                is_active=bom.is_active,
                created_at=bom.created_at,
                updated_at=bom.updated_at,
                child_part={
                    "id": child_part.id,
                    "part_number": child_part.part_number,
                    "part_number_display": child_part.part_number_display,
                    "part_name": child_part.part_name,
                    "description": child_part.description,
                    "specification": child_part.specification,
                    "unit_name": child_part.unit.name_ko if child_part.unit else None
                } if child_part else None,
                unit_name=bom.unit.name_ko if bom.unit else None
            ))
        return result
    except AppException as e:
        handle_service_exception(e)


@router.get("/parents/{child_part_id}", response_model=List[BOMDetailResponse])
def get_parents(
    child_part_id: int,
    is_active: Optional[bool] = Query(True, description="사용여부 필터"),
    service: BOMService = Depends(get_bom_service)
):
    """하위 부품이 사용되는 상위 부품 목록 조회"""
    try:
        items = service.get_parents(child_part_id, is_active)
        result = []
        for bom in items:
            parent_part = bom.parent_part
            result.append(BOMDetailResponse(
                id=bom.id,
                parent_part_id=bom.parent_part_id,
                child_part_id=bom.child_part_id,
                quantity=bom.quantity,
                unit_id=bom.unit_id,
                bom_level=bom.bom_level,
                sort_order=bom.sort_order,
                effective_date=bom.effective_date,
                expiry_date=bom.expiry_date,
                remark=bom.remark,
                is_active=bom.is_active,
                created_at=bom.created_at,
                updated_at=bom.updated_at,
                parent_part={
                    "id": parent_part.id,
                    "part_number": parent_part.part_number,
                    "part_number_display": parent_part.part_number_display,
                    "part_name": parent_part.part_name,
                    "description": parent_part.description,
                    "specification": parent_part.specification,
                    "unit_name": parent_part.unit.name_ko if parent_part.unit else None
                } if parent_part else None,
                unit_name=bom.unit.name_ko if bom.unit else None
            ))
        return result
    except AppException as e:
        handle_service_exception(e)


@router.get("/tree/{parent_part_id}", response_model=List[BOMTreeNode])
def get_bom_tree(
    parent_part_id: int,
    service: BOMService = Depends(get_bom_service)
):
    """BOM 트리 구조 조회 (재귀)"""
    try:
        return service.get_bom_tree(parent_part_id)
    except AppException as e:
        handle_service_exception(e)


@router.get("/{bom_id}", response_model=BOMDetailResponse)
def get_bom(
    bom_id: int,
    service: BOMService = Depends(get_bom_service)
):
    """BOM 단건 조회"""
    try:
        bom = service.get_or_raise(bom_id)
        return BOMDetailResponse(
            id=bom.id,
            parent_part_id=bom.parent_part_id,
            child_part_id=bom.child_part_id,
            quantity=bom.quantity,
            unit_id=bom.unit_id,
            bom_level=bom.bom_level,
            sort_order=bom.sort_order,
            effective_date=bom.effective_date,
            expiry_date=bom.expiry_date,
            remark=bom.remark,
            is_active=bom.is_active,
            created_at=bom.created_at,
            updated_at=bom.updated_at,
            parent_part={
                "id": bom.parent_part.id,
                "part_number": bom.parent_part.part_number,
                "part_number_display": bom.parent_part.part_number_display,
                "part_name": bom.parent_part.part_name,
                "description": bom.parent_part.description,
                "specification": bom.parent_part.specification,
                "unit_name": bom.parent_part.unit.name_ko if bom.parent_part.unit else None
            } if bom.parent_part else None,
            child_part={
                "id": bom.child_part.id,
                "part_number": bom.child_part.part_number,
                "part_number_display": bom.child_part.part_number_display,
                "part_name": bom.child_part.part_name,
                "description": bom.child_part.description,
                "specification": bom.child_part.specification,
                "unit_name": bom.child_part.unit.name_ko if bom.child_part.unit else None
            } if bom.child_part else None,
            unit_name=bom.unit.name_ko if bom.unit else None
        )
    except AppException as e:
        handle_service_exception(e)


@router.post("", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
def create_bom(
    data: BOMCreate,
    service: BOMService = Depends(get_bom_service)
):
    """BOM 생성"""
    try:
        return service.create_bom(data)
    except AppException as e:
        handle_service_exception(e)


@router.post("/bulk", response_model=List[BOMResponse], status_code=status.HTTP_201_CREATED)
def create_bom_bulk(
    data: BOMBulkCreate,
    service: BOMService = Depends(get_bom_service)
):
    """BOM 일괄 생성"""
    try:
        return service.create_bulk(data.parent_part_id, data.items)
    except AppException as e:
        handle_service_exception(e)


@router.put("/{bom_id}", response_model=BOMResponse)
def update_bom(
    bom_id: int,
    data: BOMUpdate,
    service: BOMService = Depends(get_bom_service)
):
    """BOM 수정"""
    try:
        return service.update_bom(bom_id, data)
    except AppException as e:
        handle_service_exception(e)


@router.delete("/{bom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bom(
    bom_id: int,
    service: BOMService = Depends(get_bom_service)
):
    """BOM 삭제"""
    try:
        service.delete_bom(bom_id)
        return None
    except AppException as e:
        handle_service_exception(e)


@router.delete("/parent/{parent_part_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_children(
    parent_part_id: int,
    service: BOMService = Depends(get_bom_service)
):
    """상위 부품의 모든 BOM 삭제"""
    try:
        service.delete_all_children(parent_part_id)
        return None
    except AppException as e:
        handle_service_exception(e)


@router.patch("/sort-order/{parent_part_id}")
def update_sort_orders(
    parent_part_id: int,
    orders: List[dict],
    service: BOMService = Depends(get_bom_service)
):
    """BOM 정렬 순서 일괄 업데이트"""
    try:
        service.update_sort_orders(parent_part_id, orders)
        return {"message": "정렬 순서가 업데이트되었습니다."}
    except AppException as e:
        handle_service_exception(e)


@router.get("/export/excel/{parent_part_id}")
def export_bom_excel(
    parent_part_id: int,
    include_tree: bool = Query(True, description="전체 BOM 트리 포함 여부"),
    db: Session = Depends(get_db),
    service: BOMService = Depends(get_bom_service)
):
    """
    BOM 정보를 엑셀로 내보내기

    - include_tree=True: 전체 BOM 트리 (다단계 포함)
    - include_tree=False: 직접 하위 부품만 (1단계)
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from openpyxl.utils import get_column_letter

        # 상위 부품 정보 조회
        from app.models.parts import Part
        parent_part = db.query(Part).filter(Part.id == parent_part_id).first()
        if not parent_part:
            raise HTTPException(status_code=404, detail="부품을 찾을 수 없습니다.")

        # 워크북 생성
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOM"

        # 스타일 정의
        header_font = Font(bold=True, size=11)
        header_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
        title_font = Font(bold=True, size=14)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # 제목 영역
        ws['A1'] = "BOM (Bill of Materials)"
        ws['A1'].font = title_font
        ws.merge_cells('A1:H1')

        # 상위 부품 정보
        ws['A3'] = "상위 부품:"
        ws['A3'].font = Font(bold=True)
        ws['B3'] = parent_part.part_number_display or parent_part.part_number
        ws['A4'] = "부품명:"
        ws['A4'].font = Font(bold=True)
        ws['B4'] = parent_part.part_name
        ws['A5'] = "규격:"
        ws['A5'].font = Font(bold=True)
        ws['B5'] = parent_part.specification or "-"
        ws['A6'] = "출력일시:"
        ws['A6'].font = Font(bold=True)
        ws['B6'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 헤더 (8행부터)
        headers = ["레벨", "품번", "품명", "규격", "수량", "단위", "비고"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=8, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center')

        # 데이터 행 작성
        row_num = 9

        if include_tree:
            # 전체 트리 구조로 내보내기
            tree = service.get_bom_tree(parent_part_id)

            def write_tree_node(nodes: List[dict], level: int = 1):
                nonlocal row_num
                for node in nodes:
                    # 레벨 표시 (들여쓰기)
                    level_indent = "  " * (level - 1) + f"L{level}"

                    ws.cell(row=row_num, column=1, value=level_indent).border = thin_border
                    ws.cell(row=row_num, column=2, value=node.get('part_number_display') or node.get('part_number', '')).border = thin_border
                    ws.cell(row=row_num, column=3, value=node.get('part_name', '')).border = thin_border
                    ws.cell(row=row_num, column=4, value=node.get('specification', '') or '').border = thin_border
                    ws.cell(row=row_num, column=5, value=node.get('quantity', 0)).border = thin_border
                    ws.cell(row=row_num, column=5).alignment = Alignment(horizontal='right')
                    ws.cell(row=row_num, column=6, value=node.get('unit_name', '') or '').border = thin_border
                    ws.cell(row=row_num, column=7, value='').border = thin_border

                    row_num += 1

                    # 하위 노드 재귀
                    children = node.get('children', [])
                    if children:
                        write_tree_node(children, level + 1)

            write_tree_node(tree)
        else:
            # 직접 하위 부품만
            children = service.get_children(parent_part_id, is_active=True)
            for idx, bom in enumerate(children, 1):
                child = bom.child_part
                if not child:
                    continue

                ws.cell(row=row_num, column=1, value="L1").border = thin_border
                ws.cell(row=row_num, column=2, value=child.part_number_display or child.part_number).border = thin_border
                ws.cell(row=row_num, column=3, value=child.part_name).border = thin_border
                ws.cell(row=row_num, column=4, value=child.specification or '').border = thin_border
                ws.cell(row=row_num, column=5, value=float(bom.quantity)).border = thin_border
                ws.cell(row=row_num, column=5).alignment = Alignment(horizontal='right')
                ws.cell(row=row_num, column=6, value=bom.unit.name_ko if bom.unit else '').border = thin_border
                ws.cell(row=row_num, column=7, value=bom.remark or '').border = thin_border

                row_num += 1

        # 열 너비 조정
        column_widths = [8, 25, 30, 25, 10, 10, 20]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width

        # 파일 저장
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # 파일명 생성
        part_number = (parent_part.part_number_display or parent_part.part_number).replace("-", "_")
        filename = f"BOM_{part_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="엑셀 내보내기를 위해 openpyxl 패키지가 필요합니다."
        )
    except AppException as e:
        handle_service_exception(e)


@router.get("/upload/template")
def download_bom_upload_template():
    """
    BOM 엑셀 업로드용 빈 양식(템플릿) 다운로드 (BOM 개편 2026-09)

    - 컬럼: 레벨 | 품번 | 품명 | 규격 | 수량 | 단위 | 비고
    - 레벨(L1/L2/L3…)은 '트리 위치'(상위-하위 관계)를 뜻합니다. L1이 최상위 제품.
    - 예시 행 + 작성 안내 시트를 함께 포함합니다.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOM"

        header_font = Font(bold=True, size=11)
        header_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
        example_font = Font(italic=True, color="9CA3AF")
        thin = Side(style='thin')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        headers = ["레벨", "품번", "품명", "규격", "수량", "단위", "비고"]
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=col, value=h)
            c.font = header_font
            c.fill = header_fill
            c.border = border
            c.alignment = Alignment(horizontal='center')

        # 예시 행(회색 이탤릭 - 실제 입력 시 지우고 사용)
        examples = [
            ["L1", "HXB13-PSD-KIT", "커넥터 키트(제품)", "", "", "EA", "← L1: 최상위 제품(수량 비움)"],
            ["L2", "HXB13-PSD-ASSY", "본체 어셈블리", "", "1", "EA", "L1 바로 아래 하위"],
            ["L3", "HB01-DCP-001", "하우징", "AL6061", "1", "EA", "L2 아래 하위(단품)"],
            ["L3", "HB01-DCP-002", "핀", "SUS303", "24", "EA", "수량은 상위 1개당 소요량"],
            ["L2", "HXB13-PSD-CAP", "캡", "", "2", "EA", "다시 L2 = 본체와 같은 단계"],
        ]
        for r, row in enumerate(examples, start=2):
            for col, val in enumerate(row, 1):
                cell = ws.cell(row=r, column=col, value=val)
                cell.border = border
                cell.font = example_font
                if col in (5,):
                    cell.alignment = Alignment(horizontal='right')

        widths = [8, 22, 26, 16, 8, 8, 34]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"

        # 작성 안내 시트
        guide = wb.create_sheet("작성안내")
        guide.column_dimensions['A'].width = 100
        lines = [
            ("BOM 업로드 양식 작성 안내", True),
            ("", False),
            ("1) 컬럼은 순서대로: 레벨 | 품번 | 품명 | 규격 | 수량 | 단위 | 비고", False),
            ("2) '레벨'은 트리 위치(상위-하위 관계)입니다. 부품의 레벨코드([S]/[C]/[R])와 다릅니다.", False),
            ("   - L1 = 최상위 제품(1개만). L2 = 그 바로 아래. L3 = L2의 아래 … 이런 식으로 계층을 표현합니다.", False),
            ("   - 레벨은 한 단계씩만 깊어질 수 있습니다(L1 다음 바로 L3 불가).", False),
            ("3) 수량은 '상위 1개당 소요량'입니다. L1(제품)은 수량을 비웁니다.", False),
            ("4) 품번은 X-Manager에 등록된 품번을 쓰면 자동 매칭됩니다.", False),
            ("   - 미등록 품번은 업로드 시 자동 생성(미분류)됩니다. 코드는 나중에 부여할 수 있습니다.", False),
            ("5) 단위는 EA, LOT 등. 공정성 항목은 LOT 권장.", False),
            ("6) 첫 시트(BOM)의 회색 예시 행은 지우고 실제 데이터를 입력하세요.", False),
            ("", False),
            ("※ 부품 수가 많지 않다면 엑셀 대신 BOM 탭의 '🧩 트리 편집'으로 직접 구성하는 것이 더 쉽습니다.", False),
        ]
        for i, (text, bold) in enumerate(lines, 1):
            cell = guide.cell(row=i, column=1, value=text)
            if bold:
                cell.font = Font(bold=True, size=13)

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=BOM_upload_template.xlsx"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="엑셀 생성을 위해 openpyxl 패키지가 필요합니다.")


# ==================== BOM 개편 P2/P3: 이동·상위묶기·변경로그 ====================
from pydantic import BaseModel as _BaseModel
from typing import Optional as _Optional, List as _ListT
from app.core.auth import require_auth as _require_auth_bom


class _MoveBomRequest(_BaseModel):
    new_parent_part_id: int


class _GroupUnderRequest(_BaseModel):
    child_bom_ids: _ListT[int]
    new_parent_part_id: int


@router.post("/{bom_id}/move")
def move_bom(bom_id: int, req: _MoveBomRequest,
             service: BOMService = Depends(get_bom_service), user=Depends(_require_auth_bom)):
    """BOM 연결을 다른 상위로 이동(드래그 재배치). 순환/중복 검증."""
    try:
        bom = service.move_bom(bom_id, req.new_parent_part_id, actor_id=getattr(user, "id", None))
        return {"id": bom.id, "parent_part_id": bom.parent_part_id, "child_part_id": bom.child_part_id}
    except AppException as e:
        handle_service_exception(e)


@router.post("/group-under")
def group_under(req: _GroupUnderRequest,
                service: BOMService = Depends(get_bom_service), user=Depends(_require_auth_bom)):
    """상위 트리 만들기: 선택한 하위들을 새 상위(new_parent_part_id) 밑으로 묶기."""
    try:
        return service.group_under(req.child_bom_ids, req.new_parent_part_id, actor_id=getattr(user, "id", None))
    except AppException as e:
        handle_service_exception(e)


@router.get("/audit/change-log")
def bom_change_log(parent_part_id: _Optional[int] = Query(None), limit: int = Query(100, ge=1, le=500),
                   service: BOMService = Depends(get_bom_service)):
    """BOM 변경 감사로그."""
    rows = service.get_change_log(parent_part_id=parent_part_id, limit=limit)
    return [{"id": r.id, "action": r.action, "parent_part_id": r.parent_part_id,
             "child_part_id": r.child_part_id, "detail": r.detail, "actor_id": r.actor_id,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
